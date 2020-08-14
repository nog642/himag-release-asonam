#!/usr/bin/env python3
from argparse import ArgumentParser
import json
import os
import sys
from timeit import default_timer

from analysis.ClusterDeduper import ClusterDeduper
from dataReadWrite.ReadWriteAll import ALGO_RUN_TEMPLATES
from graphDataAnalysis.GraphMeasurementsException import GraphMeasurementsException
from graphDataAnalysis.GraphMeasurements import GraphMeasurements
from graphHDS.prune_cluster import ALGORITHMS as SHAVING_ALGORITHMS
from labeling.LabelingManager import LabelingManager
from measurements.GraphSimilarity import GraphSimilarity
from util import read_genediver_graph_lab


def main():
    parser = ArgumentParser(description="Runs measurements on graph clustering algorithms")

    parser.add_argument("--seed", "-rs", type=int, required=True,
                        help="Random seed")
    parser.add_argument("--staging-dir", "-sd", type=str, required=True,
                        help="Staging dir, where dataset folders are")
    parser.add_argument("--similarity-algo", "-s", required=True, help="Use a simplified similarity algorithm",
                        choices=GraphSimilarity.SIMILARITY_ALGORITHMS)
    parser.add_argument("--human-cluster-labels", "-hc", action="store_true",
                        help="Use a simplified similarity algorithm")
    parser.add_argument("--level-measurements", action="store_true",
                        help="default is stability sorted measurements for comparing algos. If true, then it performs "
                             "shaving level measurements which may not make sense in most cases. Shaving level "
                             "measurements measure density shaving step, while stability sorted measure the whole algo:"
                             " Auto-HDS Graph")
    parser.add_argument("--shave-type", "-t", type=str, required=True, choices={"no_shave", "rand_shave", "flow_shave"},
                        help="shave type to do on non autohds-g algos")
    parser.add_argument("--top-k", "-k", type=int, required=False, default=None, help="top k clusters for human judged")
    parser.add_argument("--k-dithered", "-kd", type=int, required=False, default=None,
                        help="k dithered for human judged")
    parser.add_argument("--shaving-algo", "-sa", required=True,
                        choices=SHAVING_ALGORITHMS,
                        help="shaving algorithm to use (1=sorted by flow to "
                             "node, 2=incremental shaving by flow to node)")
    parser.add_argument("--debug", action="store_true", default=False,
                        help="Debug allows individual loaders and algo to sample for testing",)

    args = parser.parse_args()

    seed = args.seed
    staging_dir = os.path.expanduser(args.staging_dir)
    similarity_algo = args.similarity_algo
    human_cluster_labels = args.human_cluster_labels
    level_measurements = args.level_measurements
    shave_type = args.shave_type
    top_k = args.top_k
    k_dithered = args.k_dithered
    shaving_algo = args.shaving_algo
    debug = args.debug

    global_params_file_path = os.path.join(staging_dir, "params.json")
    if not os.path.exists(global_params_file_path):
        print("Could not find required params file: {}".format(global_params_file_path))
        print("You need to run either convert_data.py or stage_algo.py to stage your data first for different algos"
              "such as hmetis, kahip...")
        sys.exit(1)

    with open(global_params_file_path, "r") as f:
        global_params = json.loads(" ".join(f.readlines()))

    for _var in ["algorithms", "data_set", "experiment_name", "min_stability", "trial_set"]:
        if _var not in global_params:
            print("Required configuration variable: {} not found in file: {}".format(_var, global_params_file_path))
            print("You need to run prepare_algo.py before running this program")
            sys.exit(1)
    # these variables are set when you run prepare_algo
    data_set = global_params["data_set"]
    algorithms = global_params["algorithms"]
    experiment_name = global_params["experiment_name"]
    min_stability = global_params["min_stability"]

    # find the k_deduped for autohds-g
    autohdsg_clustering, cluster_stabilities = read_genediver_graph_lab(
        os.path.join(staging_dir, experiment_name, "graph_lab.csv")
    )
    autohdsg_clustering = {cluster_id: cluster
                           for cluster_id, cluster in autohdsg_clustering.items()
                           if cluster_stabilities[cluster_id] > min_stability}
    cluster_deduper = ClusterDeduper(autohdsg_clustering, cluster_stabilities)
    deduped_autohdsg_clustering, _ = cluster_deduper.get_deduped_clusters()
    k_deduped = len(deduped_autohdsg_clustering)

    # find the fraction kept for autohds-g
    graph_nodes = set()
    with open(os.path.join(staging_dir, "graph")) as f:
        for line in f:
            node_1, node_2, _ = line.split("\t")
            if node_1 not in graph_nodes:
                graph_nodes.add(node_1)
            if node_2 not in graph_nodes:
                graph_nodes.add(node_2)
    num_points = len(graph_nodes)
    num_deduped_points = LabelingManager.count_unique_points_in_clusters(deduped_autohdsg_clustering)
    fraction_kept = float(num_deduped_points)/num_points
    print("Using {} as fraction kept".format(fraction_kept))
    print("Found {} as k_deduped!".format(k_deduped))
    print("Found {} points, and {} deduped points".format(num_points, num_deduped_points))

    for algorithm in algorithms:
        print()
        print("=========== Algorithm: {} ===========".format(algorithm))
        print()

        if algorithm != "autohds-g" and data_set not in {"sim2_edge", "sim2_partitional"}:

            if algorithm.endswith(".overclustered"):
                algo_name = algorithm.rsplit(".", 1)[0]
                correct_k = k_deduped * 2  # TODO: don't hardcode 2
            else:
                algo_name = algorithm
                correct_k = k_deduped

            with open(os.path.join(staging_dir, algorithm, "params.json"), "r") as f:
                f_data = json.loads(f.readline())
            algorithm_k = f_data["k"]
            if algorithm_k != correct_k:
                correct_command = ALGO_RUN_TEMPLATES[algo_name].format(num_clusters=k_deduped)
                raise GraphMeasurementsException("autohds-g k_deduped does not match the k passed to {}! Please "
                                                 "rerun with this command: {}".format(algorithm, correct_command))

        graph_measurer = GraphMeasurements(
            staging_dir=staging_dir,
            data_name=data_set,
            experiment_name=experiment_name,
            algorithm=algorithm,
            similarity_algorithm=similarity_algo,
            level_measurements=level_measurements,
            seed=seed,
            shave_type=shave_type,
            top_k=top_k,
            k_dithered=k_dithered,
            min_stability=min_stability,
            shaving_algo=shaving_algo,
            fraction_kept=fraction_kept,
            debug=debug
        )

        graph_measurer.load_graph()
        graph_measurer.load_output()
        if algorithm != "autohds-g":
            algorithm_measurements_file = os.path.join(staging_dir, algorithm, "measurements.{}".format(graph_measurer.shave_method.name))
            if graph_measurer.num_all_nodes != num_points:
                raise GraphMeasurementsException("Error in output of {}, num_points is different from number of points "
                                                 "in clusters")
        else:
            algorithm_measurements_file = os.path.join(staging_dir, experiment_name, "measurements")
        graph_measurer.load_labels(human_cluster_labels)

        graph_measurer.prepare_measurements()
        print("XXXXXXXXXXXXXXXXX Start timer for measurement calc...")
        start_time = default_timer()
        for sample_proportion, num_clustered, similarity, real_sample_proportion in graph_measurer.get_measurements():
            if debug:
                print("Num clustered: {}, similarity: {}, real sample proportion: {}"
                  .format(num_clustered, similarity, real_sample_proportion))

        print("XXXXXXXXXXXXXXXXX End timer for measurement calc: {:.2f} seconds".format(default_timer() - start_time))

        graph_measurer.save_measurements(algorithm_measurements_file)


if __name__ == "__main__":
    main()
