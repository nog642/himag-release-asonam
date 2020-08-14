#!/usr/bin/env python3
from collections import defaultdict


def write_metis_input(filepath, graph, num_nodes, num_edges, node_weights=None):
    """
    Write a graph to a file in the format METIS wants as input.
    This function can take the graph as a stream, so as to not waste memory.
    This requires manually passing the number of nodes and the number of edges
    in the graph.
    :param filepath:
    :type filepath: str
    :param graph: Iterable over edges. Each edge is tuple of ((node ID 1,
                  node ID 2), weight). Weight must be an integer. Node IDs must
                  be 1-indexed and contiguous.
    :type graph: collections.Iterable[((int, int), int)]
    :param num_nodes:
    :type num_nodes: int
    :param num_edges:
    :type num_edges: int
    """
    node_connections = defaultdict(set)  # node_id -> {(connected_node_id, weight)}
    edge_count = 0
    for edge, weight in graph:
        node_id_1, node_id_2 = edge

        node_connections[node_id_1].add((node_id_2, weight))
        node_connections[node_id_2].add((node_id_1, weight))

        for node_id in edge:
            if node_id > num_nodes:
                raise ValueError("node ID {} is impossible in graph with {} nodes")

        edge_count += 1

    if num_edges != edge_count:
        raise ValueError("num_edges is {} but {} edges were passed".format(num_edges, edge_count))

    with open(filepath, "w") as output_file:
        output_file.write("{}\t{}\t1\n".format(num_nodes, num_edges))
        for node_id in range(1, num_nodes + 1):
            if node_id in node_connections:
                for connection in node_connections[node_id]:
                    node_id, weight = connection
                    output_file.write("{}\t{}\t".format(node_id, weight))
            output_file.write("\n")
