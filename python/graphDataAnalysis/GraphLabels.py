#!/usr/bin/env python3
"""
GraphLabels actually has a reason for being in a separate file, because if it
was not (and was in graphDataAnalysis.GraphMeasurements instead), it would
cause a circular import between graphDataAnalysis.GraphMeasurements and
measurements.similarity.
"""
from collections import defaultdict
import enum
import itertools
import json
import os
import re

from lib import IdentityDict, reverse_dict, warn
from util import read_judged_csv


class GraphLabels:
    """
    Attributes:
        label_format: GraphDataStager.LABEL_FORMAT enum saying what the label format is

    if label_format is LABEL_FORMAT.EDGE_BASED:
        Attributes:
            edge_weights: dictionary
                              keys = pairs of node IDs, sorted
                              value = weight of the edge, as a float

    if label_format is LABEL_FORMAT.CLUSTER_BASED:
        Attributes:
            clusters: dictionary
                          keys = cluster IDs
                          value = set of node IDs of nodes in the cluster
            background: list of node IDs of background nodes
    """

    @enum.unique
    class LABEL_FORMAT(enum.Enum):
        EDGE_BASED = 1
        CLUSTER_BASED = 2

    LABEL_FORMAT_HEADERS = {
        LABEL_FORMAT.EDGE_BASED: "edge-based labels:",
        LABEL_FORMAT.CLUSTER_BASED: "cluster-based labels:"
    }

    LABEL_FORMAT_HEADER_VALUES = reverse_dict(LABEL_FORMAT_HEADERS)

    def __init__(self, data_set_dir, contiguity_mapping=None, human_cluster_labels=False):
        """
        :param data_set_dir:
        :type data_set_dir: str
        :param contiguity_mapping: dict: GDA node ID -> contiguous node ID
        :type contiguity_mapping: dict[int, int]
        :param human_cluster_labels:
        :type human_cluster_labels: bool
        """
        self.label_format = None
        self.edge_weights = None
        self.clusters = None
        self.background = None

        labels_path = os.path.join(data_set_dir, "labels")

        if os.path.isfile(labels_path):

            if human_cluster_labels:
                raise ValueError("'{}' is a file. Expected a directory with "
                                 "human cluster labels.".format(labels_path))

            self.load_gda_labels(labels_path, contiguity_mapping)

        elif os.path.isdir(labels_path):

            if not human_cluster_labels:
                pass  # TODO: warn

            self.load_human_cluster_labels(
                labels_dir_path=labels_path,
                gda_id_mapping=GraphLabels.load_gda_id_mapping(
                    os.path.join(data_set_dir, "gda_id_mapping.tsv")
                )
            )

        else:
            raise ValueError("No such file or directory: {}".format(labels_path))

    def load_gda_labels(self, labels_file_path, contiguity_mapping=None):
        if contiguity_mapping is None:
            contiguity_mapping = IdentityDict()

        with open(labels_file_path) as f:
            self.label_format = GraphLabels.LABEL_FORMAT_HEADER_VALUES[next(f).strip()]

            if self.label_format is GraphLabels.LABEL_FORMAT.EDGE_BASED:
                self.edge_weights = dict()
                for line in map(str.strip, f):
                    if not line:
                        continue

                    weight, node1, node2 = line.split("\t")
                    weight = float(weight)
                    node1 = contiguity_mapping[int(node1)]
                    node2 = contiguity_mapping[int(node2)]
                    if node1 > node2:
                        self.edge_weights[node2, node1] = weight
                    else:
                        self.edge_weights[node1, node2] = weight

            elif self.label_format is GraphLabels.LABEL_FORMAT.CLUSTER_BASED:
                clusters = defaultdict(set)
                self.background = set()
                for line in map(str.strip, f):
                    if not line:
                        continue

                    node_id, cluster_id = line.split("\t")
                    node_id = contiguity_mapping[int(node_id)]

                    if cluster_id == "b":
                        self.background.add(node_id)
                        continue
                    cluster_id = int(cluster_id)

                    clusters[cluster_id].add(node_id)

            else:
                raise AssertionError  # unreachable state

        if self.label_format is GraphLabels.LABEL_FORMAT.CLUSTER_BASED:
            self.clusters = dict(clusters)

    @staticmethod
    def load_gda_id_mapping(gda_id_mapping_path):
        """
        :param gda_id_mapping_path:
        :type gda_id_mapping_path: str
        :return: dict: external node ID -> GDA node ID
        :rtype: dict[str, int]
        """
        gda_id_mapping = dict()
        with open(gda_id_mapping_path) as f:
            for line in map(str.strip, f):
                external_str_node_id, gda_node_id = line.split("\t")
                gda_id_mapping[external_str_node_id] = int(gda_node_id)
        return gda_id_mapping

    def load_human_cluster_labels(self, labels_dir_path, gda_id_mapping):
        """
        :param labels_dir_path:
        :type labels_dir_path: str
        :param gda_id_mapping: external node ID -> GDA node ID
        :type gda_id_mapping: dict[str, int]
        """

        judged_csv_filenames = list()
        cluster_filter_filenames = list()
        for filename in os.listdir(labels_dir_path):

            label_set_match = re.fullmatch(r"for_judging_([a-z]+)\.[a-z0-9.]+ - [a-z0-9._]+\.csv", filename)
            if label_set_match is not None:
                algo = label_set_match.group(1)
                judged_csv_filenames.append((filename, algo))
                continue

            filter_file_match = re.fullmatch(r"for_judging\.([a-z]+)\.cluster_ids\.[a-z_]+", filename)
            if filter_file_match:
                algo = filter_file_match.group(1)
                cluster_filter_filenames.append((filename, algo))
                continue

            warn("Ignoring unrecognized file in human labels dir: {}"
                 .format(filename), Warning)

        # load filter cluster IDs
        filter_cluster_ids = dict()
        for cluster_filter_filename, filter_algo in cluster_filter_filenames:
            with open(os.path.join(labels_dir_path, cluster_filter_filename)) as f:
                file_filter_cluster_ids = set(map(int, f))
            if filter_algo in filter_cluster_ids:
                filter_cluster_ids[filter_algo].update(file_filter_cluster_ids)
            else:
                filter_cluster_ids[filter_algo] = file_filter_cluster_ids
        if cluster_filter_filenames:
            del file_filter_cluster_ids

        total_stats_must_link_overwrite = 0
        total_stats_cannot_link_ignored = 0
        self.label_format = GraphLabels.LABEL_FORMAT.EDGE_BASED
        self.edge_weights = dict()
        for judged_csv_filename, label_set_algo in judged_csv_filenames:

            judged_csv_filepath = os.path.join(labels_dir_path, judged_csv_filename)

            print("reading {!r}...".format(judged_csv_filepath))

            # dict: cluster ID -> dict: node ID -> belongs
            labels, _ = read_judged_csv(judged_csv_filepath)
            del _

            if label_set_algo in filter_cluster_ids:
                for cluster_id in labels:
                    if cluster_id not in filter_cluster_ids[label_set_algo]:
                        del labels[cluster_id]

            file_stats_num_edges = 0
            file_stats_must_link = 0
            file_stats_cannot_link = 0
            file_stats_must_link_overwrite = 0
            file_stats_cannot_link_ignored = 0

            for cluster_dict in labels.values():

                # label all possible edges between nodes the belong in cluster as ML
                sorted_belonging_gda_node_ids = sorted(
                    gda_id_mapping[node_id]
                    for node_id, belongs in cluster_dict.items()
                    if belongs
                )
                for edge in itertools.combinations(sorted_belonging_gda_node_ids, 2):
                    if edge in self.edge_weights and not self.edge_weights[edge]:
                        file_stats_must_link_overwrite += 1
                    self.edge_weights[edge] = 1
                    file_stats_num_edges += 1
                    file_stats_must_link += 1

                # label edges between nodes that don't belong and all other labeled nodes as CL
                for node_id_1, belongs in cluster_dict.items():
                    if belongs:
                        continue

                    gda_node_id_1 = gda_id_mapping[node_id_1]

                    for node_id_2 in sorted_belonging_gda_node_ids:

                        gda_node_id_2 = gda_id_mapping[node_id_2]

                        if gda_node_id_1 < gda_node_id_2:
                            edge = (gda_node_id_1, gda_node_id_2)
                        else:
                            edge = (gda_node_id_2, gda_node_id_1)

                        if edge in self.edge_weights and self.edge_weights[edge]:
                            file_stats_cannot_link_ignored += 1
                            continue
                        self.edge_weights[edge] = 0
                        file_stats_num_edges += 1
                        file_stats_cannot_link += 1

            # print file stats
            print("stats for {}: {}".format(
                judged_csv_filename,
                json.dumps({
                    "num_edges": file_stats_num_edges,
                    "must_link": file_stats_must_link,
                    "cannot_link": file_stats_cannot_link,
                    "must_link_overwrite": file_stats_must_link_overwrite,
                    "cannot_link_ignored": file_stats_cannot_link_ignored
                })
            ))

            total_stats_must_link_overwrite += file_stats_must_link_overwrite
            total_stats_cannot_link_ignored += file_stats_cannot_link_ignored

        # gather total stats
        total_stats_must_link = 0
        total_stats_cannot_link = 0
        for weight in self.edge_weights.values():
            if weight:
                total_stats_must_link += 1
            else:
                total_stats_cannot_link += 1

        # print total stats
        print("total stats: {}".format(json.dumps({
            "num_edges": len(self.edge_weights),
            "must_link": total_stats_must_link,
            "cannot_link": total_stats_cannot_link,
            "must_link_overwrite": total_stats_must_link_overwrite,
            "cannot_link_ignored": total_stats_cannot_link_ignored
        })))
