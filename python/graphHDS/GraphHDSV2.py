#!/usr/bin/env python3
import json, math, operator, os
from collections import defaultdict
from random import Random
from timeit import default_timer

import numpy as np

from autoHDS.ClusterProcessor import ClusterProcessor
from lib import reverse_dict


class GraphHDSException(Exception):
    pass


class GraphHDSV2:
    """
    Warning: Assumes similarity weights are normalized between 0 and 1 in the
             input graph!

    autoHDS-G v2 algo: First multi-resolution graph shaver exactly analogous to
    spatial autoHDS. V1 did not have the ability to see graphs at multiple
    resolutions. This should be a breakthrough in our understanding of how
    dense sub-structures on any graph can be smoothed and shaved to give a true
    graph HMA. Gets rid of an important parameter that was not handled properly
    in v1 that was causing bad resolution trees and having to pick an arbitrary
    threshold.

    IMPORTANT: this advanced version ONLY works with weighted (undirected)
    graphs. For binary graphs the best you can do is to use the GraphHDSV1 as
    the relative similarity information is missing in binary graphs.

    Similarity behaves like distance in spatial, flow measures if a pair of
    points are in a high-density region just like in spatial the count of nbrs
    is measured by a radius. reason you need flow for density measure is that a
    similarity graph, unlike a metric space, does not require or satisfy the
    triangle inequality of a metric space that allows simply using a radius.
    However first computing a thresholded graph then flow has the same effect!
    And then for a fixed min flow repeated change of similarity is akin to
    zooming into higher resolution clusters fully analogous to what happens in
    spatial auto-hds. Without this similarity shaving the multi-resolution part
    is lost.

    1. Fully analogous to autoHDS spatial with min_flow replacing min_pts and
       sim_eps replacing r_eps
    2. No thresholded graph needed, but can use it for speed.
    3. Computes top-down graph with highest density sub-graph first, similar to
       Gene DIVER.
    4. Shaves on edges and computes f_shave_edge then translates to actual
       f_shave. Not guaranteed uniform shaving.
    5. Computes stability on actual f_shave for a given f_shave_edge.
    6. Ability to quit early when one cluster is probably left (fakes the
       remaining shavings)
    7. Spits out Gene DIVER-compatible files.
    8. Computes flow from highest shaving to lowest by incrementally adding
       flow as the threshold changes, thus making it relatively efficient.
    9. Based on algo type prunes low flow edges or prunes low total flow nodes.
       edge : Prunes low flow edges before clustering
       node : Prunes low total flow nodes. Then connects all dense nodes with
              flows between them. This is fully analogous to spatial autoHDS.

    TODO: Ability to stop at certain max shaving level (this should work with
    TODO:     Gene DIVER)
    TODO: Add plug-in graph sim function hook with caching to remove need for a
    TODO:     pre-produced graph. This will make the algo lot more
    TODO:     efficient/faster to compute on large graphs.
    TODO: Add sampling with above feature to do multi-level coarse sampling,
    TODO:     partitioning, estimation, and refinement.
    TODO: Parallel computations of above for large graphs
    """

    def __init__(self, staging_dir, data_name, seed, min_flow, shave_rate, min_shave, id_mapping, weight_scale):
        """

        :param staging_dir:
        :param data_name:
        :param seed:
        :param min_flow:
        :param shave_rate:
        :param min_shave:
        :param id_mapping:
        :param weight_scale: see CLI
        """

        self.shave_rate = shave_rate
        self.min_shave = min_shave
        self.random = Random(seed)
        self.min_flow = min_flow
        self.weight_scale = weight_scale

        # loaded raw graph, loaded during first load call
        # Only stores half of the matrix removing duplicates.
        self.graph = list()
        # set of loaded original node ids and their flow
        self.node_flows = dict()

        # nodes with flow > min_flow
        self.dense_nodes = set()

        # weights of individual nodes if id mapping file is found with weights in it
        # default is 1.0 for all points if id mapping file not passed. Also weights passed are normalized between
        # 0 and 1 for all points based on weight_scale policy
        self.node_weights = dict()

        # 0 indexed sorted index mapping of points based on point order and makes ids contiguous
        # eg. 2 995 34 maps to 2->0, 34->1, 995->2
        self.sorted_node_mapping = dict()

        # Flow graph at any given point during shaving is stored here.
        self.flow_graph = dict()  # dict (node ID 1, node ID 2) -> flow

        # set of indices into self.graph representing unique nbrs/edges related to a given point/node
        self.nbrs = defaultdict(set)
        self.num_edges = None

        # edge shave threshold percentiles
        self.edge_shave_percentiles = None

        # clusters at each level, not re-labeled these are converted into HMA hierarchy at the end
        # no relabeling needed as that happens in gene diver
        self.level_clusters = None

        # check params
        if not 0 <= min_flow:
            raise ValueError("min_flow must be between 0 and 1")
        if not 0 <= shave_rate <= 1:
            raise ValueError("shave_rate muse be between 0 and 1")

        self.staging_dir = staging_dir

        # check paths
        if not os.path.isdir(staging_dir):
            raise GraphHDSException("Required staging dir does not exist: {}".format(staging_dir))

        # Parent directory of all output files
        self.output_dir = os.path.join(staging_dir, data_name)

        # create output experiment dir if not existing
        if not os.path.exists(self.output_dir):
            print("Creating output dir: {}".format(self.output_dir))
            os.makedirs(self.output_dir)

        # File containing graph input data
        self.graph_file = os.path.join(staging_dir, data_name + ".jsonl")

        if not os.path.isfile(self.graph_file):
            raise GraphHDSException("Could not find required graph input file: {}".format(self.graph_file))

        # load ID mapping
        if id_mapping:
            self.source_id_mappings = dict()
            # file with original node values as a single column of values"
            graph_index_file = os.path.join(staging_dir,
                                            data_name + ".mapping.tsv")

            print("Getting point id mappings from {}".format(graph_index_file))

            with open(graph_index_file) as f:
                line_count =0
                for line in f:
                    cols = line.split("\t")
                    if len(cols) != 3:
                        raise GraphHDSException("Expected format to be <node id> <int id> <raw weight>, found: {} at line: {}".format(line, line_count))
                    line_count += 1
                    node_original_id = cols[1].strip()
                    node_id = int(cols[0])
                    node_weight = float(cols[2])
                    self.source_id_mappings[node_id] = node_original_id
                    self.node_weights[node_id] = node_weight
        else:
            self.source_id_mappings = None

            print("Skipping ID mapping of points since graph ID mapping flag was off")

    def get_all_nodes_set(self):
        """
        returns the set of all original node ids
        :return:
        """

        return set(self.node_flows.keys())

    def _normalize_node_weights(self):
        """
        normalizes node weights for all nodes found so that they are on an average equal to 1.0 over all points
        0 : no weighting all are equal, also the case if id mapping is missing
        1 : raw weights just scaled by average weight
        2 and beyond: log scale renormalized using the correspond weight scale as log base
        :return:
        """

        # no node weights found set all of them to 1.0, or if weight scale is forced 0
        if (len(self.node_weights) == 0) or (self.weight_scale == 0):
            for _node_id in self.get_all_nodes_set():
                self.node_weights[_node_id] = 1.0

            print("Setting all nodes to weight of 1.0")
            return

        if self.weight_scale == 1:
            print("Setting all nodes using linear scaling")
        else:
            print("Setting all nodes using log({}) scaling".format(self.weight_scale))

        avg_weight = 0.0
        for w_node_id in self.node_weights.keys():
            # log scale it IFF weight scale > 1
            if self.weight_scale > 1:
                self.node_weights[w_node_id] = abs(math.log(self.node_weights[w_node_id], self.weight_scale))
            else:
                pass

            avg_weight += self.node_weights[w_node_id]

        # now compute average by dividing by node count
        avg_weight /= len(self.get_all_nodes_set())

        # now renormalize to between 0 and 1
        min_norm_weight = 10000000000.0
        max_norm_weight = 0.0
        avg_norm_weight = 0.0
        for _node_id in self.get_all_nodes_set():
            if _node_id in self.node_weights:
                norm_node_weight = self.node_weights[_node_id]/(avg_weight+0.000000000000000000000000000001)
                self.node_weights[_node_id] = norm_node_weight
                if min_norm_weight > norm_node_weight:
                    min_norm_weight = norm_node_weight
                if max_norm_weight < norm_node_weight:
                    max_norm_weight = norm_node_weight
                avg_norm_weight += norm_node_weight
            else:
                raise GraphHDSException("Missing node id {} in id mapping file".format(_node_id))

        avg_norm_weight /= len(self.get_all_nodes_set())
        print("Normalized all weights to an average of 1.0, avg_weight: {}, min_weight: "
              "{}, max_weight: {}".format(avg_norm_weight, min_norm_weight, max_norm_weight))

    def load_graph(self):
        """
        Loads the autoHDS-G graph into memory as a list of edges.
        """

        start_time = default_timer()
        last_time = start_time
        self.num_edges = 0

        # temporary edges for deduping
        unique_edges = set()
        with open(self.graph_file) as f:
            for i, line in enumerate(map(str.strip, f), 1):
                if len(line.strip()) == 0:
                    # ignore empty line
                    continue

                # line_len = len(line)
                # if line_len > max_line_len:
                #     print("    longest line so far (line {:,}): {:,} characters".format(i, line_len))
                #     max_line_len = line_len

                if i % 1000 == 0:
                    now = default_timer()
                    print("\tReading data for adjacency matrix row {:,} "
                          "({:.2f} s cumulative) (Δcumulative={:.3f} s)"
                          .format(
                              i,
                              now - start_time,
                              now - last_time
                          ))
                    last_time = default_timer()

                point_data = json.loads(line)

                point_id = point_data["id"]
                self.node_flows[point_id] = 0.0
                for neighbor, weight in point_data["connections"]:

                    if neighbor < point_id:
                        edge_id = (neighbor, point_id)
                        edge = (neighbor, point_id, weight)
                    elif neighbor > point_id:
                        edge_id = (point_id, neighbor)
                        edge = (point_id, neighbor, weight)
                    else:
                        print("Warning: removing referenced edges to self, please fix your graph!")
                        continue

                    if edge_id not in unique_edges:
                        self.num_edges += 1
                        self.graph.append(edge)
                        unique_edges.add(edge_id)

        # created sorted node id mapping for internal hma labels matrix storage
        idx = 0
        for external_int_id in sorted(self.node_flows):
            self.sorted_node_mapping[idx] = external_int_id
            idx += 1

        print("Graph at: {} loaded with {} points and {} edges in {:.3f} "
              "seconds".format(self.graph_file, len(self.graph),
                               self.num_edges, default_timer() - start_time))

        # now compute normalized node weights
        self._normalize_node_weights()

    def _calc_edge_shave_thresholds(self):
        """
        Calculates the edge similarity shave thresholds as percentiles based on
        edge shave rate.
        :return:
        """

        f_kept = 1.0
        edge_shave_idx = list()
        while math.floor(f_kept * self.num_edges) >= 1.0:
            # 0 indexed index into array
            percentile_idx = round(self.num_edges * f_kept) - 1
            # don't add shaving duplicates
            if (len(edge_shave_idx) == 0) or (edge_shave_idx[-1] != percentile_idx):
                edge_shave_idx.append(percentile_idx)

            f_kept *= 1.0 - self.shave_rate

        print("Found {} discrete shaving levels at shaving rate"
              " of {} for {} edges in graph.".format(len(edge_shave_idx), self.shave_rate, self.num_edges))

        # reverse the order of the list
        edge_shave_idx.reverse()

        # now calculate the shaving thresholds to get as many edges
        # TODO: speed this up using heap
        print("Sorting edge values for ")
        self.graph.sort(key=operator.itemgetter(2), reverse=True)

        edge_shave_percentiles = list()
        print("Edge shave thresholds (reverse order):")
        count = 0
        for edge_idx in edge_shave_idx:
            # remove duplicate thresholds that can happen due to digitization effects of similarities
            if (len(edge_shave_percentiles) == 0) or (edge_shave_percentiles[-1] != self.graph[edge_idx][2]):
                edge_shave_percentiles.append(self.graph[edge_idx][2])
                count += 1
                print("{:.7f} ".format(edge_shave_percentiles[-1]), end='')
            if count % 20 == 0:
                print("")
        print("\n")

        return edge_shave_percentiles

    def _compute_edge_prune_groups(self):
        """
        Given the full graph, returns the pruning groups of edges that would be
        added in the graph at each shaving level starting from nothing.
        :return:
        """

        edge_groups = list()
        for _ in self.edge_shave_percentiles:
            edge_groups.append(set())

        num_percentiles = len(self.edge_shave_percentiles)

        # absolute index into the weight percentile buckets
        weight_idx = 0
        # absolute index into the original graph edges list
        edge_idx = 0
        for point1, point2, weight in self.graph:
            # keep track of where you are in the bucket as you will move
            #     through sorted points and buckets in the same direction
            if (weight < self.edge_shave_percentiles[weight_idx]) and (weight_idx < num_percentiles - 1):
                weight_idx += 1

            # now save this edge in the right group, also we don't want duplicates a,b is same as b,a
            edge_groups[weight_idx].add(edge_idx)

            edge_idx += 1

        return edge_groups

    def _update_nbr_flow(self, edge_idx, node_pos):
        """
        Given an edge (node1, node2) and a target node pos (0 or 1) in the
        edge, update the flow between the target node's neighbors and the
        non-target node.
        :param edge_idx:
        :param node_pos:
        """

        if node_pos == 0:
            node1, node2, weight = self.graph[edge_idx]
        else:  # node_pos == 1
            node2, node1, weight = self.graph[edge_idx]

        for nbr_edge_idx in self.nbrs[node1]:
            node_a, node_b, nbr_weight = self.graph[nbr_edge_idx]
            nbr_node_id = node_a if node_a != node1 else node_b

            # todo try multiplicative flow weighting later. we weight by points also
            #flow_inc = nbr_weight * weight * ((self.node_weights[nbr_node_id] + self.node_weights[node2])/2.0)
            flow_inc = nbr_weight * weight * max(self.node_weights[nbr_node_id], self.node_weights[node2])

            # keep track of total flow to a point. actual flow at point is adjusted by its weight
            self.node_flows[node2] += flow_inc * self.node_weights[node2]
            self.node_flows[nbr_node_id] += flow_inc * self.node_weights[nbr_node_id]

            if (node2 not in self.dense_nodes) and (self.node_flows[node2] >= self.min_flow):
                self.dense_nodes.add(node2)
            if (nbr_node_id not in self.dense_nodes) and (self.node_flows[nbr_node_id] > self.min_flow):
                self.dense_nodes.add(nbr_node_id)

            # this is native tuple edge id as we need random access for flow updates
            node2_to_nbr_edge = (node2, nbr_node_id) if node2 < nbr_node_id else (nbr_node_id, node2)

            # update the flow from nod2 to node1's nbr
            if node2_to_nbr_edge not in self.flow_graph:
                self.flow_graph[node2_to_nbr_edge] = 0

            self.flow_graph[node2_to_nbr_edge] += flow_inc

    def _update_flow_with_next_level(self, group_in):
        """
        Apply the next prune group to the flow graph incrementally.
        Updates the flow graph with the group's edges.

        :param group_in:
        :type group_in: set[int]
        :return: set of nodes involved in new edges
        :rtype: set[int]
        """
        start_time = default_timer()

        # set of all points touched by these edges
        nodes_processed = set()

        # update current prune group neighbors
        for edge_idx in group_in:
            # update flow for neighbors of node1 and node2 in edge_idx caused by this new connection
            self._update_nbr_flow(edge_idx, 0)
            self._update_nbr_flow(edge_idx, 1)

            node1, node2, _ = self.graph[edge_idx]

            # update the nbrs set
            self.nbrs[node1].add(edge_idx)
            self.nbrs[node2].add(edge_idx)

            nodes_processed.add(node1)
            nodes_processed.add(node2)

        print("flow update took: {:.3f} seconds".format(default_timer() - start_time))
        return nodes_processed

    def _compute_edge_flow_clusters(self):
        """
        Computes current clusters given the threshold for min flow of edges
        using flood fill algorithm.
        :return: The sparse cluster labels as set of of points clustered.
        """
        start_time = default_timer()

        cluster_labels = dict()  # dict: node ID -> cluster ID
        cluster_points = dict()  # dict: cluster ID -> set of node IDs

        new_label = 0
        for (node1, node2), flow in self.flow_graph.items():
            if flow >= self.min_flow:

                if (node1 not in cluster_labels) and (node2 not in cluster_labels):
                    # neither of the nodes have been encountered before
                    # put them together in a new cluster
                    new_label += 1
                    cluster_points[new_label] = {node1, node2}
                    cluster_labels[node1] = new_label
                    cluster_labels[node2] = new_label

                elif (node1 in cluster_labels) and (node2 not in cluster_labels):
                    # add node2 to node1 cluster
                    label = cluster_labels[node1]
                    cluster_labels[node2] = label
                    cluster_points[label].add(node2)

                elif (node1 not in cluster_labels) and (node2 in cluster_labels):
                    # add node1 to node2 cluster
                    label = cluster_labels[node2]
                    cluster_labels[node1] = label
                    cluster_points[label].add(node1)

                elif (node1 in cluster_labels) and (node2 in cluster_labels):
                    # both are in cluster already merge the two clusters into one
                    node1_cluster_label = cluster_labels[node1]
                    node2_cluster_label = cluster_labels[node2]
                    if node2_cluster_label == node1_cluster_label:
                        # nothing to do, the points are already in the same cluster!
                        continue

                    # relabel points in node2 cluster points to node1 cluster label
                    node2_cluster_points = cluster_points[node2_cluster_label]
                    for node2_cluster_point in node2_cluster_points:
                        # add the node2 points to cluster of node1
                        cluster_labels[node2_cluster_point] = node1_cluster_label
                        cluster_points[node1_cluster_label].add(node2_cluster_point)
                    # remove the node2 cluster as it is merged
                    del cluster_points[node2_cluster_label]

                else:
                    # Regardless of the data, reaching this point should be
                    #     impossible.
                    # All possibilities of node1 and node2 being or not being
                    #     in cluster_labels were covered.
                    raise AssertionError

        print("cluster labeling took: {:.3f} seconds".format(default_timer() - start_time))

        return cluster_points

    def _compute_node_flow_clusters(self):
        """
        Computes current clusters given the threshold for min flow of total flow of nodes using
        flood fill algorithm.
        :return: The sparse cluster labels as set of of points clustered.
        """

        start_time = default_timer()

        cluster_labels = dict()  # dict: node ID -> cluster ID
        cluster_points = dict()  # dict: cluster ID -> set of node IDs

        new_label = 0
        for node1 in self.dense_nodes:
            dense_node_edges = self.nbrs[node1]

            for edge_id in dense_node_edges:
                node_a, node_b, _ = self.graph[edge_id]
                if node_a != node1:
                    node2 = node_a
                else:
                    node2 = node_b

                # nbr is not dense, skip. we are only clustering connected dense nodes
                if node2 not in self.dense_nodes:
                    continue

                if (node1 not in cluster_labels) and (node2 not in cluster_labels):
                    # neither of the nodes have been encountered before
                    # put them together in a new cluster
                    new_label += 1
                    cluster_points[new_label] = {node1, node2}
                    cluster_labels[node1] = new_label
                    cluster_labels[node2] = new_label

                elif (node1 in cluster_labels) and (node2 not in cluster_labels):
                    # add node2 to node1 cluster
                    label = cluster_labels[node1]
                    cluster_labels[node2] = label
                    cluster_points[label].add(node2)

                elif (node1 not in cluster_labels) and (node2 in cluster_labels):
                    # add node1 to node2 cluster
                    label = cluster_labels[node2]
                    cluster_labels[node1] = label
                    cluster_points[label].add(node1)

                elif (node1 in cluster_labels) and (node2 in cluster_labels):
                    # both are in cluster already merge the two clusters into one
                    node1_cluster_label = cluster_labels[node1]
                    node2_cluster_label = cluster_labels[node2]
                    if node2_cluster_label == node1_cluster_label:
                        # nothing to do, the points are already in the same cluster!
                        continue

                    # print("Merging cluster {} with {} points with {} with {} points".format(node1_cluster_label, len(node1_cluster_points), node2_cluster_label, len(node2_cluster_points)))

                    # relabel points in node2 cluster points to node1 cluster label
                    node2_cluster_points = cluster_points[node2_cluster_label]
                    for node2_cluster_point in node2_cluster_points:
                        # add the node2 points to cluster of node1
                        cluster_labels[node2_cluster_point] = node1_cluster_label
                        cluster_points[node1_cluster_label].add(node2_cluster_point)
                    # remove the node2 cluster as it is merged
                    del cluster_points[node2_cluster_label]

                else:
                    # Regardless of the data, reaching this point should be
                    #     impossible.
                    # All possibilities of node1 and node2 being or not being
                    #     in cluster_labels were covered.
                    raise AssertionError

        print("cluster labeling took: {} seconds".format(default_timer()-start_time))

        return cluster_points

    def hds(self, algo):
        """
        Computes hierarchical density shaving on graph using the V2 algorithms
        described in the docstring of this class.
        :param algo: dense total flow node or dense flow edge based
        :return:
        """

        start_time = default_timer()

        print("Computing using Graph Auto-HDS {} Algo!".format(algo))
        # Compute edge percentile thresholds based on shaving rate.
        # A list of values
        self.edge_shave_percentiles = self._calc_edge_shave_thresholds()

        # Compute pruning groups for edges by edge shave thresholds.
        # A set of edges grouped by idx into edge percentile thresholds
        prune_groups = self._compute_edge_prune_groups()

        num_edge_kept = 0
        num_pts = len(self.node_flows)
        num_edges = len(self.graph)
        num_levels = len(prune_groups)
        points_processed = set()
        num_pts_clustered = None

        clusters_for_saved_levels = list()

        for edge_shave_level, prune_group in enumerate(prune_groups, 0):

            level = num_levels - edge_shave_level

            # Compute flow graph using all edges above sim_eps threshold which
            #     is given by previous groups, then add the flow because of the
            #     extra edges appearing in the next group.
            level_points_processed = self._update_flow_with_next_level(prune_group)

            points_processed.update(level_points_processed)
            num_edge_kept += len(prune_group)
            # now threshold by min_flow and find the number of clusters
            if algo == "node":
                clusters = self._compute_node_flow_clusters()
            elif algo == "edge":
                clusters = self._compute_edge_flow_clusters()
            else:
                raise GraphHDSException("Unsupported algo passed: {}".format(algo))

            num_clusters = len(clusters)
            cluster_sizes = list()
            for cluster in clusters.values():
                cluster_sizes.append(len(cluster))
            # track no. of points clustered in this level vs last
            num_pts_clustered_last_level = num_pts_clustered
            num_pts_clustered = sum(cluster_sizes)

            # you need skip duplicate levels that can happen as edge shaving is not predictable w.r.t point shavings
            if (num_pts_clustered_last_level is not None) and (num_pts_clustered == num_pts_clustered_last_level):
                print("Redundant:", end='')
            elif num_pts_clustered == 0:
                print("No Clusters:", end='')
            else:
                clusters_for_saved_levels.append(clusters)
                print("Clustered:", end='')

            print("    Level: {}"
                  "    Edge: kept:{}, total:{}"
                  "    Points: processed:{}, kept: {}, total:{}"
                  "    No. of clusters: {}, cluster sizes: {}"
                  .format(level, num_edge_kept, num_edges,
                          len(points_processed), num_pts_clustered, num_pts,
                          num_clusters, cluster_sizes))

            fraction_clustered = num_pts_clustered / num_pts
            if fraction_clustered >= 1 - self.min_shave:
                print("Clustered maximum fraction data of {}, done clustering!".format(1-self.min_shave))
                break

        # add a fake level if min shave is not 0 to make sure hma index are correct
        if self.min_shave > 0.0:
            # all points in one cluster
            clusters = dict()
            clusters[1] = self.get_all_nodes_set()
            clusters_for_saved_levels.append(clusters)

        # Initialize cluster labels for each level.
        num_levels_saved = len(clusters_for_saved_levels)
        self.level_clusters = np.zeros((num_levels_saved, num_pts), dtype=np.uint32)

        # save clusters from all saved levels since number of points clustered increased (non redundant levels)
        save_level = 1
        for clusters in clusters_for_saved_levels:
            save_level_idx = num_levels_saved - save_level
            for cluster_id, cluster_nodes in clusters.items():
                for node_id in cluster_nodes:
                    self.level_clusters[save_level_idx, self.sorted_node_mapping[node_id]] = cluster_id

            save_level += 1



        # # shaving is finished as after this there is no info all clusters have merged into one
        # if num_clusters == 1 and max_level_cluster_count > 1:
        #     break

        # The code above is commented out because there could easily be a
        #     situation where there is only one cluster left, but as more
        #     edges appear, another cluster appears that is not connected
        #     to the first.
        # 1 0 0 0 0 0 0 0 0
        # 1 1 2 0 0 0 0 0 0
        # 1 1 2 2 0 0 0 0 0
        # 1 1 2 2 2 0 0 0 0
        # 1 1 3 3 3 3 0 0 0
        # 1 1 3 3 3 3 4 0 0
        # 1 1 3 3 3 3 4 4 4
        # 1 1 3 3 3 3 5 5 0
        #   ^       ^
        #   |       We don't want to stop here.
        #   |
        #   We want to stop here.

        print("Auto-HDS clustering finished!")
        print(" done. (time={:.2f} s)".format(default_timer() - start_time))

    def save(self, cluster_labels_file=None):
        level_clusters = self.level_clusters

        # sort level_clusters
        print("Sorting HMA Matrix, this may take some time if f ({}) is small and num points ({}) is large...".format(self.shave_rate, len(self.node_flows)))
        sort_indices = np.lexsort(level_clusters[::-1])

        cluster_processor = ClusterProcessor(
            sorted_labels=level_clusters[:, sort_indices],
            node_map=reverse_dict(self.sorted_node_mapping),
            sort_indices=sort_indices
        )

        del level_clusters
        del sort_indices

        cluster_processor.save_full_label_matrix_jsonl(
            os.path.join(self.output_dir, "full_label_matrix.jsonl")
        )

        print("Saving Gene Diver compatible output...", end="", flush=True)
        start_time = default_timer()
        cluster_processor.save_genediver_data(
            output_dir=self.output_dir,
            point_mapping=self.source_id_mappings,
            cluster_labels_file=cluster_labels_file
        )
        print(" done. (time={:.2f} s)".format(default_timer() - start_time))
