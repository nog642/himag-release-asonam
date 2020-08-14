#!/usr/bin/env python3
"""
CLI for autoHDS-G v2. See GraphHDSV2 class for more details.
"""
import json
import os

from graphHDS.GraphHDSV2 import GraphHDSV2
from graphHDS.LSAIExperimentLogger import LSAIExperimentLogger


def main():  # function exists to avoid global variables
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("--staging-dir", "-t", required=True)
    parser.add_argument("--no-mapping", "-m", action="store_true", help="use if {staging-dir}/{data-name}.mapping.tsv "
                                                                        "does not exist")
    parser.add_argument("--min-flow", "-n", default=10.0, type=float)
    parser.add_argument("--shave-rate", "-r", default=0.05, type=float)
    parser.add_argument("--min-shave", "-f", default=0.3, type=float, help="fraction least dense data that is never "
                                                                           "clustered (stops early)")
    parser.add_argument("--seed", type=int, required=True, help="Randomization seed (e.g. 123)")
    parser.add_argument("--experiment-name", "-e", required=True, help="this is the sub directory where your autohds"
                                                                       "experiment run is staged and prevents it from "
                                                                       "being over written when you run again. this is "
                                                                       "the same name as the stage graph for autohds")
    parser.add_argument("--experiment-description", "-ed", default="automated run",
                        help="describe in one line what this experiment was changing from previous one.")
    parser.add_argument("--algo", "-a", default="node", choices={"node", "edge"}, help="Algo to use, dense node based, "
                                                                                       "dense edge-based, add more "
                                                                                       "variations here.")
    parser.add_argument("--weight-log-scale", "-w", default=1, type=int, choices={0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10},
                        help="log scale for weights for points. Only used if id mapping was passed that "
                             "has node weights in it. 0 would cause weights to be ignore and all points to have "
                             "equal weight. This is also what happens if no id mapping file found. 1 (default)"
                             "will scale the weights passed between 0 and 1 over all points. 2 and beyond will "
                             "cause weights to be interpreded as abs(log(weight,base) where base is value passed for this"
                             "parameter"
                        )
    args = parser.parse_args()

    staging_dir = os.path.expanduser(args.staging_dir)
    min_flow = args.min_flow
    shave_rate = args.shave_rate
    seed = args.seed
    no_mapping = args.no_mapping
    min_shave = args.min_shave
    algo = args.algo
    weight_log_scale = args.weight_log_scale

    use_last_version = True  # TODO: this can raise errors when running for the first time
    experiment_name = None

    if args.experiment_name is not None:
        experiment_name = args.experiment_name
        use_last_version = False

    # for continuing with current experiment folder/files. assumes that already
    #     at least one file was created by a previous step (the stage graph
    #     program does that)
    experiment_logger = LSAIExperimentLogger(
        experiments_root_dir=staging_dir,
        use_last_version=use_last_version,
        experiment_name=experiment_name,
        description=args.experiment_description
    )

    # recover last step's experiment/version name
    if experiment_name is None:
        data_name = experiment_logger.get_experiment_name()
    else:
        data_name = experiment_name

    # optional cluster labels file if found. can contain sparse labels for some points
    cluster_labels_file = os.path.join(staging_dir, "labels.clusters.jsonl")
    if not os.path.isfile(cluster_labels_file):
        cluster_labels_file = None

    graph_hds = GraphHDSV2(
        staging_dir=staging_dir,
        data_name=data_name,
        seed=seed,
        min_flow=min_flow,
        shave_rate=shave_rate,
        min_shave=min_shave,
        id_mapping=not no_mapping,
        weight_scale=weight_log_scale
    )
    graph_hds.load_graph()

    # run hds minus auto-hds - this should give the HMA hierarchy we can save and use in Gene DIVER
    graph_hds.hds(algo)

    # save output for Gene DIVER
    graph_hds.save(cluster_labels_file)

    exp_params_file = os.path.join(staging_dir, "experiment_params.txt")
    exp_params = {
        "runGraphHDS.seed": args.seed,
        "runGraphHDS.shave_rate": args.shave_rate,
        "runGraphHDS.min_flow": args.min_flow
    }

    with open(exp_params_file, "a") as ef:
        ef.write("{}\n".format(json.dumps(exp_params)))

    # generate final experiment log as this is the last step
    experiment_logger.update_log()


if __name__ == "__main__":
    main()
