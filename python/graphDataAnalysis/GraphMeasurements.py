#!/usr/bin/env python3
from collections import defaultdict
import json
import os
from random import Random
from timeit import default_timer

import numpy as np

from analysis.ClusterDeduper import ClusterDeduper
from dataReadWrite.ReadWriteAll import ALGORITHMS
from graphDataAnalysis.GraphLabels import GraphLabels
from graphDataAnalysis.GraphMeasurementsException import GraphMeasurementsException
from graphHDS.prune_cluster import get_density_sorted_cluster
from graphHDS.pseudo_stability import get_algo_cluster_stabilities
from labeling.LabelingManager import LabelingManager
from lib import reverse_index
from measurements.GraphSimilarity import GraphSimilarity
from util import read_genediver_graph_lab, SHAVING_METHOD, shave_clustering

ALGO_NAMES = set(ALGORITHMS.keys()) | {"autohds-g"}  # set for nice repr


class GraphMeasurements:

    # set specific properties of datasets here so as to change the behavior of how it is measured
    DATA_PARAMS = {
        "pokec": {
            "infer_missing_as_cannot_link": True
        },
        "livejournal": {
            "infer_missing_as_cannot_link": True
        }
    }

    def __init__(self, staging_dir, data_name, experiment_name, algorithm, similarity_algorithm, level_measurements,
                 seed, shave_type, fraction_kept, top_k, k_dithered, min_stability, shaving_algo, debug):

        staging_dir = os.path.expanduser(staging_dir)
        if not os.path.isdir(staging_dir):
            raise GraphMeasurementsException("Staging dir does not exist: {}".format(staging_dir))

        # no check is performed to see if data_name is valid

        if algorithm in ALGO_NAMES:
            algo_name = algorithm
            self.overclustered = False
        elif algorithm in {"{}.overclustered".format(algo) for algo in ALGO_NAMES}:
            algo_name = algorithm.rsplit(".", 1)[0]
            self.overclustered = True
        else:
            raise GraphMeasurementsException("Algorithm name not allowed! Got: {}".format(algorithm))

        if similarity_algorithm not in GraphSimilarity.SIMILARITY_ALGORITHMS:
            raise GraphMeasurementsException("Similarity algorithm name not allowed! Got: {}".format(similarity_algorithm))

        # similiarity (measurement) calc object initialize during first calculation run
        self.graph_sim = None

        self.staging_dir = staging_dir
        self.data_name = data_name
        self.experiment_name = experiment_name
        self.algorithm = algo_name
        self.similarity_algorithm = similarity_algorithm
        self.level_measurements = level_measurements

        self.seed = seed
        self.random = Random(self.seed)

        if shave_type == "rand_shave":
            self.shave_method = SHAVING_METHOD.RAND
        elif shave_type == "flow_shave":
            self.shave_method = SHAVING_METHOD.FLOW
        else:
            self.shave_method = None
        self.fraction_kept = fraction_kept
        self.top_k = top_k
        self.k_dithered = k_dithered
        self.min_stability = min_stability
        self.shaving_algo = shaving_algo
        self.debug = debug

        self.algorithm_dir = os.path.join(self.staging_dir, algorithm)

        # self.labels = None  # dict: (node ID 1, node ID 2) -> weight
        self.labels = None  # GraphLabels instance
        self.input_graph = None  # dict: (node ID 1, node ID 2) -> weight
        self.clustering = None  # defaultdict: cluster ID -> list of node IDs
        self.clustering_ridx = None  # dict: node ID -> cluster ID

        # set in the loader
        self.num_all_nodes = None  # int: number of vertices in original graph

        self.autohdsg_label_matrix = None  # numpy array of shape (number of shave levels, number of nodes)
        self.density_sorted_clusters = None  # dict: cluster id -> density sorted cluster (tuple of node id)

        # used only for stability sorted measurements
        self.cluster_stabilities = None  # dict: cluster ID -> stability

        self.measurements = None  # list of tuples (sample proportion, ari)

        self.contiguity_mapping = None  # dict: external ID -> contiguous ID

    def load_graph(self):
        """
        Load the main graph from staging_dir/data_name/graph into
        self.input_graph.
        """
        print("Loading graph...", end="", flush=True)
        start_time = default_timer()

        self.contiguity_mapping = dict()
        with open(os.path.join(self.staging_dir, "nodes")) as f:
            for i, node in enumerate(map(int, f)):
                self.contiguity_mapping[node] = i

        self.input_graph = dict()
        graph_nodes = set()
        with open(os.path.join(self.staging_dir, "graph")) as graph_file:
            for line in graph_file:
                node1, node2, weight = line.split("\t")
                node1 = self.contiguity_mapping[int(node1)]
                node2 = self.contiguity_mapping[int(node2)]
                weight = float(weight)

                # This graph file does not contain the same edge twice, and the
                #     node IDs in an edge are already sorted.

                # save to input graph
                self.input_graph[node1, node2] = weight
                if node1 not in graph_nodes:
                    graph_nodes.add(node1)
                if node2 not in graph_nodes:
                    graph_nodes.add(node2)

        self.num_all_nodes = len(graph_nodes)

        print(" done. (time={:.3f} s)".format(default_timer() - start_time))

    @staticmethod
    def _read_mapping(filename):
        """
        :param filename: mapping TSV filepath
        :type filename: str
        :return: ID mapping (old node ID -> new node ID), reverse ID mapping
                 (new node ID -> old node ID)
        :rtype: (dict[int, int], dict[int, int])
        """
        id_mapping = dict()  # dict: old node ID -> new node ID
        reverse_id_mapping = dict()  # dict: new node ID -> old node ID
        with open(filename) as f:
            for line in map(str.strip, f):
                if not line:
                    continue

                old_node_id, new_node_id = map(int, line.split("\t"))

                id_mapping[old_node_id] = new_node_id
                reverse_id_mapping[new_node_id] = old_node_id

        return id_mapping, reverse_id_mapping

    def load_output(self):
        """
        Load the output clustering of whatever graph clustering algorithm was
        used into self.clustering and self.clustering_ridx.

        For autohds-g level measurements: Loads the label matrix.

        TODO: This currently requires that for autoHDS-G the input file (graph.jsonl) had consecutive 0-indexed node IDs.
        """
        print("Loading clustering...", end="", flush=True)
        start_time = default_timer()

        if self.algorithm == "autohds-g":

            stage_graph_for_autohds_mapping_file = os.path.join(self.staging_dir, self.experiment_name + ".mapping.tsv")
            if os.path.isfile(stage_graph_for_autohds_mapping_file):

                stage_graph_for_autohds_mapping = dict()
                with open(stage_graph_for_autohds_mapping_file) as f:
                    for line in f:
                        autohds_int_node_id, str_node_id, _ = line.split("\t")
                        autohds_int_node_id = int(autohds_int_node_id)
                        stage_graph_for_autohds_mapping[autohds_int_node_id] = str_node_id

                gda_id_mapping = dict()
                with open(os.path.join(self.staging_dir, "gda_id_mapping.tsv")) as f:
                    for line in f:
                        str_node_id, gda_int_node_id = line.split("\t")
                        gda_int_node_id = int(gda_int_node_id)
                        gda_id_mapping[str_node_id] = gda_int_node_id

                stage_graph_for_autohds_run = True
            else:
                stage_graph_for_autohds_run = False

            if self.level_measurements:

                # the clusterings will be loaded later from the full label matrix
                self.clustering = defaultdict(list)
                self.clustering_ridx = dict()

                label_matrix_dict = defaultdict(dict)
                max_level = -1

                # full_label_matrix.jsonl has no additional node ID mapping. The
                #     IDs are converted back to the same IDs as graph.jsonl. And
                #     since no ID mapping is done for autohds-g in the staging
                #     step, no node ID conversion is necessary.
                with open(os.path.join(self.algorithm_dir, "graph", "full_label_matrix.jsonl")) as f:
                    for line in f:

                        line_dict = json.loads(line)
                        level = line_dict["level"]
                        node_id = line_dict["id"]
                        cluster_label = line_dict["label"]

                        if level > max_level:
                            max_level = level

                        if stage_graph_for_autohds_run:
                            # GDA and autohds-g have different integer IDs if
                            #     stage_graph_for_autohds.py was run. This converts
                            #     the autohds-g IDs back to GDA IDs.
                            node_id = gda_id_mapping[stage_graph_for_autohds_mapping[node_id]]

                        node_id = self.contiguity_mapping[node_id]

                        label_matrix_dict[level][node_id] = cluster_label

                # 0s in the label matrix indicate background
                label_matrix = np.zeros((max_level + 1, self.num_all_nodes), dtype=np.uint8)
                for level, level_dict in label_matrix_dict.items():
                    for node_id, cluster_label in level_dict.items():
                        label_matrix[level, node_id] = cluster_label
                self.autohdsg_label_matrix = label_matrix

            else:  # stability sorted measurements

                graph_lab_clustering, self.cluster_stabilities = read_genediver_graph_lab(
                    os.path.join(self.staging_dir, self.experiment_name, "graph_lab.csv")
                )
                autohdsg_clustering = dict()
                nodes = set()
                pruned_clusters = set()
                for cluster_id, cluster in graph_lab_clustering.items():
                    if self.cluster_stabilities[cluster_id] < self.min_stability:
                        pruned_clusters.add(cluster_id)
                        continue
                    autohdsg_clustering[cluster_id] = set()
                    for node_id in cluster:

                        if stage_graph_for_autohds_run:
                            node_id = gda_id_mapping[node_id]
                        else:
                            # not sure if this is right
                            # this case won't be run for most data sets
                            node_id = int(node_id)
                        node_id = self.contiguity_mapping[node_id]

                        if node_id not in nodes:
                            nodes.add(node_id)
                        autohdsg_clustering[cluster_id].add(node_id)

                print("Nodes before deduping: {}".format(sum(map(len, autohdsg_clustering.values()))))
                # print("Unique nodes (len {}): {}".format(len(nodes), nodes))
                print("Pruned clusters since they didn't meet the min_stability: {}".format(pruned_clusters))
                print("Deduping clusters!")
                cluster_deduper = ClusterDeduper(autohdsg_clustering,
                                                 self.cluster_stabilities)
                deduped_autohdsg_clustering, excluded_clusters = cluster_deduper.get_deduped_clusters()
                print("Nodes after deduping: {}".format(sum(map(len, deduped_autohdsg_clustering.values()))))
                k_deduped = len(deduped_autohdsg_clustering)
                print("k_deduped: {}".format(k_deduped))

                # For debugging, will raise exception if there are multiple clusters per key
                deduped_nodes = set()
                for cluster in deduped_autohdsg_clustering.values():
                    if cluster & deduped_nodes:
                        raise AssertionError("There are overlapping clusters!")
                    deduped_nodes.update(cluster)
                print("Excluded clusters after deduping: {}".format(excluded_clusters))

                self.clustering = {cluster_id: list(cluster)
                                   for cluster_id, cluster in deduped_autohdsg_clustering.items()}
                self.clustering_ridx = reverse_index(self.clustering)

        else:
            # reverse_id_mapping: dict: contiguous 0-indexed node ID external to DRW -> GDA node ID
            _, reverse_id_mapping = self._read_mapping(
                os.path.join(self.algorithm_dir, "id_mapping.tsv")
            )

            reader = ALGORITHMS[self.algorithm](self.algorithm_dir)

            raw_clustering = reader.read_clustering()

            self.clustering_ridx = dict()
            self.clustering = dict()
            for cluster_id, cluster in raw_clustering.items():
                self.clustering[cluster_id] = list()

                for contiguous_node_id in cluster:
                    node_id = self.contiguity_mapping[reverse_id_mapping[contiguous_node_id]]

                    self.clustering[cluster_id].append(node_id)
                    self.clustering_ridx[node_id] = cluster_id
            self.num_all_nodes = sum(map(len, self.clustering.values()))

        print(" done. (time={:.3f} s)".format(default_timer() - start_time))

    def load_labels(self, human_cluster_labels):
        """
        Load the labels into self.labels.
        """
        print("Loading labels...")
        start_time = default_timer()

        self.labels = GraphLabels(
            data_set_dir=self.staging_dir,
            contiguity_mapping=self.contiguity_mapping,
            human_cluster_labels=human_cluster_labels
        )

        print("Done loading labels. (time={:.3f} s)".format(default_timer() - start_time))

    def prepare_measurements(self):
        """
        For level measurements:
        Gets density sorted clusters using get_density_sorted_cluster and
        stores them in self.density_sorted_clusters.

        For sorted measurements:
        Calculates the cluster stabilities if needed.
        """
        if self.num_all_nodes is None:
            raise GraphMeasurementsException("must load graph before preparing measurements")

        if self.level_measurements:

            print("Calculating density-sorted clusters...", end="", flush=True)
            start_time = default_timer()

            if self.input_graph is None:
                raise GraphMeasurementsException("load_graph must be called before get_density_sorted_clusters")
            if self.clustering is None or self.clustering_ridx is None:
                raise GraphMeasurementsException("load_output must be called before get_density_sorted_clusters")

            # dictionary that has cluster id -> edges param in get_density_sorted_cluster
            clustering_edges = dict()

            for cluster_id in self.clustering:
                clustering_edges[cluster_id] = list()
            for id1, id2 in self.input_graph:
                # only add if both are in same cluster
                if self.clustering_ridx[id1] == self.clustering_ridx[id2]:
                    # add in format of (node1, node2, weight)
                    clustering_edges[self.clustering_ridx[id1]].append((id1, id2, self.input_graph[id1, id2]))
            self.density_sorted_clusters = dict()
            for cluster_id, cluster in self.clustering.items():
                self.density_sorted_clusters[cluster_id] = get_density_sorted_cluster(
                    nodes=cluster,
                    edges=clustering_edges[cluster_id],
                    algo="1"  # TODO: add CLI option to choose shaving algo
                )

            print(" done. (time={:.3f} s)".format(default_timer() - start_time))

        elif self.algorithm != "autohds-g":

            self.cluster_stabilities = get_algo_cluster_stabilities(
                graph=self.input_graph,
                cluster_points=self.clustering
            )

    def _get_clustering_for_measurements(self, sample_proportion):
        """
        shave clusters and return new clustering
        :param sample_proportion:
        :type sample_proportion: float
        :return:
        :rtype: dict[int, set[int]]
        """

        # calculate shaved clustering from density-sorted clusters
        shaved_clustering = dict()
        for cluster_id, density_sorted_cluster in self.density_sorted_clusters.items():
            # only have sample_proportion of the density_sorted_cluster
            shaved_clustering[cluster_id] = set(density_sorted_cluster[int((1 - sample_proportion) *
                                                                           len(density_sorted_cluster)):])

        return shaved_clustering

    def _calculate_measurement(self, clustering, next_cluster_id=None):
        """
        :param clustering:
        :type clustering: dict[int, set[int]]
        :param: next_cluster_id: If passed, it's a way for it to know to reuse
                                 previous clustering and increment for speed,
                                 else redoes the whole evaluation on full
                                 clustering passed.
        :type next_cluster_id: int | None
        :return: num_clustered, similarity
        :rtype: (int, float)
        """
        num_all_points = None
        if (self.data_name in GraphMeasurements.DATA_PARAMS) and \
                ("infer_missing_as_cannot_link" in GraphMeasurements.DATA_PARAMS[self.data_name]) and \
                (GraphMeasurements.DATA_PARAMS[self.data_name]["infer_missing_as_cannot_link"]):
            if self.num_all_nodes is None:
                raise GraphMeasurementsException("Number of nodes in graph is undefined, needed for calculating measurements!")
            num_all_points = self.num_all_nodes
        if self.debug:
            print("    Calculating measurement...")

        # lazy init
        if self.graph_sim is None:
            self.graph_sim = GraphSimilarity(
                clustering=clustering,
                labels=self.labels,
                algorithm=self.similarity_algorithm,
                num_all_points=num_all_points,
                debug=self.debug
            )

        measurement = self.graph_sim.calculate_similarity(clustering=clustering, cluster_id=next_cluster_id)

        return sum(map(len, self.graph_sim.get_cumulative_clusters().values())), measurement

    def get_measurements(self):
        """
        Calculate measurements at different all different levels of clustering.
        This handles the shaving logic for level measurements and the top k
        logic for stability sorted measurements.
        :return: yields sample_proportion, num_clustered, similarity,
                 real_sample_proportion
        :rtype: collections.Iterable[(float, int, float, float)]
        """
        if self.labels is None:
            raise GraphMeasurementsException("load_labels must be called before get_measurements")

        self.measurements = list()

        # autohds-g is special
        if self.algorithm == "autohds-g" and self.level_measurements:

            if self.autohdsg_label_matrix is None:
                raise GraphMeasurementsException("prepare_measurements must be called before get_measurements")

            for level, level_clustering in enumerate(self.autohdsg_label_matrix):

                if not any(level_clustering):
                    # no more points are being clustered at this level
                    break

                if self.debug:
                    print("Calculating measurement on HDS level {}".format(level))
                # print(level_clustering)

                clustering = defaultdict(set)

                for node_id, cluster_label in enumerate(level_clustering):
                    if not cluster_label:
                        # this is a background point
                        continue

                    clustering[cluster_label].add(node_id)

                num_clustered, similarity = self._calculate_measurement(clustering)

                real_sample_proportion = num_clustered / self.num_all_nodes

                self.measurements.append((real_sample_proportion, similarity))
                yield None, num_clustered, similarity, real_sample_proportion

        elif self.level_measurements:

            if self.density_sorted_clusters is None:
                raise GraphMeasurementsException("prepare_measurements must be called before get_measurements")

            self.measurements = list()

            for sample_proportion in (1, .9, .8, .7, .6, .5, .4, .3, .2, .1):  # TODO: maybe don't hardcode sample proportions

                shaved_clustering = self._get_clustering_for_measurements(sample_proportion)

                num_clustered, similarity = self._calculate_measurement(shaved_clustering)

                real_sample_proportion = num_clustered / self.num_all_nodes

                self.measurements.append((real_sample_proportion, similarity))
                yield sample_proportion, num_clustered, similarity, real_sample_proportion

        else:  # stability sorted measurements

            if self.clustering is None or self.cluster_stabilities is None:
                raise GraphMeasurementsException

            cluster_sizes = set()
            for cluster_id in self.clustering:
                cluster_sizes.add(len(self.clustering[cluster_id]))

            print("Maximum cluster size before shaving is {}, and minimum cluster size of {} for the algorithm {}".format(
                max(cluster_sizes), min(cluster_sizes), self.algorithm
            ))

            # autohds-g doesn't need to be shaved
            if (self.algorithm != "autohds-g") and (self.shave_method is not None):
                start_timer = default_timer()
                if self.top_k is not None:
                    # we need to filter the cluster points using the original params to determine how much more shaving
                    # needs
                    filtered_cluster_points, top_k_cluster_ids, full_dithered_cluster_ids = LabelingManager.filter_clustering(
                        clustering=self.clustering,
                        cluster_stabilities=self.cluster_stabilities,
                        top_k=self.top_k,
                        k_dithered=self.k_dithered
                    )
                    num_filtered_points = LabelingManager.count_unique_points_in_clusters(filtered_cluster_points)
                    print("Number of nodes clustered after filtering: {}".format(num_filtered_points))
                    filtered_proportion = num_filtered_points / self.num_all_nodes
                    print("filtered proportion: {:.5f}".format(filtered_proportion))
                    # SHAVE CLUSTERS (if filtering didn't already shave enough)
                    print("Sample proportion: {:.5f}".format(self.fraction_kept))
                else:
                    # this means it is not a human judged dataset, so no filtering is needed
                    filtered_proportion = 1.0
                    filtered_cluster_points = self.clustering

                if filtered_proportion <= self.fraction_kept:
                    print("No shaving performed because enough points were already filtered.")
                    shaved_cluster_points = filtered_cluster_points
                else:
                    new_sample_proportion = self.fraction_kept / filtered_proportion
                    print("new sample proportion: {:.5f}".format(new_sample_proportion))
                    print("Shaving clusters using algorithm {}...".format(self.shaving_algo))
                    # shave clusters down to the same number of nodes clustered as autoHDS-G
                    shaved_cluster_points = shave_clustering(
                        clustering=self.clustering,
                        method=self.shave_method,
                        fraction_kept=new_sample_proportion,
                        input_graph=self.input_graph,
                        shaving_algo=self.shaving_algo,
                        debug=self.debug,
                        num_points_in_graph=self.num_all_nodes,
                        seed=self.seed
                    )

                    num_shaved_cluster_points = LabelingManager.count_unique_points_in_clusters(shaved_cluster_points)
                    print("num shaved cluster points: {}".format(num_shaved_cluster_points))
                    print()
                print("Shaved clusters! Took {:.2f} seconds".format(default_timer() - start_timer))
            else:
                # no shaving performed
                shaved_cluster_points = self.clustering

            sorted_cluster_ids = sorted(
                shaved_cluster_points,
                key=self.cluster_stabilities.__getitem__,
                reverse=True
            )

            if (self.data_name in GraphMeasurements.DATA_PARAMS) and \
                ("infer_missing_as_cannot_link" in GraphMeasurements.DATA_PARAMS[self.data_name]) and \
                    (GraphMeasurements.DATA_PARAMS[self.data_name]["infer_missing_as_cannot_link"]):
                print("Inferring cannot-links for calculating edge-based measurements")
            else:
                # todo: Neil/Sheshank compute cannot link odds params in datset gen and then adjust formulas below and then change
                # this message to the weight (1/cannot-link fraction) of each cannotlink being estimated and remove this
                print("Warning: explicit cannot-links used for calculating edge-based measurements, make sure your "
                      "cannot-link labels are complete, else your metrics will be wrong!")

            # build shaved clustering of all clusters
            clustering = dict()
            cluster_sizes = set()
            for k, cluster_id in enumerate(sorted_cluster_ids, 1):
                # update clustering with next stable cluster
                clustering[cluster_id] = shaved_cluster_points[cluster_id]
                cluster_sizes.add(len(clustering[cluster_id]))

            print("Maximum cluster size after shaving is {}, and minimum cluster size of {} for the algorithm {}, with "
                  "{} total clusters".format(max(cluster_sizes), min(cluster_sizes), self.algorithm,
                                             len(sorted_cluster_ids)))

            # measure clustering incrementally
            # top 1, top 2, etc.
            for k, cluster_id in enumerate(sorted_cluster_ids, 1):
                if self.debug:
                    print("Calculating measurement for top {} clusters".format(k))
                # send the full clustering reference, but also then say which cluster is next to be added for incremental
                # calculations for speed. If cluster_id is not passed this will not work and you will not pass incremental
                # clusterings which would be slow
                num_clustered, similarity = self._calculate_measurement(clustering, next_cluster_id=cluster_id)

                sample_proportion = num_clustered / self.num_all_nodes

                self.measurements.append((sample_proportion, similarity))
                yield None, num_clustered, similarity, sample_proportion

    def save_measurements(self, file_path):
        """
        saves measurements as line json with header
        :param file_path:
        :type file_path: str
        """
        if self.measurements is None:
            raise GraphMeasurementsException("Please run get_measurements before save_measurements")
        with open(file_path, "w") as output_file:
            params = json.dumps({"measurement": self.similarity_algorithm, "shaving_method": self.shave_method.name})
            output_file.write(params + "\n")
            for sample_proportion, similarity in self.measurements:
                output_file.write(json.dumps({"fraction": sample_proportion, "similarity": similarity}) + "\n")
        print("Saved measurements!")
