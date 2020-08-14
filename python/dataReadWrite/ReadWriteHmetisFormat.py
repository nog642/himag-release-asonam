#!/usr/bin/env python3
from abc import ABCMeta
from collections import defaultdict
import os
import re

from dataReadWrite.read_hmetis_output import read_hmetis_output
from dataReadWrite.ReadWriteAbstract import ReadWriteAbstract


class ReadWriteHmetisFormat(ReadWriteAbstract, metaclass=ABCMeta):

    def write_graph(self, graph, num_nodes, num_edges, node_weights=None):
        """

        :param graph: connections format graph
        :param num_nodes:
        :param num_edges:
        :param node_weights:
        :return:
        """

        file_path = os.path.join(self.algo_staging_dir, "graph")

        # weight is float; hMETIS needs integer value. Multiply by constant.
        # hMETIS node IDs are 1-indexed, so we add 1 to the node IDs
        # graph = (((node_id_1 + 1, node_id_2 + 1), round(weight * 100))
        #
        # for node_id2, node_information in graph:
        #     for node_id1, weight in node_information["connections"]

        edges_found = set()

        with open(file_path, "w") as f:
            if node_weights is None:
                graph_type = 1  # weighted hyperedges
            else:
                graph_type = 11  # weighted hyperedges and vertices
            f.write("{}\t{}\t{}\n".format(num_edges, num_nodes, graph_type))
            for node_information in graph:
                node_id_1 = node_information["id"]
                for node_id_2, weight in node_information["connections"]:
                    # deduplicate edges a->b, b->a
                    if node_id_1 < node_id_2:
                        node_a = node_id_1
                        node_b = node_id_2
                        edge = str(node_id_1)+ "." + str(node_id_2)
                    else:
                        node_a = node_id_2
                        node_b = node_id_1
                        edge = str(node_id_2) + "." + str(node_id_1)
                    if edge not in edges_found:
                        edges_found.add(edge)
                        # if not round(weight * 100) and round(weight * 1000):
                        #     print("uh oh")
                        f.write("{}\t{}\t{}\n".format(round(weight * 100), node_a + 1, node_b + 1))

            # TODO sheshank this code is completely broken as the ordering of node weights is missing
            # you are writing weights in random order!!!
            if node_weights is not None:
                raise NotImplementedError("# TODO sheshank this code is completely broken as the ordering of node weights is missing")
                #for _, weight in node_weights.items():
                #    f.write("{}\n".format(weight))

    def read_clustering(self):
        valid_filepaths = list()
        for name in os.listdir(self.algo_staging_dir):
            if re.fullmatch(self.FILENAME_REGEX, name):
                path = os.path.join(self.algo_staging_dir, name)
                if os.path.isfile(path):
                    valid_filepaths.append(path)

        if not valid_filepaths:
            raise Exception("no output file for {} found in '{}'".format(self.ALGORITHM_DISPLAY_NAME,
                                                                         self.algo_staging_dir))
        elif len(valid_filepaths) > 1:
            raise Exception("more than one output file for {} found in "
                            "'{}':\n{}".format(
                                self.ALGORITHM_DISPLAY_NAME,
                                self.algo_staging_dir,
                                ', '.join(map(os.path.basename,
                                              valid_filepaths))
                            ))

        clustering = defaultdict(set)
        for hmetis_node_id, hmetis_cluster_id in read_hmetis_output(valid_filepaths[0]):
            # hMETIS uses 1-indexed node IDs, but those need to be converted
            #     back to 0-indexed for use in this program by subtracting 1.
            # hMETIS cluster IDs are 0-indexed. The cluster IDs do not actually
            #     matter, only the clusters do, so adding 1 does no harm. This
            #     avoids having a cluster 0 in the output CSV for this script,
            #     which might cause unnecessary confusion.
            clustering[hmetis_cluster_id + 1].add(hmetis_node_id - 1)

        return dict(clustering)
