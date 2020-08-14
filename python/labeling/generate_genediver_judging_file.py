#!/usr/bin/env python3
import json
import os
import sys
from timeit import default_timer

from analysis.ClusterDeduper import ClusterDeduper
from labeling.LabelingManager import LabelingManager
from dataReadWrite.NativeReadWrite import NativeReadWrite


def main():
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("--staging-dir", "-s", required=True, help="root staging dir of auto-hds g")
    parser.add_argument("--experiment-name", "-e", required=True, help="Experiment name usually yyyy-mm-dd")
    parser.add_argument("--top-k", "-k", type=int, required=True, help="top k clusters")
    parser.add_argument("--k-dithered", "-kd", type=int, required=True,
                        help="k dithered")
    parser.add_argument("--max-sample", "-m", type=int, required=True, help="max sample")
    parser.add_argument("--seed", "-se", type=int, required=True, help="seed")
    parser.add_argument("--min-stability", "-ms", default=0.0, type=float,
                        help="min stability to be plotted")

    args = parser.parse_args()

    staging_dir = os.path.expanduser(args.staging_dir)
    experiment_name = args.experiment_name
    top_k = args.top_k
    k_dithered = args.k_dithered
    max_sample = args.max_sample
    seed = args.seed
    min_stability = args.min_stability

    if not os.path.isdir(staging_dir):
        print("Could not find staging dir: {}".format(staging_dir))
        sys.exit(1)

    native_read_writer = NativeReadWrite(staging_dir, experiment_name)

    # ==READ CLUSTERING FILE OUTPUT==
    print("Loading graph lab file...", end="", flush=True)
    start_time = default_timer()
    try:
        cluster_points, cluster_stabilities = native_read_writer.read_graph_lab()
        gene_diver_k = len(cluster_points)
    except FileNotFoundError:
        # more helpful error message than FileNotFoundError traceback
        print("\nCould not find graph lab file; please run Gene DIVER first!",
              file=sys.stderr)
        sys.exit(1)
    print(" done. (time={:.3f} s)".format(default_timer() - start_time))

    # ==LOAD INPUT GRAPH== to get the number of points for clustered fraction
    print("Loading graph from file...", end="", flush=True)
    start_time = default_timer()
    num_points = native_read_writer.count_graph_nodes()
    print(" done. (time={:.3f} s)".format(default_timer() - start_time))

    # ==DEDUPE CLUSTERS==
    cluster_deduper = ClusterDeduper(
        clustering=cluster_points,
        cluster_stabilities=cluster_stabilities
    )
    deduped_cluster_points, excluded_clusters = cluster_deduper.get_deduped_clusters(min_stability=min_stability)

    # ==FILTER CLUSTERS==
    filtered_cluster_points, top_k_cluster_ids, k_dithered_cluster_ids = LabelingManager.filter_clustering(
        clustering=deduped_cluster_points,
        cluster_stabilities=cluster_stabilities,
        top_k=top_k,
        k_dithered=k_dithered
    )
    print("Excluded clusters after deduping: {}".format(excluded_clusters))

    num_deduped_cluster_points = LabelingManager.count_unique_points_in_clusters(deduped_cluster_points)

    sample_proportion = num_deduped_cluster_points / num_points
    generated_k_deduped = len(deduped_cluster_points)
    LabelingManager.generate_judging_files(
        clustering=deduped_cluster_points,
        filtered_clustering=filtered_cluster_points,
        top_k_cluster_ids=top_k_cluster_ids,
        k_dithered_cluster_ids=k_dithered_cluster_ids,
        algorithm_name="genediver",
        max_sample=max_sample,
        seed=seed,
        cluster_stabilities=cluster_stabilities,
        staging_dir=staging_dir
    )

    print()
    print("== RESULTS ==")
    print("K_deduped: {}".format(generated_k_deduped))
    if generated_k_deduped < top_k:
        print("Warning: generated K_deduped is less than top_k_clusters")
    # will not be greater than top_k_clusters since it is being created dynamically, no chance of old data
    # run hMETIS/METIS
    print("Top k clusters: {}".format(top_k))
    print("Generated k_deduped: {}".format(generated_k_deduped))
    print("total points in graph: {}".format(num_points))
    print("(gene_diver_k) total genediver clusters including large ones AND parents: {}".format(gene_diver_k))
    print("total points after deduping and taking top k clusters: {}".format(num_deduped_cluster_points))
    print("clustered fraction: {:.5f}".format(sample_proportion))

    with open(os.path.join(staging_dir, "judge_params.json"), "w") as f:
        f.write(json.dumps({
            "num_points_in_graph": num_points,
            "k_deduped": generated_k_deduped,
            "fraction_kept": sample_proportion
        }))


if __name__ == "__main__":
    main()
