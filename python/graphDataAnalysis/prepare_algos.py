#!/usr/bin/env python3
"""
Get the commands and write out the params for all external algos.
"""
import json
import os
import sys

from analysis.ClusterDeduper import ClusterDeduper
from dataReadWrite.NativeReadWrite import NativeReadWrite
from dataReadWrite.ReadWriteAll import ALGO_RUN_TEMPLATES, ALGORITHMS
from lib import warn


def main():
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("--staging-dir", "-sd", required=True)
    parser.add_argument("--data-set", "-d", required=True)
    parser.add_argument("--trial-set", "-t", required=True, help="this is the variation of your graph staging due to "
                                                                 "jaccard or sampling differences. e.g. "
                                                                 "node_100k.n_1.li_0.1")
    parser.add_argument("--experiment-name", "-e", required=True, help="this is the sub directory where your autohds"
                                                                       "experiment run is staged and prevents it from "
                                                                       "being over written when you run again. this is "
                                                                       "the same name as the stage graph for autohds."
                                                                       "e.g. n_1")
    parser.add_argument("--min-stability", "-m", default=0.5, type=float,
                        help="min stability to be plotted")
    parser.add_argument("--overclustering", "-oc", default=2.0, type=float,
                        help="overclustering")

    args = parser.parse_args()

    staging_dir = os.path.expanduser(args.staging_dir)
    data_set = args.data_set
    trial_set = args.trial_set
    experiment_name = args.experiment_name
    min_stability = args.min_stability
    overclustering = args.overclustering

    if not os.path.isdir(staging_dir):
        raise FileNotFoundError("Staging directory not found: {}"
                                .format(staging_dir))

    data_set_dir = os.path.join(staging_dir, data_set)

    if not os.path.isdir(data_set_dir):
        raise FileNotFoundError("Data set directory not found: {}"
                                .format(data_set_dir))

    trial_set_dir = os.path.join(data_set_dir, trial_set)

    if not os.path.isdir(trial_set_dir):
        raise FileNotFoundError("Trial set directory not found: {}"
                                .format(trial_set_dir))

    autohds_g_dir = os.path.join(trial_set_dir, experiment_name)

    if not os.path.isdir(autohds_g_dir):
        raise FileNotFoundError("Could not find autohds-g directory in data "
                                "set directory. Run convert_data.py first.")

    clustering, stabilities = NativeReadWrite(trial_set_dir, experiment_name).read_graph_lab()

    nodes = set()
    for cluster in clustering.values():
        nodes.update(cluster)

    print("Nodes before deduping: {}".format(sum(map(len, clustering.values()))))
    print("Unique nodes: {}".format(len(nodes)))
    print("Deduping clusters!")
    cluster_deduper = ClusterDeduper(clustering, stabilities)
    deduped_clustering, excluded_clusters = cluster_deduper.get_deduped_clusters(min_stability=min_stability)
    print("Nodes after deduping: {}".format(sum(map(len, deduped_clustering.values()))))

    # For debugging, will raise exception if there are multiple clusters per key
    deduped_nodes = set()
    for cluster in deduped_clustering.values():
        if cluster & deduped_nodes:
            raise AssertionError("There are overlapping clusters!")
        deduped_nodes.update(cluster)
    print("Excluded clusters after deduping: {}".format(excluded_clusters))

    print("==================================================================")

    k_deduped = len(deduped_clustering)
    print("k_deduped: {}".format(k_deduped))

    command_format = "(cd {working_dir}; {command})"
    algorithms = ["autohds-g"]

    global_params_file_path = os.path.join(trial_set_dir, "params.json")
    if not os.path.exists(global_params_file_path):
        print("Could not find required params file: {}".format(global_params_file_path))
        print("You need to run either convert_data.py or stage_algo.py to stage your data first for different algos"
              "such as hmetis, kahip...")
        sys.exit(1)

    for dirname in os.listdir(trial_set_dir):
        if not os.path.isdir(os.path.join(trial_set_dir, dirname)):
            continue

        if dirname == experiment_name:
            continue

        if dirname in ALGO_RUN_TEMPLATES:
            num_clusters = k_deduped
            algo = dirname
        elif dirname in {"{}.overclustered".format(algo) for algo in ALGO_RUN_TEMPLATES}:
            num_clusters = round(k_deduped * overclustering)
            algo = dirname.rsplit(".", 1)[0]
        else:
            warn("skipping unexpected dir in data set dir: {}"
                 .format(dirname), Warning)
            continue

        algo_dir_path = os.path.join(trial_set_dir, dirname)
        algorithms.append(dirname)

        print("\n")

        algo_params_file_path = os.path.join(algo_dir_path, "params.json")
        print("Writing out {!r}...".format(algo_params_file_path), end="", flush=True)
        with open(algo_params_file_path, "w") as f:
            json.dump({"k": num_clusters}, f)
        print(" done.\n")

        print("{} command:".format(ALGORITHMS[algo].ALGORITHM_DISPLAY_NAME))
        print(command_format.format(
            working_dir=algo_dir_path,
            command=ALGO_RUN_TEMPLATES[algo].format(num_clusters=num_clusters)
        ))

    with open(global_params_file_path, "r") as f:
        global_params = json.loads(" ".join(f.readlines()))
    global_params["experiment_name"] = experiment_name
    global_params["algorithms"] = algorithms
    global_params["min_stability"] = min_stability
    global_params["data_set"] = data_set
    global_params["trial_set"] = trial_set
    with open(global_params_file_path, "w") as f:
        json.dump(global_params, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
