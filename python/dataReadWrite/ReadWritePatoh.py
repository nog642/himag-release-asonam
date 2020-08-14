#!/usr/bin/env python3
import os

from dataReadWrite.ReadWriteAbstract import ReadWriteAbstract
from dataReadWrite.ReadWriteHmetisFormat import ReadWriteHmetisFormat


class ReadWritePatoh(ReadWriteAbstract):
    """
    Has same output format as Hmetis, but different input format.
    """

    ALGORITHM_DISPLAY_NAME = "PaToH"
    FILENAME_REGEX = r"graph\.part\.[0-9]+"
    WEIGHTED = False

    def __init__(self, algo_staging_dir):
        super().__init__(algo_staging_dir)

    # Has different input format than hmetis
    def write_graph(self, graph, num_nodes, num_edges, node_weights=None):
        num_pins = num_edges * 2  # Since each edge has 2 vertices
        with open(os.path.join(self.algo_staging_dir, "graph"), "w") as f:

            # [base value in indexing] [num nodes] [num edges] [sum of vertices in all edges (pins)]
            #           [graph type (2 for weighted edges)]
            f.write("1\t{}\t{}\t{}\t2\n".format(num_nodes, num_edges, num_pins))

            edges_found = set()
            for node_information in graph:
                node_id_1 = node_information["id"]
                for node_id_2, weight in node_information["connections"]:

                    # deduplicate edges a->b, b->a
                    if node_id_1 < node_id_2:
                        node_a = node_id_1
                        node_b = node_id_2
                        edge = str(node_id_1) + "." + str(node_id_2)
                    else:
                        node_a = node_id_2
                        node_b = node_id_1
                        edge = str(node_id_2) + "." + str(node_id_1)

                    if edge not in edges_found:
                        edges_found.add(edge)
                        f.write("{}\t{}\t{}\n".format(round(weight * 100), node_a + 1, node_b + 1))

    # hMETIS and PaToH output formats are identical
    read_clustering = ReadWriteHmetisFormat.read_clustering
