#!/usr/bin/env python3
import json
import os
import sys
from timeit import default_timer

from dataReadWrite.NativeReadWrite import NativeReadWrite
from dataReadWrite.ReadWriteAll import ALGO_RUN_TEMPLATES, ALGORITHMS
from labeling.LabelingManager import LabelingManager


def main():
    from argparse import ArgumentParser

    parser = ArgumentParser()

    parser.add_argument("--staging-dir", "-s", required=True,
                        help="root staging dir of auto-hds g")
    parser.add_argument("--experiment-name", "-e", required=True,
                        help="Experiment name usually yyyy-mm-dd")
    parser.add_argument("--jaccard-thresh", "-jt", default=0.0, type=float,
                        help="minimum similarity threshold to use")
    parser.add_argument("--algo", "-a", choices=ALGORITHMS.keys(),
                        required=True, help="algo to use")
    parser.add_argument("--params-suffix", "-p",
                        help="the params file location. the program will look "
                             "for a file with judge_params.[suffix].json.")
    parser.add_argument("--keep-disconnected-nodes", "-k",
                        action="store_true",
                        help="The graph passed to hMETIS will contain"
                             "disconnected nodes (from jaccard thresholding) "
                             "if this option is passed")

    args = parser.parse_args()

    staging_dir = os.path.expanduser(args.staging_dir)
    experiment_name = args.experiment_name
    algo = args.algo
    jaccard_thresh = args.jaccard_thresh
    params_suffix = args.params_suffix
    keep_disconnected_nodes = args.keep_disconnected_nodes

    if not os.path.isdir(staging_dir):
        print("Could not find staging dir: {}".format(staging_dir))
        sys.exit(1)

    if params_suffix is None:
        judge_params_file = os.path.join(staging_dir, "judge_params.json")
    else:
        judge_params_file = os.path.join(staging_dir, "judge_params.{}.json".format(params_suffix))

    if not os.path.exists(judge_params_file):
        print("Missing judge params file: {!r}".format(judge_params_file))
        sys.exit(1)
    with open(judge_params_file, "r") as f:
        judge_params = json.load(f)
        for _var in ["k_deduped", "num_points_in_graph"]:
            if _var not in judge_params:
                print("Required param {} not found in judge_param file at: {}".format(_var, judge_params_file))
    k_deduped = judge_params["k_deduped"]
    num_points_in_graph = judge_params["num_points_in_graph"]

    # update and save jaccard threshold in the judge params file for next step
    judge_params["jaccard_thresh"] = jaccard_thresh
    judge_params["keep_disconnected_nodes"] = keep_disconnected_nodes
    with open(judge_params_file, "w") as f:
        json.dump(judge_params, f)

    native_read_writer = NativeReadWrite(staging_dir, experiment_name)

    print("Loading graph from file...", end="", flush=True)
    start_time = default_timer()
    thresholded_graph, num_points, num_edges = native_read_writer.read_graph(jaccard_thresh)
    if num_points != num_points_in_graph:
        print("Graph has changed since last genediver judge file generation.")
        print("You need to run generate_genediver_judging_file.py before running this!")
        sys.exit(1)
    print(" done. (time={:.3f} s)".format(default_timer() - start_time))

    if params_suffix is None:
        algo_staging_dir = os.path.join(staging_dir, algo)
    else:
        algo_staging_dir = os.path.join(staging_dir, "{}.{}".format(algo, params_suffix))
    writer = ALGORITHMS[algo](algo_staging_dir)

    if writer.WEIGHTED:
        # this algorithm is weighted, so we need to load the mapping file from the universal autohds-g id mapping
        # file that is always present when hmetis runs because hmetis always runs after running genediver
        node_weight_file_path = os.path.join(staging_dir, experiment_name + ".mapping.tsv")
        print("Loading node weights for weighted algo {} from {}".format(algo, node_weight_file_path))
        node_weights = dict()
        with open(node_weight_file_path, "r") as f:
            for line in f:
                node_id, _, weight = line.split("\t")
                node_id = int(node_id)
                weight = float(weight)
                node_weights[node_id] = weight
    else:
        node_weights = None

    print("Writing graph to file...", end="", flush=True)
    start_time = default_timer()
    if keep_disconnected_nodes:
        writer.write_graph(
            graph=thresholded_graph,
            num_nodes=num_points,
            num_edges=num_edges,
            node_weights=node_weights
        )
    else:
        # Each edge in thresholded_graph is duplicated twice.
        node_id_mapping = dict()
        for new_node_id, node_info in enumerate(thresholded_graph):
            # Every node is a line in the line JSON
            node_id_mapping[node_info["id"]] = new_node_id

        mapped_graph = list()
        for node_info in thresholded_graph:
            new_node_id_1 = node_id_mapping[node_info["id"]]
            mapped_connections = list()
            for node_id_2, weight in node_info["connections"]:
                mapped_connections.append((node_id_mapping[node_id_2], weight))
            mapped_graph.append({
                "id": new_node_id_1,
                "connections": mapped_connections
            })

        writer.write_graph(
            graph=mapped_graph,
            num_nodes=len(mapped_graph),
            num_edges=num_edges,
            node_weights=node_weights
        )

        # write out ID mapping in algo staging dir
        with open(os.path.join(algo_staging_dir, "id_mapping.tsv"), "w") as f:
            for old_node_id, new_node_id in node_id_mapping.items():
                f.write("{}\t{}\n".format(old_node_id, new_node_id))
    print(" done. (time={:.3f} s)".format(default_timer() - start_time))

    command_format = "(cd {working_dir}; {command})"
    print("{} command:".format(ALGORITHMS[algo].ALGORITHM_DISPLAY_NAME))
    print(command_format.format(
        working_dir=algo_staging_dir,
        command=ALGO_RUN_TEMPLATES[algo].format(num_clusters=k_deduped)
    ))


def save_data_params(self):
    """
    adds the experiment_params.txt
    :return:
    """
    data_params_path = os.path.join(self.output_data_dir, "params.json")
    with open(data_params_path, "w") as f:
        params = {"sim": self.sim_threshold, "num_points": self.num_points_sample}
        params.update(self.DATA_NAMES[self.data_name])
        f.write(json.dumps(params))


if __name__ == "__main__":
    main()
