#!/usr/bin/env python3
from collections import defaultdict
import itertools
import json
import os
from warnings import warn

from lib import IdentityDict, reverse_dict


class ClusterProcessor:

    def __init__(self, sorted_labels, node_map, sort_indices):
        """
        :param sorted_labels: Label matrix in transposed form (not like plot).
        :type sorted_labels: np.ndarray
        :param node_map: dict: original ID -> graphHDS index
        :type node_map: dict[int, int]
        :param sort_indices: The label matrix's columns (corresponding to
                             nodes) have been sorted. This parameter indicates
                             exactly which row went where during that sorting,
                             so that it can be reversed. The position in this
                             sequence represents the position in the sorted
                             matrix, and the value in this sequence represents
                             the original position in the unsorted matrix (and
                             therefore which node that column corresponds to).
                             Everything is 0-indexed.
        :type sort_indices: collections.Sequence[int]
        """
        self.combined_labels, self.level_map, self.new_levels = self.cluster_label_matrix(
            self._initial_relabel(sorted_labels)
        )

        # TODO: make idx_to_id the parameter instead of its reverse dict
        if node_map is None:
            self.idx_to_id = IdentityDict()
        else:
            self.idx_to_id = reverse_dict(node_map)

        self.sort_indices = sort_indices

    @staticmethod
    def _initial_relabel(label_matrix):
        """
        Relabel the label matrix so different levels don't share cluster IDs.
        :param label_matrix:
        :return:
        """
        label_matrix = label_matrix.copy()
        num_levels, num_points = label_matrix.shape
        cluster_id_gen = itertools.count(1)
        for i in range(num_levels):
            cluster_id_mapping = {old_cluster_id: next(cluster_id_gen)
                                  for old_cluster_id in sorted(set(label_matrix[i]))}
            for j in range(num_points):
                old_cluster_id = label_matrix[i, j]
                if old_cluster_id:
                    label_matrix[i, j] = cluster_id_mapping[old_cluster_id]
        return label_matrix

    def save_clusters_jsonl(self, fpath):
        """
        Saves the .clusters.jsonl file using original IDs.
        :param fpath: Path to file to save.
        """

        if not fpath.endswith(".clusters.jsonl"):
            warn("save_cluster_jsonl fpath should have '.clusters.jsonl' file "
                 "extension; got '{}' instead".format(fpath))

        with open(fpath, "w") as f:
            for i in self.new_levels:  # iterate over levels
                for j in range(self.combined_labels.shape[1]):  # iterate over points/nodes
                    if self.combined_labels[i, j] in self.new_levels[i]:
                        f.write(json.dumps({
                            "level": self.level_map[self.combined_labels[i, j]],
                            "id": self.idx_to_id[self.sort_indices[j]],
                            "label": int(self.combined_labels[i, j])  # numpy int is not JSON serializable
                        }) + "\n")

    def save_full_label_matrix_jsonl(self, fpath):
        """
        Saves all the data in the relabeled label matrix as a line json.
        Node IDs are converted back to the original IDs in graph.jsonl.
        :param fpath: Path to line json.
        """
        with open(fpath, "w") as f:
            for i in range(len(self.combined_labels)):  # iterate over levels
                for j in range(self.combined_labels.shape[1]):  # iterate over points/nodes
                    f.write(json.dumps({
                        "level": i,
                        "id": self.idx_to_id[self.sort_indices[j]],
                        "label": int(self.combined_labels[i, j])
                    }) + "\n")

    def save_genediver_data(self, output_dir, point_mapping, cluster_labels_file):
        """
        Produces .dsc (point descriptions), hds hierarchy (relabeled), and
        sorted.idx (index of hds sort ordering).
        Used by gene DIVER.
        :param output_dir:
        :type output_dir: str
        :param point_mapping:
        :type point_mapping: collections.Mapping[int, int | str] | None
        :param cluster_labels_file:
        :type cluster_labels_file: str | None
        """

        hds_file = os.path.join(output_dir, "graph.hds")
        sorted_idx_file = os.path.join(output_dir, "graph_sorted.idx")
        dsc_file = os.path.join(output_dir, "graph.dsc")

        # Create an empty data file if not already produced by data producers
        #     as it is needed for gene diver to work
        with open(os.path.join(output_dir, "graph.txt"), "w"):
            pass

        # used by gene diver
        gene_diver_cluster_labels_file = os.path.join(
            output_dir,
            "graph_cluster_labels.txt"
        )

        # load point cluster labels into memory note that these are sparse
        point_cluster_labels = dict()
        if cluster_labels_file is not None and os.path.isfile(cluster_labels_file):
            with open(cluster_labels_file) as clf:
                for line in clf:
                    label_row = json.loads(line)
                    point_id = label_row["id"]
                    point_label = label_row["label"]
                    point_cluster_labels[point_id] = point_label

        if len(point_cluster_labels) > 0:
            with open(gene_diver_cluster_labels_file, "w") as gf:
                for j in range(self.combined_labels.shape[1]):
                    graph_hds_original_id = self.idx_to_id[self.sort_indices[j]]
                    if point_mapping is None:
                        input_data_original_str_id = graph_hds_original_id
                    else:
                        input_data_original_str_id = point_mapping[graph_hds_original_id]

                    if input_data_original_str_id in point_cluster_labels:
                        gf.write("{},{}\n".format(
                            input_data_original_str_id,
                            point_cluster_labels[input_data_original_str_id])
                        )
                    else:
                        gf.write("{},0\n".format(input_data_original_str_id))

        with open(dsc_file, "w") as df, open(hds_file, "w") as hf, open(sorted_idx_file, "w") as sf:
            for j in range(self.combined_labels.shape[1]):  # iterate over points/nodes

                # .hds file has rows of hds levels for each point, these are
                #     not re-labeled yet
                hf.write(" ".join(map(str, self.combined_labels[:, j])) + "\n")

                # idx file has ordering 1,2,3,.... 1 indexed required by gene
                #     diver and since this data is already sorted the index
                #     file is just 1,2,3... so really this is a simple trick to
                #     make .hds index trivial by making it presorted
                sf.write("{}\n".format(j + 1))

                # description file contain original string identifiers of each
                #     point in .hds file in exactly the same order
                graph_hds_original_id = self.idx_to_id[self.sort_indices[j]]
                if point_mapping is not None:
                    input_data_original_str_id = point_mapping[graph_hds_original_id]
                else:
                    input_data_original_str_id = graph_hds_original_id
                df.write("{}\n".format(input_data_original_str_id))

    def save_mapped_clusters_jsonl(self, fpath, point_id_mapping):
        """
        Saves the mapped .clusters.jsonl file using mapped point IDs.
        :param fpath: Path to file to save.
        :param point_id_mapping:
        """
        with open(fpath, "w") as f:
            for i in self.new_levels:  # iterate over levels
                for j in range(len(self.combined_labels[i])):  # iterate over points/nodes
                    if self.combined_labels[i, j] in self.new_levels[i]:
                        f.write(json.dumps({
                            "level": self.level_map[self.combined_labels[i, j]],
                            "id": point_id_mapping[self.idx_to_id[self.sort_indices[j]]],
                            "label": int(self.combined_labels[i, j])  # numpy int is not JSON serializable
                        }) + "\n")

    def get_cluster_stabilities(self):
        """
        :return:
        :rtype: dict[int, int]
        """
        # TODO: replace with log formula rather than counting levels
        stabilities = defaultdict(int)
        for level in self.combined_labels:
            for cluster in set(level):
                if cluster == 0:
                    # don't want to calculate 'stability' of the background
                    continue
                stabilities[int(cluster)] += 1
        return dict(stabilities)

    @staticmethod
    def save_cluster_stabilities(stabilities, fpath):
        """
        :param stabilities: Map from cluster-ID to cluster stability.
        :param fpath: Path to file to save.
        """
        # TODO: get rid of this since it does not use the log formula and therefore causes confusion

        with open(fpath, "w") as f:
            for cluster in stabilities:
                f.write(json.dumps({
                    "label": cluster,
                    "stability": stabilities[cluster]
                }) + "\n")

    @staticmethod
    def cluster_label_matrix(labels):
        """
        Combine multi-level clusters.
        :param labels: Label matrix in transposed form (not like plot).
        :return: labels: Input label matrix with multi-level clusters renamed to
                         have single ID.
                 level_map: Map from cluster-IDs to the level used in .clusters
                            file.
                 new_levels: Map from level (label matrix index) where clusters
                             branch to a set of new clusters formed at that
                             level.
        """

        # Don't want to modify the object passed in. Will return new label
        #     matrix instead.
        labels = labels.copy()

        num_levels, num_points = labels.shape

        # Generators for unique IDs.
        new_labels_counter = itertools.count(1)
        new_level_counter = itertools.count(1)

        # map: (cluster-ID) -> (set of points in the cluster)
        cluster_points = defaultdict(set)

        # map: (cluster-ID) -> (level used in .clusters file)
        level_map = dict()

        # map: (level (label matrix index) where clusters branch) -> (set of new clusters formed at that level)
        new_levels = defaultdict(set)

        for i in range(num_levels):  # iterate over levels

            if i > 0:

                # map: (cluster-ID) -> (set of cluster-IDs from the next
                #                       level that include the same
                #                       nodes/points)
                cluster_map = defaultdict(set)

                for j in range(num_points):  # iterate over points/nodes
                    cluster_map[labels[i - 1, j]].add(labels[i, j])
                    cluster_points[labels[i, j]].add(j)
                new = list()
                for old_cluster in cluster_map:
                    new_clusters = [c for c in cluster_map[old_cluster]
                                    if c != 0]
                    if len(new_clusters) > 1:
                        new.extend(new_clusters)
                    elif len(new_clusters) == 1:
                        # the cluster only shrinks; doesn't split
                        # rename column i cluster with i-1 label
                        for j in cluster_points[new_clusters[0]]:
                            labels[i, j] = old_cluster
                        del cluster_points[new_clusters[0]]
            else:
                new = labels[i]
            new = sorted(set(new))

            # map: (old cluster-ID) -> (new cluster-ID)
            label_map = dict()

            for old_label in new:
                new_label = next(new_labels_counter)
                label_map[old_label] = new_label
                new_levels[i].add(new_label)

            if new:
                new_level = next(new_level_counter)
                for j in range(num_points):
                    old_label = labels[i, j]
                    if old_label in label_map:
                        labels[i, j] = label_map[old_label]
                for cluster_id in new:
                    level_map[label_map[cluster_id]] = new_level

        return labels, level_map, new_levels
