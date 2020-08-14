#!/usr/bin/env python3
import json
import os
import sys
from timeit import default_timer

from dataReadWrite.NativeReadWrite import NativeReadWrite
from dataReadWrite.ReadWriteAll import ALGORITHMS
from graphHDS.prune_cluster import ALGORITHMS as SHAVING_ALGORITHMS
from graphHDS.pseudo_stability import get_algo_cluster_stabilities
from labeling.LabelingManager import LabelingManager
from util import convert_connections_to_edges
from util import shave_clustering, SHAVING_METHOD


def main():
    from argparse import ArgumentParser

    parser = ArgumentParser(description="generates labeling file")

    parser.add_argument("--staging-dir", "-s", required=True,
                        help="root staging dir of auto-hds g")
    parser.add_argument("--experiment-name", "-e", required=True,
                        help="Experiment name usually yyyy-mm-dd")
    parser.add_argument("--algo", "-a", required=True,
                        choices=ALGORITHMS.keys(),
                        help="clustering algorithm to use")
    parser.add_argument("--top-k", "-k", type=int, required=True,
                        help="top k clusters from HMETIS")
    parser.add_argument("--k-dithered", "-kd", type=int, required=True,
                        help="k dithered")
    parser.add_argument("--shaving-algo", "-sa", choices=SHAVING_ALGORITHMS,
                        help="shaving algorithm to use (1=sorted by flow to "
                             "node, 2=incremental shaving by flow to node)")
    parser.add_argument("--max-sample", "-ms", type=int, required=True,
                        help="Max sample per cluster")
    parser.add_argument("--seed", "-sd", type=int, required=True, help="seed")
    parser.add_argument("--shave-type", "-t", required=True,
                        choices={"rand_shave", "flow_shave"},
                        help="shave type to do on non autohds-g algos")
    parser.add_argument("--params-suffix", "-p", required=False, default=None, help="the params file location. the"
                                                                                    " program will look for a file with"
                                                                                    " judge_params.[suffix].json.")
    parser.add_argument('--debug', action="store_true", default=False,
                        help="Debug allows individual loaders and algo to sample for testing",)

    args = parser.parse_args()

    staging_dir = os.path.expanduser(args.staging_dir)
    experiment_name = args.experiment_name
    algo = args.algo
    top_k = args.top_k
    k_dithered = args.k_dithered
    shaving_algo = args.shaving_algo
    max_sample = args.max_sample
    seed = args.seed
    shave_type = args.shave_type
    params_suffix = args.params_suffix
    debug = args.debug

    shaving_method = SHAVING_METHOD.RAND if shave_type == "rand_shave" else SHAVING_METHOD.FLOW

    if shaving_method == SHAVING_METHOD.FLOW and shaving_algo is None:
        parser.error("--shaving-algo/-sa is required if shaving method is flow_shave")

    if not os.path.isdir(staging_dir):
        print("Could not find staging dir: {}".format(staging_dir))
        sys.exit(1)

    if params_suffix is None:
        judge_params_file = os.path.join(staging_dir, "judge_params.json")
    else:
        judge_params_file = os.path.join(staging_dir, "judge_params.{}.json".format(params_suffix))

    if not os.path.exists(judge_params_file):
        print("You need to run generate_genediver_judging_file.py before running this!")
        sys.exit(1)
    with open(judge_params_file, "r") as f:
        judge_params = json.load(f)
        for _var in ["k_deduped", "fraction_kept", "num_points_in_graph", "jaccard_thresh"]:
            if _var not in judge_params:
                print("Required param {} not found in judge_param file at: {}".format(_var, judge_params_file))
    k_deduped = judge_params["k_deduped"]
    fraction_kept = judge_params["fraction_kept"]
    num_points_in_graph = judge_params["num_points_in_graph"]
    jaccard_thresh = judge_params["jaccard_thresh"]
    keep_disconnected_nodes = judge_params["keep_disconnected_nodes"]

    if shaving_algo not in SHAVING_ALGORITHMS:
        raise ValueError("shaving algorithm '{}' does not exist".format(shaving_algo))
    if k_deduped < top_k:
        raise Exception("k_deduped is {} but the number of algo clusters is only {}".format(top_k, k_deduped))

    native_read_writer = NativeReadWrite(staging_dir, experiment_name)

    # ==LOAD INPUT GRAPH to get the number of points for clustering_edges==
    print("Loading graph from file...", end="", flush=True)
    start_time = default_timer()
    connection_graph, num_points, num_edges = native_read_writer.read_graph(jaccard_threshold=jaccard_thresh)

    input_graph = convert_connections_to_edges(connection_graph)
    del connection_graph

    if num_points != num_points_in_graph:
        print("Graph has changed since last genediver judge file generation.")
        print("You need to run generate_genediver_judging_file.py before running this!")
        sys.exit(1)
    print(" done. (time={:.3f} s)".format(default_timer() - start_time))
    print()

    if params_suffix is None:
        algo_staging_dir = os.path.join(staging_dir, algo)
    else:
        algo_staging_dir = os.path.join(staging_dir, algo + "." + params_suffix)

    if not os.path.isdir(algo_staging_dir):
        print("Could not find algo staging dir: {}, please run graph algo first!".format(algo_staging_dir))
        sys.exit(1)

    hdsg_to_external_id_mapping = native_read_writer.read_mapping()

    # ==READ CLUSTERING FILE OUTPUT==
    print("Loading clustering from file...", end="", flush=True)
    start_time = default_timer()
    # TODO: warn when num_algo_clusters does not match the filename
    reader = ALGORITHMS[algo](algo_staging_dir)
    cluster_points = reader.read_clustering()
    if not keep_disconnected_nodes:

        reverse_node_id_mapping = dict()
        with open(os.path.join(algo_staging_dir, "id_mapping.tsv")) as f:
            for line in map(str.strip, f):
                old_node_id, new_node_id = line.split("\t")
                reverse_node_id_mapping[int(new_node_id)] = int(old_node_id)

        for cluster_id, cluster in cluster_points.items():
            cluster_points[cluster_id] = set(map(reverse_node_id_mapping.get, cluster))

    print(" done. (time={:.3f} s)".format(default_timer() - start_time))

    # ==SHAVE CLUSTERS (if filtering didn't already shave enough)==
    print("Sample proportion: {}".format(fraction_kept))

    print("Shaving clusters using algorithm {}...".format(shaving_algo))
    start_time = default_timer()
    # shave clusters down to the same number of nodes clustered as autoHDS-G
    shaved_cluster_points = shave_clustering(
        num_points_in_graph=num_points_in_graph,
        clustering=cluster_points,
        method=shaving_method,
        fraction_kept=fraction_kept,
        seed=seed,
        input_graph=input_graph,
        shaving_algo=shaving_algo,
        debug=debug
    )

    num_shaved_cluster_points = LabelingManager.count_unique_points_in_clusters(shaved_cluster_points)
    print("num shaved cluster points: {}".format(num_shaved_cluster_points))
    print("Finished shaving clusters in (time={:.3f} s)".format(default_timer() - start_time))
    print()

    # ==FILTER CLUSTERS==
    # This will work even if top_k = num_algo_clusters
    print("Getting the top {} clusters from the output of algo...".format(top_k), end="", flush=True)
    start_time = default_timer()
    # get cluster_stabilities
    cluster_stabilities = get_algo_cluster_stabilities(
        graph=input_graph,
        cluster_points=shaved_cluster_points,
    )

    filtered_cluster_points, top_k_cluster_ids, full_dithered_cluster_ids = LabelingManager.filter_clustering(
        clustering=shaved_cluster_points,
        cluster_stabilities=cluster_stabilities,
        top_k=top_k,
        k_dithered=k_dithered
    )
    num_filtered_points = LabelingManager.count_unique_points_in_clusters(filtered_cluster_points)
    print(" done. (time={:.3f} s)".format(default_timer() - start_time))
    print("Number of nodes in judged clusters before shaving: {}".format(num_filtered_points))

    if params_suffix:
        algo += "." + params_suffix

    LabelingManager.generate_judging_files(
        clustering=shaved_cluster_points,
        filtered_clustering=filtered_cluster_points,
        top_k_cluster_ids=top_k_cluster_ids,
        k_dithered_cluster_ids=full_dithered_cluster_ids,
        algorithm_name=algo,
        max_sample=max_sample,
        seed=seed,
        cluster_stabilities=cluster_stabilities,
        staging_dir=staging_dir,
        hdsg_to_external_id_mapping=hdsg_to_external_id_mapping
    )


if __name__ == "__main__":
    main()
