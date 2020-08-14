#!/usr/bin/env python3
import json
import os
import sys


def load_data(fname):
    """
    Reads a .spatial.jsonl file.
    :param fname: Location of input data file.
    :return data: List of data
    :return labels:
    """

    data = []
    labels = []
    with open(fname) as f:
        for line in f:
            x, y, label = json.loads(line)
            data.append((x, y))
            labels.append(label)

    return data, labels


def sq_euc_dist(p1, p2):
    """
    compute sq. euclidean distance between two points
    :param p1:
    :param p2:
    :return:
    :rtype: float
    """
    return (p1[0] - p2[0])**2 + (p1[1] - p2[1])**2


def graph_sim(p1, p2, max_sq_dist, power):
    """
    :param p1: point 1 coordinates
    :param p2: point 2 coordinates
    :param max_sq_dist: maximum distance between any two points possible on this
                     data for scaling before computing sim
    :param power:
    # :param threshold: below this similarity threshold return 0.0
    :return:
    :rtype: float
    """
    norm_dist = (sq_euc_dist(p1, p2)**0.5)/(max_sq_dist**0.5)
    # our similarity formula guarantees scaling between 0 and 1
    return (1 - norm_dist)**power


def spatial2graph(staging_dir, graph_data_name, power, threshold):
    """
    loads spatial data file and label file and produces files used by auto-HDS
    graph runner as input
    :param staging_dir:
    :type staging_dir: str
    :param graph_data_name:
    :type graph_data_name: str
    :param power:
    :type power: int
    :param threshold:
    :type threshold: float
    """

    spatial_data_file_path = os.path.join(staging_dir, "spatial.jsonl")
    graph_out_file_path = os.path.join(staging_dir,  graph_data_name + ".jsonl")

    try:
        points, labels = load_data(spatial_data_file_path)
    except FileNotFoundError:
        print("Could not open spatial data required: {}, stopping conversion".format(spatial_data_file_path))
        sys.exit(1)
    n = len(points)

    # find the max distance between all points to enable normalization of
    #     distances between 0 and 1
    max_sq_dist = 0.
    print("Computing data scale...")
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            pdist = sq_euc_dist(points[i], points[j])
            if pdist > max_sq_dist:
                print("Found largest sq. euclidean distance of {} "
                      "...".format(pdist))
                max_sq_dist = pdist

    print("Computing graph similarities...")
    graph_points = dict()
    pair_count = 0
    for i in range(n):
        graph_points[i] = list()
        for j in range(n):
            if i == j:
                continue
            sim = graph_sim(points[i], points[j], max_sq_dist, power)
            if sim > threshold:
                graph_points[i].append((j, sim))
                pair_count += 1

    print("Found and saved {} pairs above similarity threshold of {} into file: {}"
          .format(pair_count, threshold, graph_out_file_path))

    with open(graph_out_file_path, "w") as f:
        for i in graph_points:
            f.write(json.dumps({
                "id": i,
                "connections": graph_points[i]
            }) + "\n")


def main():  # function exists to avoid global variables
    from argparse import ArgumentParser

    # TODO: add appropriate stratification so that we don't get oversampling
    # TODO:     from larger clusters
    parser = ArgumentParser()
    parser.add_argument("--staging-dir", "-t", required=True)
    parser.add_argument("--graph-data-name", "-g", default="graph",
                        help="output converted graph data set name")
    parser.add_argument("--power", "-p", default=2.0, type=float,
                        help="power, higher the value the greater the decay "
                             "1.0 causes similarity to decrease in proportion "
                             "to sq. euclidean distance. >1 causes faster "
                             "decay, <1 causes slower decay")
    parser.add_argument("--sim-threshold", "-s", default=0.0, type=float)

    args = parser.parse_args()

    staging_dir = os.path.expanduser(args.staging_dir)
    graph_data_name = args.graph_data_name
    power = args.power
    sim_threshold = args.sim_threshold

    spatial2graph(
        staging_dir=staging_dir,
        graph_data_name=graph_data_name,
        power=power,
        threshold=sim_threshold
    )

    exp_params_file = os.path.join(staging_dir, "experiment_params.txt")
    exp_params = {
        "graph_sim": "1-normalized euclidean",
        "power": power,
        "sim-threshold": sim_threshold
    }

    with open(exp_params_file, "w") as ef:
        ef.write("{}\n".format(json.dumps(exp_params)))


if __name__ == "__main__":
    main()
