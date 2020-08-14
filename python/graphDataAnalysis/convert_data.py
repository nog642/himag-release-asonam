#!/usr/bin/env python3
"""
convert_data cli
"""
from argparse import ArgumentParser
import faulthandler
import os
from timeit import default_timer

from graphDataAnalysis.GraphDataStager import GraphDataStager


def convert_data(graph_data_stager, algorithms):
    """
    wrapper to compute data then route data the right algorithms
    :param graph_data_stager: 
    :param algorithms: 
    :return: 
    """
    total_start_time = default_timer()

    # make sure all algorithms passed are valid otherwise DO NOT start processing
    graph_data_stager.check_algorithms(algorithms)

    # start generating data
    print("Generating graph and labels file...")
    start_time = default_timer()

    graph_data_stager.generate_graph_and_labels()

    print("Done generating graph and labels file. (time={:.3f} s)"
          .format(default_timer() - start_time))
    print("Graph with {} nodes and {} edges created.".format(
        len(graph_data_stager.graph_nodes),
        len(graph_data_stager.graph)
    ))
    # end done generating data

    # now run each of the algorithms through this data
    print("Generating algorithm-specific graphs...", end="", flush=True)
    start_time = default_timer()
    for algorithm in algorithms:
        graph_data_stager.generate_algorithm_graph(algorithm)
    print(" done. (time={:.3f} s)".format(default_timer() - start_time))

    graph_data_stager.save_mapping()
    graph_data_stager.save_data_params()

    graph_data_stager.print_metrics()

    print("Total run-time: {:.3f} s".format(default_timer() - total_start_time))


def main():
    faulthandler.enable()

    parser = ArgumentParser(description="converts label data")

    parser.add_argument("--input-dir", "-i", required=True,
                        help="Staging dir, where dataset directories are")
    parser.add_argument("--data-name", "-d", required=True, help="Data set name")
    parser.add_argument("--experiment-name", "-e", required=True, help="this is the sub directory where the raw graph "
                                                                       "for this data name is staged. we also stage "
                                                                       "algo specific data subdirectories here. "
                                                                       "autohds-g related graphs are left in the "
                                                                       "top-level directory and they are further "
                                                                       "processed by stage_graph_for_autohds")
    parser.add_argument("--algorithms", "-a", required=True, help="comma-delimited list of algorithms")
    parser.add_argument("--sim-threshold", "-s", type=float, required=True, help="Threshold for labels")
    parser.add_argument("--num-points", "-n", type=int, help="Num points needed")
    parser.add_argument("--seed", "-r", type=int, required=True, help="Random seed")
    parser.add_argument("--max-edges", "-m", default=10**20, type=int, help="Max edges or else stop")
    parser.add_argument("--label-inject-fraction", "-l", type=float, help="only supported for external datasets")
    parser.add_argument('--debug', action="store_true", help="Debug allows individual loaders and algo to sample for "
                                                             "testing")
    args = parser.parse_args()

    input_dir = os.path.expanduser(args.input_dir)
    data_name = args.data_name
    seed = args.seed
    sim_threshold = args.sim_threshold
    num_points = args.num_points
    algorithms = args.algorithms.split(",")
    max_edges = args.max_edges
    label_inject_fraction = args.label_inject_fraction
    debug = args.debug
    experiment_name = args.experiment_name

    graph_data_stager = GraphDataStager(
        staging_dir=input_dir,
        data_name=data_name,
        experiment_name=experiment_name,
        seed=seed,
        num_points_sample=num_points,
        sim_threshold=sim_threshold,
        max_edges=max_edges,
        debug=debug,
        label_inject_fraction=label_inject_fraction
    )

    convert_data(graph_data_stager, algorithms)


if __name__ == "__main__":
    main()
