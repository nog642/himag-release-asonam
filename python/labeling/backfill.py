#!/usr/bin/env python3
"""
Backfilling CLI.

A config json and all the necessary files all go in one directory that gets passed as a CLI argument.

The config json looks like this:
{
    "source_files": [
        "source/for_judging_genediver - for_judging_genediver.csv",
        "source/for_judging_hmetis_flow - for_judging_hmetis.csv",
        "source/for_judging_kahip_flow - for_judging_kahip.csv"
    ],
    "target_files": [
        "for_judging_hmetis.csv"
    ],
    "get_cluster_names": False
}
"""
from argparse import ArgumentParser
from collections import defaultdict
import csv
import itertools
import json
import os
import sys
from timeit import default_timer

from lib import missingdict, read_csv, warn
from util import JudgedCsvReadingException, read_judged_csv


def calculate_edge_labels(labels):
    """
    :param labels:
    :type labels: dict[int, dict[str, bool]]
    :return:
    :rtype: dict[int, dict[(str, str), int]]
    """
    edge_labels = dict()  # dict: cluster ID -> dict: (node ID, node ID) -> weight
    for cluster_id, cluster_labels in labels.items():
        cluster_edge_labels = dict()
        for edge in itertools.combinations(sorted(cluster_labels), 2):
            if cluster_labels[edge[0]] and cluster_labels[edge[1]]:
                cluster_edge_labels[edge] = 1
            else:
                cluster_edge_labels[edge] = 0
        edge_labels[cluster_id] = cluster_edge_labels
    return edge_labels


def load_judged_edges(source_files):
    must_link_edges = missingdict(int)
    cannot_link_edges = missingdict(int)
    for source_filepath in source_files:
        labels, cluster_stabilities = read_judged_csv(source_filepath, use_sample_column=True)
        del cluster_stabilities

        edge_labels = calculate_edge_labels(labels)
        for cluster_edge_labels in edge_labels.values():
            for edge, weight in cluster_edge_labels.items():
                if weight:
                    if edge not in must_link_edges:
                        must_link_edges[edge] += 1
                else:
                    if edge not in cannot_link_edges:
                        cannot_link_edges[edge] += 1
    return must_link_edges, cannot_link_edges


def main():
    argparser = ArgumentParser()
    argparser.add_argument("--staging-dir", "-s", required=True)
    argparser.add_argument("--ml-fraction", "-f", type=float)
    argparser.add_argument("--v1", action="store_true")
    argparser.add_argument("--debug", action="store_true")
    args = argparser.parse_args()

    staging_dir = os.path.expanduser(args.staging_dir)
    ml_fraction = args.ml_fraction
    v1_algo = args.v1
    debug_mode = args.debug

    if v1_algo:
        ml_fraction = 1

    if not debug_mode and ml_fraction is None:
        argparser.error("the following arguments are required: --ml-fraction/-f")

    if v1_algo and debug_mode:
        print("cannot run v1 algo in debug mode.", file=sys.stderr)
        sys.exit(1)

    with open(os.path.join(staging_dir, "config.json")) as f:
        config_dict = json.load(f)

    source_files = config_dict["source_files"]
    target_files = config_dict["target_files"]
    get_cluster_names = config_dict["get_cluster_names"]

    # convert relative paths to absolute
    for i, source_file in enumerate(source_files):
        source_files[i] = os.path.join(staging_dir, source_file)
    for i, target_file in enumerate(target_files):
        target_files[i] = os.path.join(staging_dir, target_file)

    print("Loading input files...", end="", flush=True)
    start_time = default_timer()

    must_link_edges, cannot_link_edges = load_judged_edges(source_files)
    # These two sets are not disjoint since there are multiple source files.

    x_labels = set()
    required_fields = ("cluster_id", "label")
    if get_cluster_names:
        all_node_cluster_names = defaultdict(lambda: defaultdict(int))
        required_fields += ("cluster_name",)
    for source_filepath in source_files:
        if get_cluster_names:
            # cluster_names = defaultdict(lambda: defaultdict(int))
            cluster_names = dict()
            clustering = defaultdict(list)
        for row_number, row in read_csv(source_filepath,
                                        required_fieldnames=required_fields):
            try:
                cluster_id = int(row["cluster_id"])
            except ValueError as e:
                raise JudgedCsvReadingException(
                    "unable to parse cluster ID {!r} as int (row {}))"
                    .format(row["cluster_id"], row_number)
                ) from e

            node_id = row["node_id"]
            belongs = row["label"]

            if belongs == "x":
                x_labels.add(node_id)
                continue

            if get_cluster_names and belongs == "1":
                cluster_name = row["cluster_name"]
                if cluster_name:  # non-empty string
                    cluster_names[cluster_id] = cluster_name
                clustering[cluster_id].append(node_id)

        if get_cluster_names:
            for cluster_id, cluster_name in cluster_names.items():
                for node_id in clustering[cluster_id]:
                    all_node_cluster_names[node_id][cluster_name] += 1
            del cluster_names

    print(" done. (time={:.3f} s)".format(default_timer() - start_time))

    metrics = {
        "clusters skipped because of conflict": 0,
        "clusters backfilled": 0,
        "number of must-links": len(must_link_edges),
        "number of cannot-links": len(cannot_link_edges),
    }

    for target_filepath in target_files:

        print("Loading target file {!r}...".format(target_filepath), end="", flush=True)
        start_time = default_timer()

        clustering = defaultdict(set)
        for row_number, row in read_csv(target_filepath,
                                        required_fieldnames=("cluster_id",
                                                             "node_id")):
            try:
                cluster_id = int(row["cluster_id"])
            except ValueError as e:
                raise JudgedCsvReadingException(
                    "unable to parse cluster ID {!r} as int (row {}))"
                    .format(row["cluster_id"], row_number)
                ) from e
            clustering[cluster_id].add(row["node_id"])

        print(" done. (time={:.3f} s)".format(default_timer() - start_time))

        print("Backfilling in memory for target file {!r}...".format(target_filepath))
        start_time = default_timer()

        global_belong_nodes = dict()
        for i, (cluster_id, cluster) in enumerate(clustering.items(), 1):

            if not i % 1000:
                print("Loading cluster {} of {} ({!r}) ({} nodes) (cumulative time = {:.3f} s)"
                      .format(i, len(clustering), cluster_id, len(cluster), default_timer() - start_time))

            edge_vals = dict()
            for edge in itertools.combinations(sorted(cluster), 2):
                must_link_count = must_link_edges[edge]
                cannot_link_count = cannot_link_edges[edge]
                if must_link_count == 0:
                    continue
                must_link_proportion = must_link_count / (must_link_count + cannot_link_count)

                if debug_mode:
                    edge_vals[edge] = must_link_proportion
                else:
                    if must_link_proportion >= ml_fraction:
                        edge_vals[edge] = 1
                    else:
                        edge_vals[edge] = 0

            skip_cluster = False
            belong_nodes = defaultdict(int)
            if debug_mode:
                node_denominators = defaultdict(int)
            for (node_id_1, node_id_2), edge_val in edge_vals.items():
                if edge_val > 0:
                    if debug_mode:
                        belong_nodes[node_id_1] += edge_val
                        belong_nodes[node_id_2] += edge_val
                        node_denominators[node_id_1] += 1
                        node_denominators[node_id_2] += 1
                    else:
                        if node_id_1 not in belong_nodes:
                            belong_nodes[node_id_1] = 1
                        if node_id_2 not in belong_nodes:
                            belong_nodes[node_id_2] = 1
                elif v1_algo:
                    skip_cluster = True
                    metrics["clusters skipped because of conflict"] += 1
                    break

            if skip_cluster:
                continue

            if debug_mode:
                for node_id in belong_nodes:
                    belong_nodes[node_id] /= node_denominators[node_id]

            if belong_nodes:
                metrics["clusters backfilled"] += 1
                global_belong_nodes.update(belong_nodes)
            # else there were no conflicts but no nodes to backfill either

        out_filepath = target_filepath.rsplit('.', 1)[0] + ".out.csv"

        print("Done backfilling in memory for target file {!r}. (time={:.3f} s)"
              .format(target_filepath, default_timer() - start_time))

        print("Writing output file {!r}...".format(out_filepath))
        start_time = default_timer()

        with open(out_filepath, "w") as out_file, open(target_filepath) as source_file:

            # csv.reader handles quoting (where commas are in the cell text)
            # default delimiter and quotechar are correct
            csv_reader = csv.reader(source_file)

            header = next(csv_reader)
            num_cols = len(header)
            col_nums = dict()
            find_cols = ("node_id", "label")
            if get_cluster_names:
                find_cols += ("cluster_name",)
            for colname in find_cols:
                # TODO: use csv.DictWriter
                try:
                    col_nums[colname] = header.index(colname)
                except ValueError as e:
                    raise JudgedCsvReadingException("missing column in header: {}"
                                                    .format(colname)) from e

            csv_writer = csv.writer(out_file)
            header.append("backfilled")
            csv_writer.writerow(header)

            for row_number, row in enumerate(csv_reader, 1):
                if len(row) != num_cols:
                    raise JudgedCsvReadingException(
                        "wrong number of cols in row {}"
                        .format(row_number)
                    )

                row += ("",)  # backfilled column

                node_id = row[col_nums["node_id"]]

                if node_id in global_belong_nodes:
                    row = list(row)
                    row[col_nums["label"]] = str(global_belong_nodes[node_id])
                    row[-1] = "1"  # backfilled column

                    if node_id in x_labels:
                        warn("node {!r} is backfilled as {!r}, but was also "
                             "marked as 'x'; leaving it blank."
                             .format(node_id, global_belong_nodes[node_id]),
                             Warning)
                        row[col_nums["label"]] = ""
                        row[-1] = ""  # backfilled column

                elif node_id in x_labels:
                    row[col_nums["label"]] = "x"
                    row[-1] = "1"  # backfilled column

                if get_cluster_names and node_id in all_node_cluster_names:
                    node_cluster_names = all_node_cluster_names[node_id]
                    row[col_nums["cluster_name"]] = "backfill guess: " + max(
                        node_cluster_names,
                        key=node_cluster_names.get
                    )

                if row[-1] and not row[col_nums["label"]]:
                    warn("Row marked as backfilled with no label.", Warning)

                csv_writer.writerow(row)

        print("Done writing output file {!r}. (time={:.3f} s)"
              .format(out_filepath, default_timer() - start_time))

    print(json.dumps(metrics, indent=4, sort_keys=True))


if __name__ == "__main__":
    main()
