#!/usr/bin/env python3
"""
This program is only taking the original paper sim 2 data and producing it in
the modern form usable by new python code.
"""
import collections
import json
import os


def preprocess(tdata_in, spatial_out, clusters_out, clusters_background_out, clustering_dir):
    """
    :param tdata_in:
    :param spatial_out:
    :param clusters_out:
    :param clusters_background_out:
    :param clustering_dir:
    """

    clusters = collections.defaultdict(list)
    background = list()
    points = list()
    with open(tdata_in, 'r') as f, open(os.path.join(clustering_dir, "spatial.txt"), "w") as of:
        of.write("dim1,dim2,classlabel\n")
        for line in f:
            line = line.strip()
            if line.startswith("#"):
                continue
            x, y, cluster = line.split()
            x = float(x)
            y = float(y)
            cluster = int(cluster)
            if cluster == 0:
                background.append(len(points))
            else:
                clusters[cluster].append(len(points))
            points.append((x, y, cluster))

            of.write("{},{},{}\n".format(x, y, cluster))

    with open(spatial_out, "w") as f:
        for point in points:
            f.write(json.dumps(point) + "\n")

    with open(clusters_out, "w") as f:
        for cluster in clusters:
            for i in clusters[cluster]:
                f.write(json.dumps({
                    "level": 0,
                    "id": i,
                    "label": cluster
                }) + "\n")

    with open(clusters_background_out, "w") as f:
        for cluster in clusters:
            for i in clusters[cluster]:
                f.write(json.dumps({
                    "level": 0,
                    "id": i,
                    "label": cluster
                }) + "\n")
        for i in background:
            f.write(json.dumps({
                "level": 0,
                "id": i,
                "label": "b"
            }) + "\n")


def main():
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("--staging-dir", "-t", required=True)

    args = parser.parse_args()

    staging_dir = os.path.expanduser(args.staging_dir)

    spatial_clustering_dir = os.path.join(staging_dir, "spatialHDS")

    if not os.path.exists(spatial_clustering_dir):
        os.makedirs(spatial_clustering_dir)

    preprocess(
        # this is the original matlab binary test data file checked it. It can
        #     also be regenerated with a different seed but good for
        #     reproducing original Auto-HDS results
        tdata_in="../../datasets/sim2/spatial/tdata.mat",
        spatial_out=os.path.join(staging_dir, "spatial.jsonl"),
        clusters_out=os.path.join(staging_dir, "labels.clusters.jsonl"),
        clusters_background_out=os.path.join(staging_dir, "labels_background.clusters.jsonl"),
        clustering_dir=spatial_clustering_dir
    )


if __name__ == "__main__":
    main()
