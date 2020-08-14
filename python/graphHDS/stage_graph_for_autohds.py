#!/usr/bin/env python3
import argparse
import json
import os
import traceback

from graphHDS.AutoHDSGraphConverter import AutoHDSGraphConverter
from graphHDS.LSAIExperimentLogger import LSAIExperimentLogger


if __name__ == "__main__":

    example = {"id1": "apple", "id2": "orange", "sim": 0.9}
    parser = argparse.ArgumentParser(description="Given a graph edge json, produce a line-JSON graph "
                                                 "compatible with GraphHDS and an associated mapping file.")
    parser.add_argument("--input-graph-file", "-i", required=True,
                        help="graph edge json of form {} produced with PostGraphGenerator, best to have "
                             "similarity scaled between 0 and 1".format(example))
    parser.add_argument("--output-dir", "-o", default=None,
                        help="Directory to dump output files")
    parser.add_argument("--experiment-name", "-e", default=None,
                        help="Name that signifies the experiment you are doing, based on thresholds")
    parser.add_argument("--sim-threshold", "-s", default=0.0, type=float,
                        help="Optional similarity threshold value above which edges are included in output graph")
    parser.add_argument("--node-weights-file", "-n", default=None,
                        help="Optional node weight file and type. Expect to be a tsv file of type <node id> <weight>.")

    parser.add_argument("--url-template", "-u", default=None, help="pass a url template to "
                                                                   "make your point ids have url in gene diver and "
                                                                   "label data, e.g. https://www.instagram.com/p/{PT_ID}")

    args = parser.parse_args()

    input_graph_file = os.path.expanduser(args.input_graph_file)
    output_dir = os.path.dirname(input_graph_file)
    sim_threshold = args.sim_threshold
    experiment_name = args.experiment_name
    url_template = args.url_template

    if args.node_weights_file is not None:
        node_weights_file = os.path.expanduser(args.node_weights_file)
    else:
        node_weights_file = None

    # this is the first step update/recreate experiment params file

    try:

        # for creating NEW experiment folder/files
        experiment_logger = LSAIExperimentLogger(
            experiments_root_dir=output_dir,
            use_last_version=False,
            experiment_name=experiment_name,
            description=""
        )

        converter = AutoHDSGraphConverter(input_graph_file, node_weights_file, output_dir,
                                          experiment_logger.get_experiment_name(), url_template=url_template)

        converter.load_generated_graph(sim_threshold)
        converter.save_hds_g_compatible_graph()
        converter.save_hds_g_compatible_mapping_file()

        exp_params_file = os.path.join(output_dir, "experiment_params.txt")
        exp_params = {"stage_graph_for_autohds.sim-threshold": sim_threshold}

        with open(exp_params_file, "a") as ef:
            ef.write("{}\n".format(json.dumps(exp_params)))

    except Exception as e:
        print("Graph conversion failed. Error: {}".format(e))
        traceback.print_exc()
