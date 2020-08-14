#!/usr/bin/env python3
from collections import defaultdict
import enum
import math
from random import Random
from timeit import default_timer

from graphHDS.prune_cluster import ALGORITHMS as SHAVING_ALGORITHMS
from graphHDS.prune_cluster import get_density_sorted_cluster
from lib import read_csv, reverse_index


def read_genediver_graph_lab(filepath):
    """
    Read autoHDS clustering from output of Gene DIVER
    :param filepath:
    :return: clustering: dict: cluster ID -> set of node IDs (as strings)
             stabilities: dict: cluster ID -> cluster stability
    :rtype: (dict[int, set[str]], dict[int, float])
    """
    clustering = dict()
    stabilities = dict()
    with open(filepath) as f:
        next(f)  # skip header line)
        for line in map(str.strip, f):
            try:
                cluster_id, stability, _, node_id = line.split(",")
            except ValueError as e:
                raise RuntimeError("found bad row in graph lab file '{}': {}".format(filepath, line)) from e
            cluster_id = int(cluster_id)
            stability = float(stability)

            if cluster_id not in clustering:
                clustering[cluster_id] = set()
                stabilities[cluster_id] = stability
            clustering[cluster_id].add(node_id)

    return clustering, stabilities


class JudgedCsvReadingException(Exception):
    """
    Custom exception for read_judged_csv.
    """


def read_judged_csv(filepath, use_sample_column=False):
    """
    Read human-judged CSV.
    :param filepath: Judged CSV filepath
    :type filepath: str
    :return: labels: Judged labels
             cluster_stabilities:
    :rtype: (dict[int, dict[str, bool]], dict[int, float])
    """
    labels = defaultdict(dict)  # dict: cluster ID -> dict: node ID -> belongs
    cluster_stabilities = dict()

    required_fieldnames = ("cluster_id", "stability", "node_id", "label")
    if use_sample_column:
        required_fieldnames += ("sample",)

    for row_number, row in read_csv(filepath,
                                    required_fieldnames=required_fieldnames):

        try:
            cluster_id = int(row["cluster_id"])
        except ValueError as e:
            raise JudgedCsvReadingException(
                "unable to parse cluster ID {!r} as int (row {}))"
                .format(row["cluster_id"], row_number)
            ) from e

        belongs = row["label"]

        if belongs == "" or belongs == "x":
            continue

        if use_sample_column:
            if row["sample"] == "0":
                continue

        if cluster_id not in cluster_stabilities:
            cluster_stabilities[cluster_id] = float(row["stability"])

        node_id = row["node_id"]

        if belongs == "1":
            labels[cluster_id][node_id] = True
        elif belongs == "0":
            labels[cluster_id][node_id] = False

        else:
            raise JudgedCsvReadingException(
                "invalid 'belongs' label in row {}: {}"
                .format(row_number, belongs)
            )

    return dict(labels), cluster_stabilities


def _generate_clustering_edges(input_graph, clustering):
    """
    Generates clustering_edges for generate_density_sorted_clusters.
    :param input_graph: (node1, node2) -> weight
    :type input_graph: dict[(int, int), float]
    :param clustering: cluster_id -> set(node_ids)
    :type clustering: dict[int, set]
    :return: clustering_edges: dict: cluster_id -> edges
                               edges are list of (node1, node2, weight)
    :rtype: dict[int, list[(int, int, float)]]
    """
    # dictionary that has cluster id -> edges param in get_density_sorted_cluster
    clustering_edges = dict()
    for cluster_id in clustering.keys():
        clustering_edges[cluster_id] = list()
    clustering_ridx = reverse_index(clustering)

    for id1, id2 in input_graph:

        # clustering may have been filtered so all nodes are not necessarily there
        if id1 not in clustering_ridx or id2 not in clustering_ridx:
            # ignore edges with filtered nodes
            continue

        cluster_id_1 = clustering_ridx[id1]

        # only add if both are in same cluster
        if cluster_id_1 == clustering_ridx[id2]:
            # add in format of (node1, node2, weight)
            clustering_edges[cluster_id_1].append((id1, id2, input_graph[id1, id2]))

    return clustering_edges  # convert back to dict


def _generate_density_sorted_clusters(cluster_points, clustering_edges, shaving_algo):
    """
    Sorts clusters by density.
    :param cluster_points: cluster_id -> set of points
    :type cluster_points: dict[int, set[int]]
    :param clustering_edges: cluster_id -> list of (id1, id2, weight)
    :type clustering_edges: dict[int, collections.Iterable[(int, int, float)]]
    :param shaving_algo:
    :type shaving_algo: str
    :return: cluster_id -> sorted list of points
    :rtype: dict[int, tuple[int]]
    """
    print("Sorting by density...", end="", flush=True)
    start_time = default_timer()
    density_sorted_clusters = dict()
    for cluster_id, cluster in cluster_points.items():
        density_sorted_clusters[cluster_id] = get_density_sorted_cluster(
            nodes=tuple(cluster),
            edges=clustering_edges[cluster_id],
            algo=shaving_algo
        )
    print(" done. (time={:.3f} s)".format(default_timer() - start_time))
    return density_sorted_clusters


def _shave_density_sorted_clustering(sample_proportion, density_sorted_clusters):
    """
    shave clusters and return new clustering
    :param sample_proportion: Proportion of points to cluster
                              (1 - sample_proportion of points will be shaved).
                              This should be a float between 0 and 1.
    :type sample_proportion: float
    :param density_sorted_clusters:
    :type density_sorted_clusters: dict[int, collections.Sequence]
    :return:
    :rtype: dict[int, set[int]]
    """
    print("Shaving clustering...")
    # calculate shaved clustering from density-sorted clusters
    shaved_clustering = dict()
    for cluster_id, density_sorted_cluster in density_sorted_clusters.items():
        print("Before shaving: cluster {} , no. of points: {}"
              .format(cluster_id, len(density_sorted_cluster)))
        # only have sample_proportion of the density_sorted_cluster
        shaved_clustering[cluster_id] = set(density_sorted_cluster[int((1 - sample_proportion) *
                                                                       len(density_sorted_cluster)):])
        print("After shaving: cluster {} , no. of points: {}"
              .format(cluster_id, len(shaved_clustering[cluster_id])))

    print("Done shaving clustering.")
    return shaved_clustering


def convert_connections_to_edges(connections_graph):
    """
    convert the compact connections graph into expanded form for easier processing for some rare cases though this
    is slower. yeilds nodes filtered
    :param connections_graph:
    :return:
    """

    graph_ret = dict()

    for node_information in connections_graph:
        node_id_1 = node_information["id"]
        for node_id_2, weight in node_information["connections"]:
            # deduplicate edges a->b, b->a
            if node_id_1 < node_id_2:
                edge = (node_id_1, node_id_2)
            elif node_id_2 < node_id_1:
                edge = (node_id_2, node_id_1)
            else:
                continue

            # avoids duplicate edges already processed
            if edge not in graph_ret:
                graph_ret[edge] = weight

    return graph_ret


@enum.unique
class SHAVING_METHOD(enum.Enum):
    RAND = 1
    FLOW = 2


def shave_clustering(clustering, num_points_in_graph, method, fraction_kept, seed, input_graph=None, shaving_algo=None, debug=False):
    """
    Shave a clustering. Each cluster will be shaved by the same proportion,
    specified by fraction_kept.
    :param clustering: The clustering to shave (dict: cluster ID -> set of
                       (int) node IDs)
    :type clustering: dict[int, set[int]]
    :param num_points_in_graph: no. of points in original graph (clustering could have pruned points)
    :param method:
    :type method: SHAVING_METHOD
    :param fraction_kept: Fraction of nodes to be kept (between 0 and 1)
    :type fraction_kept: float
    :param seed: (only for random shaving) Random seed.
    :type seed: collections.Hashable
    :param input_graph: (only for flow-based shaving) Data graph.
    :type input_graph: dict[(int, int), float] | None
    :param shaving_algo: (only for flow-based shaving) Flow-shaving algo.
    :type shaving_algo: str | None
    :param debug:
    :return: Shaved clustering.
    :rtype dict[int, set[int]]
    """
    if not isinstance(clustering, dict):
        raise TypeError("clustering must be a dict")
    if not isinstance(method, SHAVING_METHOD):
        raise TypeError("method must be instance of SHAVING_METHOD enum")
    if not 0 < fraction_kept < 1:
        raise ValueError("sample_fraction must be between 0 and 1")

    num_points_clusters = sum(map(len, clustering.values()))

    # this would happen if pruning was done to clusters before clustering
    # you need to adjust the cluster's shaving fractions
    if num_points_in_graph > num_points_clusters:
        cluster_fraction_kept = fraction_kept * (num_points_in_graph/num_points_clusters)
        print("Adjusting fraction kept for individual clusters to account for "
              "pre-pruning from {} to {}...".format(fraction_kept, cluster_fraction_kept))
    else:
        cluster_fraction_kept = fraction_kept

    # pre-calculated resources needed by pruners, based on the type of pruner used
    flow_pre_calc = {
        # dict of edges by cluster
        "clustering_edges": None,
        # dict of sorted list of node ids by cluster, nodes within a cluster are sorted by shaving_algo's notion of
        # density. currently there are 2 options, 1 for non-incremental, 2 for incremental
        "density_sorted_cluster_points": None,
        # random seed needed by random pruner
        "random": None
    }

    shaved_clustering = dict()
    kept_cluster_count = 0
    ideal_kept_count = round(num_points_in_graph * fraction_kept)

    print("total number of points in graph: {}".format(num_points_in_graph))
    print("total number of points in clustering: {}".format(num_points_clusters))
    print("expected shaved points count: {}".format(ideal_kept_count))

    initial_kept_count = 0

    flow_pre_calc["random"] = Random(seed)

    for cluster_id, cluster in clustering.items():

        cluster_size = len(cluster)

        # don't allow empty or singleton clusters
        if cluster_size < 2:
            print("Warning: Not keeping cluster {} of size {}.".format(cluster_id, cluster_size))
            continue

        shaved_cluster_size = math.ceil(cluster_size * cluster_fraction_kept)

        # if the cluster size after shaving (or before) was 2 don't shave it any more
        if shaved_cluster_size < 2:
            shaved_cluster_size = 2

        if debug:
            print("Pruned cluster: {} from {} to {}".format(cluster_id, cluster_size, shaved_cluster_size))

        initial_kept_count += shaved_cluster_size

        if method == SHAVING_METHOD.RAND:
            shaved_cluster = flow_pre_calc["random"].sample(cluster, shaved_cluster_size)
        elif method == SHAVING_METHOD.FLOW:
            # lazy init
            if flow_pre_calc["density_sorted_cluster_points"] is None:
                if not isinstance(input_graph, dict):
                    raise TypeError("input_graph must be a dict for flow-based cluster"
                                    " shaving")
                if shaving_algo not in SHAVING_ALGORITHMS:
                    raise ValueError("shaving algo {!r} is invalid. Valid values: {}"
                                     .format(shaving_algo, SHAVING_ALGORITHMS))

                flow_pre_calc["clustering_edges"] = _generate_clustering_edges(
                    input_graph=input_graph,
                    clustering=clustering
                )

                flow_pre_calc["density_sorted_cluster_points"] = _generate_density_sorted_clusters(
                    cluster_points=clustering,
                    clustering_edges=flow_pre_calc["clustering_edges"],
                    shaving_algo=shaving_algo
                )
            # get the last k items as they are the highest "density" as per Neil's implementation
            shaved_cluster = set(flow_pre_calc["density_sorted_cluster_points"][cluster_id][-shaved_cluster_size:])
        else:
            raise NotImplementedError("SHAVING_METHOD.{} currently unsupported".format(method.name))

        shaved_clustering[cluster_id] = shaved_cluster
        kept_cluster_count += 1

        if debug:
            print("Shaved cluster {} from size {} to {}".format(cluster_id, cluster_size, shaved_cluster_size))

    # we can get discretization
    to_remove = initial_kept_count - ideal_kept_count

    # randomized algo to remove the error extra points from random clusters
    cluster_ids = list(shaved_clustering.keys())

    clusters_available_to_shave = set()

    # only prune from clusters that are > 2
    for cluster_id in cluster_ids:
        if len(shaved_clustering[cluster_id]) > 2:
            clusters_available_to_shave.add(cluster_id)

    print("{} points to be shaved further in second pass..".format(to_remove))
    print("{} of {} shaved clusters ready for further pruning...".format(len(clusters_available_to_shave), len(cluster_ids)))

    max_pruned_count = 0
    while to_remove > 0:
        if len(clusters_available_to_shave) == 0:
            print("Further pruning not possible, all clusters are length 2 now, maximum pruning already done!")
            break

        cluster_id = flow_pre_calc["random"].choice(list(clusters_available_to_shave))
        new_cluster_len = len(shaved_clustering[cluster_id]) - 1

        if new_cluster_len >= 2:
            if method == SHAVING_METHOD.RAND:
                shaved_clustering[cluster_id] = set(flow_pre_calc["random"].sample(shaved_clustering[cluster_id], new_cluster_len))
            elif method == SHAVING_METHOD.FLOW:
                shaved_clustering[cluster_id] = set(flow_pre_calc["density_sorted_cluster_points"][cluster_id][-new_cluster_len:])
            to_remove -= 1
        else:
            if debug:
                print("Cluster id: {} can no longer shrink, removing from prune set..".format(cluster_id))
            max_pruned_count += 1
            clusters_available_to_shave.remove(cluster_id)

    print("{} clusters pruned completely to 2 points max".format(max_pruned_count))

    # check to see if we reached our goal after max pruning, if not we need to now start throwing clusters away
    removed_cluster_count = 0
    while to_remove > 0:
        cluster_id = flow_pre_calc["random"].choice(cluster_ids)
        print("Removing cluster: {} of size: {}".format(cluster_id, len(shaved_clustering[cluster_id])))
        del shaved_clustering[cluster_id]
        cluster_ids.remove(cluster_id)
        to_remove -= 2
        removed_cluster_count += 1

        # no more clusters left ! this will only happen if desired no. of points is 0
        if len(shaved_clustering) == 0:
            break

    print("{} clusters removed completely to get the right number of points...".format(removed_cluster_count))
    # recount total no. of points kept
    kept_count = sum(map(len, shaved_clustering.values()))

    print("kept {} points in {} clusters after shaving, initial kept count was: {}, ideal node count: {}"
          .format(kept_count, kept_cluster_count, initial_kept_count, ideal_kept_count))
    return shaved_clustering
