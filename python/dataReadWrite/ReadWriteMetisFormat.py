#!/usr/bin/env python3
from abc import ABCMeta
import os

from dataReadWrite.ReadWriteAbstract import ReadWriteAbstract
from dataReadWrite.ReadWriteHmetisFormat import ReadWriteHmetisFormat
from collections import defaultdict


class ReadWriteMetisFormat(ReadWriteAbstract, metaclass=ABCMeta):
    """
    Note: This class will read write based on the Metis input/output formats. Currently, metis itself isn't being used,
    only other algorithms that use metis input/output formats are being used.
    """

    def write_graph(self, graph, num_nodes, num_edges, node_weights=None):
        """
        :param graph:
        :param num_nodes:
        :param node_weights:
        :return:
        """

        filepath=os.path.join(self.algo_staging_dir, "graph")

        node_connections = defaultdict(set)  # node_id -> {(connected_node_id, weight)}
        unique_edges = set()
        for node_information in graph:
            node_id_1 = node_information["id"]+1
            if node_id_1 > num_nodes:
                raise ValueError("node ID {} is impossible in graph with {} nodes".format(node_id_1, num_nodes))
            for node_o, weight_o in node_information["connections"]:
                weight = round(weight_o*100)
                node_id_2 = node_o+1

                if node_id_2 > num_nodes:
                    raise ValueError("node ID {} is impossible in graph with {} nodes".format(node_id_2, num_nodes))

                if node_id_1 < node_id_2:
                    edge_id = str(node_id_1) + "." + str(node_id_2)
                elif node_id_2 < node_id_1:
                    edge_id = str(node_id_2) + "." + str(node_id_1)
                else:
                    continue
                if edge_id not in unique_edges:
                    unique_edges.add(edge_id)

                node_connections[node_id_1].add((node_id_2, weight))
                node_connections[node_id_2].add((node_id_1, weight))

        if len(unique_edges) != num_edges:
            raise Exception("Number of edges passed: {} not equal to number of edges found: {}".format(num_edges, len(unique_edges)))
        with open(filepath, "w") as output_file:
            output_file.write("{}\t{}\t1\n".format(num_nodes, num_edges))
            for node_id in range(1, num_nodes + 1):
                if node_id in node_connections:
                    output_nbrs = list()
                    for connection in node_connections[node_id]:
                        node_id_nbr, weight = connection
                        output_nbrs.append(str(node_id_nbr))
                        output_nbrs.append(str(weight))
                    output_file.write("{}\n".format("\t".join(output_nbrs)))
                else:
                    output_file.write("\n")

    # hMETIS and METIS output formats are identical
    read_clustering = ReadWriteHmetisFormat.read_clustering
