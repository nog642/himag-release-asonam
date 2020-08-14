#!/usr/bin/env python3
import itertools

import numpy as np
from scipy.sparse import csr_matrix

ALGORITHMS = {"1", "2"}
# 1: sorted by flow to node
# 2: incremental shaving by flow to node


def _get_flow_graph(graph):
    """
    :param graph: square matrix representing graph
    :type graph: scipy.sparse.csr_matrix
    :return: square matrix representing flow graph
    :rtype: scipy.sparse.lil_matrix
    """
    # calculate full squared matrix
    flow_matrix = graph * graph

    # covert to LIL so zeroing the diagonal is more efficient
    flow_graph = flow_matrix.tolil()

    # zero the diagonal, since nodes should not have flow with themselves
    for i in range(graph.shape[0]):
        flow_graph[i, i] = 0

    return flow_graph


def get_density_sorted_cluster(nodes, edges, algo):
    """
    Get the information necessary to prune a graph (or subgraph).
    :param nodes: list of all node IDs (ints) in cluster.
    :type nodes: collections.Sequence[int]
    :param edges: list (iterator will work) of all edges, in the form
                  (nodeID_1, nodeID_2, weight). Edges with a node ID that is
                  not in `nodes` will be ignored.
    :type edges: collections.Iterable[(int, int, float)]
    :param algo: shaving algo to use (from ALGORITHMS)
    :type algo: str
    :return: list of node IDs sorted from least dense to most dense
    :rtype: tuple[int]
    """
    n = len(nodes)

    # get a reverse dict for old IDs (elements of `nodes`) to new IDs (indices
    #     of `nodes`). ID conversion is required so the graph can be
    #     represented in a matrix.
    new_ids = {old_id: i for i, old_id in enumerate(nodes)}

    rows = list()
    cols = list()
    data = list()
    for id1, id2, weight in edges:
        try:
            new_id1 = new_ids[id1]
            new_id2 = new_ids[id2]
        except KeyError:
            continue  # edge is not within subgraph; ignore it

        # TODO: if edges already contains both directions, bidirectional edges
        # TODO:     do not need to be added here for each edge

        rows.append(new_id1)
        cols.append(new_id2)
        data.append(weight)

        rows.append(new_id2)
        cols.append(new_id1)
        data.append(weight)

    graph = csr_matrix((data, (rows, cols)), shape=(n, n), dtype=np.float16)

    # sort the new IDs by density, and convert back to old IDs
    return tuple(nodes[i] for i in _ALGORITHM_FUNCTIONS[algo](graph))


def _get_density_sorted_graph_1(graph):
    """
    :param graph: square matrix representing graph
    :type graph: scipy.sparse.csr_matrix
    :return: A list of indices of the matrix that represents `graph` (each
             index represents a point) sorted from lowest density to highest
             density using node flow.
    """
    n = graph.shape[0]

    flow_graph = _get_flow_graph(graph)

    # calculate sum of flow of all edges for each point (by summing the rows of
    #     the flow matrix)
    node_densities = np.array(flow_graph.sum(axis=1).flat)

    sort_indices = node_densities.argsort()

    sorted_nodes = [None] * n
    for point_id, sort_index in enumerate(sort_indices):
        sorted_nodes[sort_index] = point_id

    return sorted_nodes


def _get_density_sorted_graph_2(graph):
    """
    :param graph: square matrix representing graph
    :type graph: scipy.sparse.csr_matrix
    :return: A list of indices of the matrix that represents `graph` (each
             index represents a point) sorted from lowest density to highest
             density by incrementally shaving by node flow.
    """
    flow_graph = _get_flow_graph(graph)

    # calculate sum of flow of all edges for each point (by summing the rows of
    #     the flow matrix)
    node_densities = dict(enumerate(flow_graph.sum(axis=1).flat))

    sorted_nodes = list()
    while node_densities:
        least_dense_node = min(node_densities, key=node_densities.get)

        sorted_nodes.append(least_dense_node)

        del node_densities[least_dense_node]

        # all nodes connected to the least dense node
        connected_nodes = graph[least_dense_node].nonzero()[1]

        for node_1, node_2 in itertools.combinations(connected_nodes, 2):
            flow = graph[node_1, node_2]

            if node_1 in node_densities:
                node_densities[node_1] -= flow
            if node_2 in node_densities:
                node_densities[node_2] -= flow

    assert not node_densities

    return sorted_nodes


_ALGORITHM_FUNCTIONS = {
    "1": _get_density_sorted_graph_1,
    "2": _get_density_sorted_graph_2
}
