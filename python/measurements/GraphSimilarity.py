#!/usr/bin/env python3
from collections import defaultdict
import itertools

from graphDataAnalysis.GraphLabels import GraphLabels
from lib import comb, reverse_index, tiny_reverse_index, warn


class GraphSimilarity(object):

    SIMILARITY_ALGORITHMS = {"edge-ari", "edge-precision", "point-precision"}

    def __init__(self, clustering, labels, algorithm="point-precision", num_all_points=None, debug=False):
        """
        :param clustering:
        :type clustering: dict[int, set[int]]
        :param labels:
        :type labels: graphDataAnalysis.GraphLabels.GraphLabels
        :param algorithm:
        :type algorithm: str
        :param num_all_points: If passed, it assumes we need to infer missing
                               edges in labels set as cannot_link: if an edge
                               is not present in the set of labeled edges then
                               assume it's a cannotlink. Useful for external
                               datasets where we know ALL the positive edge
                               labels such as pokec.
        :return: similarity between 0 and 1
        """

        # standard initial state resources, things needed in each calculate cumulative iteration
        self.clustering = clustering
        # accumulated clusters plotted so far at the end of a calculate run
        self.cumulative_clustering = dict()
        self.labels = labels
        self.algorithm = algorithm
        self.num_all_points = num_all_points
        self.debug = debug

        if not isinstance(labels, GraphLabels):
            raise TypeError("labels must be an instance of GraphLabels")

        if algorithm not in GraphSimilarity.SIMILARITY_ALGORITHMS:
            raise ValueError("algorithm '{}' is not a valid option. Options are: {}".format(algorithm, GraphSimilarity.SIMILARITY_ALGORITHMS))

        # cache of previous iteration in the cumulative calc for speed up. The cache is a dict of variables needed
        # depending upon metric or type of measurement being done. We keep them flat, and only algos that need a
        # cache define it. In any given run some may never be cached which is ok

        self.clustering_cache = {"clustering_ridx": None}

    def get_cumulative_clusters(self):
        """
        :return: clusters so far
        """
        return self.cumulative_clustering

    def calculate_similarity(self, clustering, cluster_id):
        """
        Calculate cumulative similiarity by adding this cluster_id to existing calculations and return
        the cumulative values. we need this for speed as it can be quite slow on larger datasets otherwise
        :rtype: numbers.Real

        :param clustering:
        :param cluster_id: if None perform measurements from scratch on the whole clustering passed in, else accumulate
        :return:
        """

        self.clustering = clustering

        if cluster_id is None:
            # replace old clustering redo everything
            self.cumulative_clustering = self.clustering
        else:
            # cache run, build cumulative clusters
            self.cumulative_clustering[cluster_id] = clustering[cluster_id]

        if self.labels.label_format is GraphLabels.LABEL_FORMAT.EDGE_BASED:

            # lazy init only if not asked to redo from scratch. we cache many variables for full clustering once that
            # don't need to be incremental for both incremental and redo scenarios
            if ((cluster_id is not None) and (len(self.cumulative_clustering) == 1)) or (cluster_id is None):
                if cluster_id is None:
                    self.clustering_cache["clustering_ridx"] = reverse_index(self.clustering)

                # otherwise built incrementally later

                # all edges in labels set that are predicted as connected in clustering AND are MUST LINK in labels
                self.clustering_cache["connected_connected"] = 0
                # all edges in labels set (must link AND cannot link) that are predicted as connected in clustering
                self.clustering_cache["connected_a"] = 0
                self.clustering_cache["connected_labels"] = 0

                # this is recalculated every time non incremental one, else incremented every cluster
                self.clustering_cache["clusters_correct_point_count"] = 0
                self.clustering_cache["clusters_point_count"] = 0

                # ARI related non-incremental one-off calc for all clusters in one shot
                for _, label_weight in self.labels.edge_weights.items():
                    self.clustering_cache["connected_labels"] += label_weight

                self.clustering_cache["connected_connected_by_cluster"] = defaultdict(int)
                # total no. of edges
                if self.num_all_points is not None:
                    self.clustering_cache["num_edges"] = self.num_all_points * (self.num_all_points - 1) // 2

                    if cluster_id is None:
                        # batch recalculate all clusters: all the linkages intra-clusters are mix of cannot-link and must-link
                        for _, cluster in self.clustering.items():
                            cluster_size = len(cluster)
                            self.clustering_cache["connected_a"] += cluster_size * (cluster_size - 1) // 2
                    # else calculated incrementally
                else:
                    self.clustering_cache["num_edges"] = len(self.labels.edge_weights)

            # iterate based on the pairs that are smaller: cluster vs labels
            # label scanning will be faster
            scan_method = "labels"
            if cluster_id is not None:
                cluster_size = len(self.clustering[cluster_id])
                num_pairs_clusters = cluster_size * (cluster_size - 1) / 2
                if num_pairs_clusters < len(self.labels.edge_weights):
                    # cluster scanning will be faster and is possible
                    scan_method = "clusters"

            if scan_method == "clusters":
                # for all pairs in the cluster if they exist in label weights then update weight counts
                # this is faster when the cluster size is smaller than the label set
                for node_id_1, node_id_2 in itertools.combinations(self.clustering[cluster_id], 2):
                    # sort edges for deduping
                    if node_id_1 < node_id_2:
                        cluster_edge_id = (node_id_1, node_id_2)
                    else:
                        cluster_edge_id = (node_id_2, node_id_1)
                    if cluster_edge_id in self.labels.edge_weights:
                        label_weight = self.labels.edge_weights[cluster_edge_id]
                        self.clustering_cache["connected_connected_by_cluster"][cluster_id] += label_weight
                        self.clustering_cache["connected_connected"] += label_weight
                        self.clustering_cache["connected_a"] += 1
            else:
                if cluster_id is not None:
                    # build delta reverse index one cluster at a time as we only need to add stats for that cluster
                    # for the labels
                    self.clustering_cache["clustering_ridx"] = dict()
                    self.clustering_cache["clustering_ridx"] = tiny_reverse_index(k=cluster_id, v=self.clustering[cluster_id])
                # else already done first time

                # for all pairs in labels if they exit in cluster then update weight counts this
                # is faster when label set is smaller than cluster
                for (node_id_1, node_id_2), label_weight in self.labels.edge_weights.items():
                    # if the label edge is found in the cluster then connected_connected counts go up. also predicted count goes up, as we are
                    # filtering by labels only edges
                    if (node_id_1 in self.clustering_cache["clustering_ridx"]) and (node_id_2 in self.clustering_cache["clustering_ridx"]):
                        if self.clustering_cache["clustering_ridx"][node_id_1] == self.clustering_cache["clustering_ridx"][node_id_2]:
                            self.clustering_cache["connected_connected_by_cluster"][self.clustering_cache["clustering_ridx"][node_id_1]] += label_weight
                            self.clustering_cache["connected_connected"] += label_weight
                            self.clustering_cache["connected_a"] += 1

            # if infer missing edges as cannot link in labels, then you just count all the edges in the cluster as
            # connected_a for precision calculations as we don't prune non "cannot-link" tagged edges. We also need
            # to calculate the cross-cluster cannot-links
            if (cluster_id is not None) and (self.num_all_points is not None):
                # incremental add this cluster
                cluster_size = len(self.clustering[cluster_id])
                self.clustering_cache["connected_a"] += cluster_size * (cluster_size - 1) // 2

            if self.algorithm == "edge-ari":

                return self._soft_generalized_ari(
                    connected_connected=self.clustering_cache["connected_connected"],
                    connected_a=self.clustering_cache["connected_a"],
                    connected_labels=self.clustering_cache["connected_labels"],
                    num_edges=self.clustering_cache["num_edges"]
                )
            elif self.algorithm == "edge-precision":
                # cluster edge precision
                # warning this can give strange numbers when labels are sparse as denominator count can be 0. it is important
                # to make sure the cannot link set is complete, otherwise will have a bias that needs to be adjusted
                # todo: correct for missing cannot link fraction using odds ratio
                # so either use the infer flag if you can, OR use segmented clustering or use ARI for reporting

                return self._edge_precision(connected_connected=self.clustering_cache["connected_connected"],
                                            num_edges=self.clustering_cache["connected_a"])

            elif self.algorithm == "point-precision":
                # cluster point precision estimator
                # warning this can give strange numbers when labels are sparse as denominator count can be 0. it is important
                # to make sure the cannot link set is complete, otherwise will have a bias that needs to be adjusted
                # todo: correct for missing cannot link fraction using odds ratio
                # so either use the infer flag if you can, OR use segmented clustering or use ARI for reporting

                # if infer missing edges as cannot link in labels, then you just count all the edges in the cluster as
                # connected_a for precision calculations as we don't prune non "cannot-link" tagged edges

                # weighted accuracy by cluster size (assuming homogenous cluster label equivalence

                if cluster_id is None:

                    self.clustering_cache["clusters_correct_point_count"] = 0
                    self.clustering_cache["clusters_point_count"] = 0
                    # batch call for all clusters
                    for cluster_id, cluster in self.clustering.items():
                        cluster_size = len(cluster)
                        self.clustering_cache["clusters_point_count"] += cluster_size
                        correct_edge_count = self.clustering_cache["connected_connected_by_cluster"][cluster_id]
                        # quadratic equation solution for n given n(n-1)/2
                        # assuming that all edges came from 1 cluster how many nodes would have to be correct
                        # to see these many correct edges
                        if correct_edge_count > 0:
                            correct_nodes_equivalent_count = ((8*correct_edge_count+1)**0.5 + 1) / 2.0
                        else:
                            correct_nodes_equivalent_count = 0
                        self.clustering_cache["clusters_correct_point_count"] += correct_nodes_equivalent_count
                else:
                    cluster_size = len(self.clustering[cluster_id])
                    self.clustering_cache["clusters_point_count"] += cluster_size
                    correct_edge_count = self.clustering_cache["connected_connected_by_cluster"][cluster_id]
                    # quadratic equation solution for n given n(n-1)/2
                    # assuming that all edges came from 1 cluster how many nodes would have to be correct
                    # to see these many correct edges
                    if correct_edge_count > 0:
                        correct_nodes_equivalent_count = ((8 * correct_edge_count + 1) ** 0.5 + 1) / 2.0
                    else:
                        correct_nodes_equivalent_count = 0
                    self.clustering_cache["clusters_correct_point_count"] += correct_nodes_equivalent_count

                return self.clustering_cache["clusters_correct_point_count"] / self.clustering_cache["clusters_point_count"]

            else:
                # The code should never reach this point since there was a check at
                #     the top of the function. This is an unreachable state.
                raise AssertionError

        elif self.labels.label_format is GraphLabels.LABEL_FORMAT.CLUSTER_BASED:

            # this is not optimized for incremental calculations yet, redoes every time
            # let's not do it unless we really need it for speed

            # clustered_nodes = set.union(*clustering.values())

            # label nodes includes all nodes in labels including those nodes are background
            label_nodes = self.labels.background.union(*self.labels.clusters.values())

            # only include nodes in clustering that are in the labels as we can't measure the rest
            # prunes out predicted nodes that the labels don't know about as background/non-background
            filtered_clustering = dict()
            for predicted_cluster_id, predicted_cluster in self.clustering.items():
                filtered_clustering[predicted_cluster_id] = set(predicted_cluster) & label_nodes

            # we don't filter labels by clustering in our current sparse ARI implementation
            filtered_labels = self.labels.clusters

            if self.algorithm == "point-precision":
                raise NotImplementedError("point precision is ironically only implemented on edge-based labels")

            connected_connected = 0
            connected_a = 0
            for predicted_cluster_id, predicted_cluster in filtered_clustering.items():

                connected_a += comb(len(predicted_cluster), 2)

                # Count for any given predicted vs labeled groups, how many
                #     (connected) pairs they share in common, sum over all labeled
                #     groups. Note that this is maximized only when the predicted
                #     cluster is identical to one of the label groups otherwise it
                #     gets fragmented and only some pairs get overlapped
                for label_cluster_id, label_cluster in filtered_labels.items():
                    num_pairs = comb(len(predicted_cluster & label_cluster), 2)
                    connected_connected += num_pairs

            # now we count how many edges are connected in label set by enumerating across all groups
            connected_labels = 0
            for label_cluster_id, label_cluster in self.labels.clusters.items():
                connected_labels += comb(len(label_cluster), 2)

            # how many possible edge pairs the label has it's just n choose 2 where n = (number
            # of points in the label set)
            num_label_edges = comb(len(label_nodes), 2)

            if self.algorithm == "edge-ari":
                return self._soft_generalized_ari(
                    connected_connected=connected_connected,
                    connected_a=connected_a,
                    connected_labels=connected_labels,
                    num_edges=num_label_edges
                )
            elif self.algorithm == "edge-precision":
                # precision
                return self._edge_precision(
                    connected_connected=connected_connected,
                    num_edges=connected_a
                )
            else:
                # The code should never reach this point since there was a check at
                #     the top of the function. This is an unreachable state.
                raise AssertionError

        else:
            raise AssertionError  # unreachable state

    def _soft_generalized_ari(self, connected_connected, connected_a, connected_labels, num_edges):
        """
        :param connected_connected:
        :param connected_a:
        :param connected_labels:
        :param num_edges: number of edges found in labeled set
        :return:
        """
        label_edge_prior = connected_labels / num_edges

        index = connected_connected
        expected_index = connected_a * label_edge_prior
        max_index = min(connected_a, connected_labels)

        # add 10^(-9) to denominator to avoid ZeroDivisionError
        # return (index - expected_index)**0.5 / (max_index - expected_index + 0.00000000000001)**0.5
        return (index - expected_index) / (max_index - expected_index + 1e-9)

    def _edge_precision(self, connected_connected, num_edges):
        if not num_edges:
            warn("simple similarity index calculation: no edges to compute index "
                 "over; returning 0 similarity", Warning)
            return 0
        return connected_connected / num_edges
