#!/usr/bin/env python3
"""
Generate plots from measurements run by run_measurements.py (not actually ARI).
"""
from argparse import ArgumentParser
import json
import os
import sys

from graphDataAnalysis.GraphDataPlotter import GraphDataPlotter


def main():
    parser = ArgumentParser(description="Test plots data algorithms")

    parser.add_argument("--staging-dir", "-sd", required=True,
                        help="Trial set directory")
    parser.add_argument("--k-ignore", "-k", default=0, type=int,
                        help="won't plot first k clusters. helpful for removing noise")
    parser.add_argument("--markers", "-m", action="store_true",
                        help="Add markers on each data point.")
    parser.add_argument("--show", "-s", action="store_true",
                        help="Show the plot in a window before saving")

    args = parser.parse_args()

    staging_dir = os.path.expanduser(args.staging_dir)
    k_ignore = args.k_ignore
    markers = args.markers
    show = args.show

    global_params_file_path = os.path.join(staging_dir, "params.json")
    if not os.path.exists(global_params_file_path):
        print("Could not find required params file: {}"
              .format(global_params_file_path), file=sys.stderr)
        print("You need to run either convert_data.py or stage_algo.py to "
              "stage your data first for different algossuch as hmetis, "
              "kahip...", file=sys.stderr)
        sys.exit(1)

    with open(global_params_file_path, "r") as f:
        global_params = json.loads(" ".join(f.readlines()))

    for _var in ("algorithms", "data_set", "experiment_name", "min_stability", "trial_set"):
        if _var not in global_params:
            print("Required configuration variable: {} not found in file: {}"
                  .format(_var, global_params_file_path), file=sys.stderr)
            print("You need to run prepare_algo.py before running this program",
                  file=sys.stderr)
            sys.exit(1)
    # these variables are set when you run prepare_algo
    data_set = global_params["data_set"]
    algorithms = global_params["algorithms"]
    experiment_name = global_params["experiment_name"]

    graph_data_plotter = GraphDataPlotter(
        data_set_dir=staging_dir,
        data_name=data_set,
        algorithms=algorithms,
        experiment_name=experiment_name,
        k_ignore=k_ignore
    )
    graph_data_plotter.get_measurement_data()
    graph_data_plotter.plot(show=show, markers=markers)


if __name__ == "__main__":
    main()
