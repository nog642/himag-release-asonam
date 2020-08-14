#!/usr/bin/env python3
"""
Judged measurements.

A config json and all the necessary files all go in one directory that gets passed as a CLI argument.

The config json looks like this:
{
    "total_num_nodes": 89678,
    "dataset": "Marketing: Education",
    "data": [
        {
            "algo": "autohds-g",
            "judged_file": "for_judging_genediver.n50 - for_judging_genediver.n50.csv",
            "topk_cluster_ids_file": "for_judging.genediver.cluster_ids.top_k"
        },
        {
            "algo": "hmetis",
            "judged_file": "for_judging_hmetis.jt0.3 - for_judging_hmetis.csv",
            "topk_cluster_ids_file": "for_judging.hmetis.cluster_ids.top_k",
            "shaving_method": "flow"
        },
        ...
    ]
}

"""
from collections import defaultdict
import itertools
import json
import operator
import os
from timeit import default_timer

from graphDataAnalysis.GraphDataPlotter import GraphDataPlotter
from graphDataAnalysis.GraphLabels import GraphLabels
from measurements.GraphSimilarity import GraphSimilarity
from util import read_judged_csv

# minimum number of labels for a cluster to be included.
MIN_CLUSTER_LABELS = 0

# Assumes all unlabeled edges are cannot-link (ie edges between clusters) using
#     the num_all_points parameter of GraphSimilarity.
# Edge-ARI is screwed up if this is False.
ASSUME_CANNOTLINK = True

MODIFY_LABELS_FOR_TOPK = False


def remove_underlabeled_clusters(labels, topk_filters):
    """
    Remove clusters without enough labels.

    Mutates labels' and topk_filters' contents.
    :param labels:
    :type labels: dict[str, dict[int, dict[str, bool]]]
    :param topk_filters:
    :type topk_filters: dict[str, set[int]]
    """
    for algo, algo_labels in labels.items():
        algo_topk_filter = topk_filters[algo]
        for cluster_id, cluster_labels in tuple(algo_labels.items()):
            if len(cluster_labels) < MIN_CLUSTER_LABELS:
                del algo_labels[cluster_id]
                if cluster_id in algo_topk_filter:
                    algo_topk_filter.remove(cluster_id)


def calculate_edge_labels(labels):
    """
    :param labels:
    :type labels: dict[str, dict[int, dict[str, bool]]]
    :return:
    :rtype: (dict[str, dict[int, dict[(str, str), int]]], dict[str, int])
    """
    edge_labels = dict()  # dict: algo -> dict: cluster ID -> dict: (node ID, node ID) -> weight
    num_label_nodes = dict()  # dict: algo -> number of label nodes
    for algo, algo_labels in labels.items():
        algo_edge_labels = dict()
        algo_num_label_nodes = 0
        for cluster_id, cluster_labels in algo_labels.items():
            algo_num_label_nodes += len(cluster_labels)
            cluster_edge_labels = dict()
            for edge in itertools.combinations(sorted(cluster_labels), 2):
                if cluster_labels[edge[0]] and cluster_labels[edge[1]]:
                    cluster_edge_labels[edge] = 1
                else:
                    cluster_edge_labels[edge] = 0
            algo_edge_labels[cluster_id] = cluster_edge_labels
        edge_labels[algo] = algo_edge_labels
        num_label_nodes[algo] = algo_num_label_nodes
    return edge_labels, num_label_nodes


def filter_cluster_ids(topk_filters, edge_labels, clusterings):
    """
    Mutates edge_labels' and clusterings' contents.
    :param topk_filters:
    :type topk_filters: dict[str, set[int]]
    :param edge_labels:
    :type edge_labels: dict[str, dict[int, dict[(str, str), int]]]
    :param clusterings:
    :type clusterings: dict[str, dict[int, set[str]]]
    """
    for algo, algo_topk_filter in topk_filters.items():
        algo_edge_labels = edge_labels[algo]
        algo_clustering = clusterings[algo]
        for cluster_id in tuple(algo_edge_labels):
            if cluster_id not in algo_topk_filter:
                if MODIFY_LABELS_FOR_TOPK:
                    del algo_edge_labels[cluster_id]
                del algo_clustering[cluster_id]


def create_graph_labels_object(edge_labels):
    """
    GraphLabels is supposed to read the labels from file(s) itself in the
    constructor, so injecting custom edge labels from memory requires some
    hacking.
    The class is instantiated without calling the constructor, and then the
    externally accessed class attributes (i.e. label_format and edge_weights)
    are set manually.
    :param edge_labels: Edge labels for a single algo.
    :type edge_labels: dict[int, dict[(str, str), int]]
    :return:
    :rtype: GraphLabels
    """
    edge_weights = dict()
    for cluster_edge_weights in edge_labels.values():
        edge_weights.update(cluster_edge_weights)

    graph_labels_object = GraphLabels.__new__(GraphLabels)
    graph_labels_object.label_format = GraphLabels.LABEL_FORMAT.EDGE_BASED
    graph_labels_object.edge_weights = edge_weights
    return graph_labels_object


def measure_and_plot(clusterings, edge_labels, stabilities, total_num_nodes,
                     num_label_nodes, staging_dir, title, plot_namespace,
                     shaving_methods):
    """
    :param clusterings: dict: algo -> dict: cluster ID -> set of node IDs
    :type clusterings: dict[str, dict[int, set[str]]]
    :param edge_labels: dict algo -> dict: cluster ID -> dict: (node ID, node ID) -> weight
    :type edge_labels: dict[str, dict[int, dict[(str, str), int]]]
    :param stabilities: dict algo -> dict: cluster ID -> cluster stability
    :type stabilities: dict[str, dict[int, float]]
    :param total_num_nodes: Total number of nodes in graph.
    :type total_num_nodes: int
    :param num_label_nodes:
    :type num_label_nodes: dict[str, int]
    :param staging_dir: Directory to output plots in.
    :type staging_dir: str
    :param title: Title of the plot.
    :type title: str
    :param plot_namespace: Prefix of plot file names.
    :type plot_namespace: str
    :param shaving_methods:
    :type shaving_methods: dict[str, str]
    """
    total_results = defaultdict(list)  # dict: similarity algo -> list of (algo, dict: num clusters -> similarity)
    for algo, algo_clustering in sorted(clusterings.items(), key=operator.itemgetter(0)):
        graph_labels = create_graph_labels_object(edge_labels[algo])
        stability_sorted_clusters = sorted(algo_clustering, key=stabilities[algo].__getitem__, reverse=True)

        if ASSUME_CANNOTLINK:
            num_all_points = num_label_nodes[algo]
        else:
            num_all_points = None

        for sim_algo in GraphSimilarity.SIMILARITY_ALGORITHMS:
            results = list()  # list of (fraction clustered, similarity index)

            print("### {}; {}".format(algo, sim_algo))

            clustering = dict()
            num_nodes_clustered = 0
            for cluster_id in stability_sorted_clusters:

                cluster = algo_clustering[cluster_id]
                num_nodes_clustered += len(cluster)
                clustering[cluster_id] = cluster

                # Note: num_all_points is only used for Edge-ARI, not precision.
                similarity_index = GraphSimilarity(
                    clustering=clustering,
                    labels=graph_labels,
                    algorithm=sim_algo,
                    num_all_points=num_all_points,  # None unless ASSUME_CANNOTLINK
                    debug=True
                ).calculate_similarity(clustering, None)
                results.append((num_nodes_clustered / total_num_nodes,
                                similarity_index))

                print("Adding cluster {}. {}: {}".format(cluster_id, sim_algo, similarity_index))

            total_results[sim_algo].append((algo, shaving_methods[algo], results))
            print()

    for sim_algo, sim_algo_results in total_results.items():
        plotter = GraphDataPlotter.__new__(GraphDataPlotter)
        plotter.data_set_dir = staging_dir
        plotter.data_name = plot_namespace
        plotter.measurements_data = sim_algo_results
        plotter.similarity_algorithm = sim_algo
        plotter.k_ignore = 0

        plotter.plot(title=title, bottom_zero=True)


def main():
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("--staging-dir", "-st", required=True)
    args = parser.parse_args()

    staging_dir = os.path.expanduser(args.staging_dir)

    if not os.path.isdir(staging_dir):
        raise FileNotFoundError("staging dir not found: {}".format(staging_dir))

    with open(os.path.join(staging_dir, "config.json")) as f:
        config_dict = json.load(f)

    total_num_nodes = config_dict["total_num_nodes"]
    dataset_title = config_dict["dataset"]

    labels = dict()  # dict: algo -> dict: cluster ID -> dict: node ID -> belongs
    topk_filters = dict()  # dict algo -> set of cluster IDs
    stabilities = dict()  # dict algo -> dict: cluster ID -> cluster stability

    print("Loading data from files...", end="", flush=True)
    start_time = default_timer()
    shaving_methods = dict()
    for algo_config in config_dict["data"]:
        algo = algo_config["algo"]
        judged_csv_filename = algo_config["judged_file"]
        topk_cluster_ids_filename = algo_config["topk_cluster_ids_file"]
        if "shaving_method" in algo_config:
            shaving_methods[algo] = algo_config["shaving_method"]
        else:
            shaving_methods[algo] = None

        labels[algo], stabilities[algo] = read_judged_csv(os.path.join(staging_dir, judged_csv_filename))

        with open(os.path.join(staging_dir, topk_cluster_ids_filename)) as f:
            topk_filters[algo] = set(map(int, f))
    print(" done. (time={:.3f} s)".format(default_timer() - start_time))

    # remove clusters without enough labels
    remove_underlabeled_clusters(labels, topk_filters)

    # TODO: The similarity code claims to need int node IDs, whereas it should
    # TODO:     still work with string IDs. Either change the similarity
    # TODO:     documentation to use collections.Hashable or add a node ID
    # TODO:     mapping generation here.

    # dict: algo -> dict: cluster ID -> dict: (node ID, node ID) -> weight
    edge_labels, num_label_nodes = calculate_edge_labels(labels)

    clusterings = {algo: {cluster_id: set(cluster_labels)
                          for cluster_id, cluster_labels in algo_labels.items()}
                   for algo, algo_labels in labels.items()}

    del labels

    measure_and_plot(
        clusterings=clusterings,
        edge_labels=edge_labels,
        stabilities=stabilities,
        total_num_nodes=total_num_nodes,
        num_label_nodes=num_label_nodes,
        staging_dir=staging_dir,
        title="{} (All Labeled Clusters)".format(dataset_title),
        plot_namespace="judged_all",
        shaving_methods=shaving_methods
    )

    print()

    if MODIFY_LABELS_FOR_TOPK:
        # TODO
        raise NotImplementedError("num_label_nodes must be updated if MODIFY_LABELS_FOR_TOPK")

    # filter based on topk cluster_ids
    # mutates edge_labels' and clusterings' contents
    filter_cluster_ids(topk_filters, edge_labels, clusterings)

    measure_and_plot(
        clusterings=clusterings,
        edge_labels=edge_labels,
        stabilities=stabilities,
        total_num_nodes=total_num_nodes,
        num_label_nodes=num_label_nodes,
        staging_dir=staging_dir,
        title="{} (Top K Clusters)".format(dataset_title),
        plot_namespace="judged_topk",
        shaving_methods=shaving_methods
    )


if __name__ == "__main__":
    main()
