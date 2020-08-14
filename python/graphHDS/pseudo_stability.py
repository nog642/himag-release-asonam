#!/usr/bin/env python3
import numpy as np
from scipy.sparse import csr_matrix
from lib import comb


def get_algo_cluster_stabilities(graph, cluster_points):
    """
    :param graph:
    :type graph: dict[(int, int), float]
    :param cluster_points:
    :type cluster_points: dict[int, collections.Collection[int]]
    :return:
    :rtype: dict[int, float]
    """
    # get a reverse dict for old IDs (elements of `nodes`) to new IDs (indices
    #     of `nodes`). ID conversion is required so the graph can be
    #     represented in a matrix.
    node_id_mapping = dict()
    clustering_ridx = dict()
    for cluster_id, cluster in cluster_points.items():

        # each cluster gets its own set of IDs, 0-indexed.
        for i, old_id in enumerate(cluster):
            node_id_mapping[old_id] = i
            clustering_ridx[old_id] = cluster_id

    # dict: cluster ID -> (rows, cols data)
    cluster_csr_data = {cluster_id: (list(), list(), list())
                        for cluster_id in cluster_points}

    for (node_id_1, node_id_2), weight in graph.items():
        if (node_id_1 not in clustering_ridx) or (node_id_2 not in clustering_ridx):
            # sometimes the clustering passed is shaved so some nodes in the graph aren't in the clustering_ridx
            continue
        cluster_id = clustering_ridx[node_id_1]
        if clustering_ridx[node_id_2] != cluster_id:
            # the nodes are in different clusters, so the edge does not belong to a cluster
            continue

        node_node_id_1 = node_id_mapping[node_id_1]
        node_node_id_2 = node_id_mapping[node_id_2]

        rows, cols, data = cluster_csr_data[cluster_id]

        # Unweighted graph needs both directions. graph dict should not contain duplicate edges.

        rows.append(node_node_id_1)
        cols.append(node_node_id_2)
        data.append(weight)

        rows.append(node_node_id_2)
        cols.append(node_node_id_1)
        data.append(weight)

    cluster_matrices = dict()
    cluster_sizes = dict()
    for cluster_id, (rows, cols, data) in cluster_csr_data.items():
        n = len(cluster_points[cluster_id])
        cluster_matrices[cluster_id] = csr_matrix((data, (rows, cols)), shape=(n, n), dtype=np.float16)
        cluster_sizes[cluster_id] = n
    del cluster_csr_data

    stabilities = dict()
    for cluster_id, cluster_matrix in cluster_matrices.items():
        # calculate full squared matrix
        flow_matrix = cluster_matrix * cluster_matrix

        if cluster_sizes[cluster_id] < 2:
            stabilities[cluster_id] = 0.0
        else:
            stabilities[cluster_id] = float(flow_matrix.sum()) / comb(cluster_sizes[cluster_id], 2)

    # no need to convert node IDs back because cluster IDs are all that are returned

    return stabilities
