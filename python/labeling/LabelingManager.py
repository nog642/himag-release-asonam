#!/usr/bin/env python3
import os
from random import Random

from dataReadWrite.NativeReadWrite import NativeReadWrite
from dataReadWrite.ReadWriteAll import ALGORITHMS


class LabelingManager:
    # TODO: support any data set

    # TODO: maybe refactor some of the static methods to non-static
    # TODO:     e.g. in stage 3 store clustering in instance variable and mutate it

    def __init__(self, staging_dir, experiment_name, algo=None):
        # TODO: there is never an instance of LabelingManager being created
        self.native_readwriter = NativeReadWrite(staging_dir, experiment_name)
        self.staging_dir = staging_dir

        if algo is not None:
            if algo not in ALGORITHMS:
                raise ValueError

        self.algo = algo

    @staticmethod
    def count_unique_points_in_clusters(cluster_points):
        """
        Count the number of unique nodes in a clustering.
        :param cluster_points: The clustering.
        :type cluster_points: dict[int, set[collections.Hashable]]
        :return: Number of unique nodes in clustering.
        :rtype: int
        """
        return sum(map(len, cluster_points.values()))

    # TODO: should this be static? has more parameters than expected
    @staticmethod
    def generate_judging_files(clustering, filtered_clustering,
                               top_k_cluster_ids, k_dithered_cluster_ids,
                               algorithm_name, max_sample, seed,
                               cluster_stabilities, staging_dir,
                               hdsg_to_external_id_mapping=None):
        """
        generate 3 files, for_judging_<algo>.csv, for_judging_<algo>.csv.top_k, for_judging_<algo>.csv.k_dithered
        :param clustering:
        :param filtered_clustering:
        :param top_k_cluster_ids:
        :type top_k_cluster_ids: collections.Iterable
        :param k_dithered_cluster_ids:
        :type k_dithered_cluster_ids: collections.Iterable
        :param algorithm_name:
        :type algorithm_name: str
        :param max_sample:
        :type max_sample: int
        :param seed:
        :type seed: collections.Hashable
        :param cluster_stabilities:
        :type cluster_stabilities: dict[int, float]
        :param staging_dir:
        :type staging_dir: str
        :param hdsg_to_external_id_mapping:
        :type hdsg_to_external_id_mapping: dict | None
        """

        sampled_clustering = LabelingManager._sample_cluster_points(
            cluster_points=filtered_clustering,
            sample_per_cluster=max_sample,
            seed=seed
        )

        if hdsg_to_external_id_mapping is None:
            LabelingManager.write_judging_csv(
                cluster_points=clustering,
                sampled_cluster_points=sampled_clustering,
                stabilities=cluster_stabilities,
                algo_name=algorithm_name,
                staging_dir=staging_dir
            )
        else:
            LabelingManager.write_judging_csv(
                cluster_points=clustering,
                sampled_cluster_points=sampled_clustering,
                stabilities=cluster_stabilities,
                algo_name=algorithm_name,
                staging_dir=staging_dir,
                hdsg_to_external_id_mapping=hdsg_to_external_id_mapping
            )

        LabelingManager.write_cluster_ids_file(
            os.path.join(staging_dir, "for_judging." + algorithm_name + ".cluster_ids.top_k"),
            top_k_cluster_ids
        )
        LabelingManager.write_cluster_ids_file(
            os.path.join(staging_dir, "for_judging." + algorithm_name + ".cluster_ids.dithered"),
            k_dithered_cluster_ids
        )

    @staticmethod
    def write_cluster_ids_file(output_path, cluster_ids):
        """
        Writes to the file a list of the cluster ids that were selected
        :param output_path:
        :type output_path: str
        :param cluster_ids:
        :type cluster_ids: collections.Iterable
        """
        with open(output_path, "w") as output_file:
            output_file.write("\n".join(map(str, cluster_ids)))
        print("Wrote cluster_ids to file: {}".format(output_path))

    @staticmethod
    def filter_clustering(clustering, cluster_stabilities, top_k, k_dithered):
        """
        returns partial dithered clusters (topk + remaining dithered) and fully
        dithered clusters_ids, and topk_clusterids
        :param clustering:
        :type clustering: dict[int, T]
        :param cluster_stabilities:
        :type cluster_stabilities: dict[int, numbers.Real]
        :param top_k:
        :type top_k: int
        :param k_dithered:
        :type k_dithered: int
        :return: filtered_clustering
        :rtype: (dict[int, T], list[int], list[int])
        """
        num_algo_clusters = len(clustering)
        if num_algo_clusters == top_k:
            return clustering.copy(), set(clustering), set(clustering)
        elif num_algo_clusters < top_k:
            raise ValueError("cannot get top {} clusters from clustering with "
                             "{} clusters".format(top_k, num_algo_clusters))

        sorted_cluster_ids = sorted(
            clustering,
            key=cluster_stabilities.get,
            reverse=True
        )

        # {cluster_id: clustering[cluster_id] for cluster_id in sorted_cluster_ids[:top_k]}
        top_k_cluster_ids = sorted_cluster_ids[:top_k]
        if k_dithered > 0:
            remaining_cluster_ids = sorted_cluster_ids[top_k:]
            len_remaining_clusters = len(remaining_cluster_ids)
            skip_value = float(len_remaining_clusters) / (k_dithered-1)
            # we don't need to skip clusters if there are not enough
            if skip_value < 1.0:
                print("Warning! total number of clusters - topk is less than "
                      "k_dithered, taking all clusters")
                skip_value = 1
            cursor = 0.0

            dither_cluster_ids = list()
            # we skip the first round(skip_value) for first position then take k_dithered including last one
            # we are calculating the extra dithered only here
            while True:
                cursor_idx = round(cursor)
                # keep appending if its not at the end otherwise make sure to get the last one
                if cursor_idx < len_remaining_clusters:
                    dither_cluster_ids.append(remaining_cluster_ids[cursor_idx])
                else:
                    if dither_cluster_ids[-1] != remaining_cluster_ids[-1]:
                        dither_cluster_ids.append(remaining_cluster_ids[-1])
                    break

                cursor += skip_value

            full_dither_cluster_ids = top_k_cluster_ids + dither_cluster_ids
        else:
            full_dither_cluster_ids = top_k_cluster_ids

        return (
            {cluster_id: clustering[cluster_id]
             for cluster_id in full_dither_cluster_ids},
            top_k_cluster_ids,
            full_dither_cluster_ids
        )

    @staticmethod
    def _sample_cluster_points(cluster_points, sample_per_cluster, seed):
        """
        Samples clusters based on sample_per_cluster.
        :param cluster_points: cluster ID -> list of points
        :type cluster_points: dict[int, T <= (collections.Sequence[U] | set[U])]
        :param sample_per_cluster: points to be sampled per cluster
        :type sample_per_cluster: int
        :param seed: random seed
        :type seed: collections.Hashable
        :return: cluster_id -> list of points
        :rtype: dict[int, set[U]]
        """
        print("Sampling cluster points...", end="", flush=True)
        sampled_cluster_points = dict()
        seeded_random = Random(seed)
        for cluster_id, cluster in cluster_points.items():
            if len(cluster) >= sample_per_cluster:  # only random sample if there are more points then sample
                sampled_cluster_points[cluster_id] = set(seeded_random.sample(cluster, sample_per_cluster))
            else:  # if the sample is more than the points in cluster, then leave it
                sampled_cluster_points[cluster_id] = set(cluster)
        print(" done.")
        return sampled_cluster_points

    @staticmethod
    def write_judging_csv(cluster_points, sampled_cluster_points, staging_dir, stabilities=None,
                          hdsg_to_external_id_mapping=None, algo_name=None):
        """
        Outputs to csv file.
        :param cluster_points: cluster_id -> cluster
        :type cluster_points: dict[int, set[int]] | dict[int, set[Hashable]]
        :param sampled_cluster_points: cluster_id -> cluster
        :type sampled_cluster_points: dict[int, set[int]]
        :param staging_dir:
        :type staging_dir: str
        :param stabilities: dict: cluster ID -> stability
        :type stabilities: dict[int, float]
        :param hdsg_to_external_id_mapping: point_id -> instagram_id
        :type hdsg_to_external_id_mapping: dict[int, str]
        :param algo_name:
        :type algo_name: str
        """
        if algo_name is None:
            output_file_path = os.path.join(staging_dir, "for_judging.csv")
        else:
            output_file_path = os.path.join(
                staging_dir,
                "for_judging_{}.csv".format(algo_name)
            )

        print("Outputting cluster points to '{}'...".format(output_file_path),
              end="", flush=True)

        # sort sampled_cluster_points based on stabilities
        if stabilities is None:
            sorted_cluster_ids = list(sampled_cluster_points)
            for cluster_id in cluster_points:
                if cluster_id not in sampled_cluster_points:
                    sorted_cluster_ids.append(cluster_id)
        else:
            sorted_cluster_ids = sorted(
                sampled_cluster_points,
                key=stabilities.get,
                reverse=True
            )
            sorted_cluster_ids += sorted(
                (cluster_id for cluster_id in cluster_points
                 if cluster_id not in sampled_cluster_points),
                key=stabilities.get,
                reverse=True
            )

        url_present = None
        with open(output_file_path, "w") as output_file:
            for cluster_id in sorted_cluster_ids:

                if cluster_id in sampled_cluster_points:
                    sampled_cluster = sampled_cluster_points[cluster_id]
                else:
                    sampled_cluster = set()

                # reorder points to group all the sample ones in a cluster together for ease of judging
                cluster_points_order = list()
                for point in sampled_cluster:
                    cluster_points_order.append(point)
                for point in cluster_points[cluster_id]:
                    if point not in sampled_cluster:
                        cluster_points_order.append(point)

                for point in cluster_points_order:
                    if point in sampled_cluster:
                        sample = 1
                    else:
                        sample = 0

                    # if there is a mapping then convert the point to the external id
                    if hdsg_to_external_id_mapping is not None:
                        point = hdsg_to_external_id_mapping[point]

                    # lazy first time format detector
                    if url_present is None:
                        # only runs on the first line, so header can be written here
                        if stabilities is None:
                            output_file.write("cluster_id,node_id,sample,label,cluster_name")
                        else:
                            output_file.write("cluster_id,stability,node_id,sample,label,cluster_name")
                        if ":" in point:
                            output_file.write(",url\n")
                            url_present = True
                        else:
                            output_file.write("\n")
                            url_present = False

                    desc_parts = point.split(":")

                    if stabilities is None:
                        output_line = "{},{},{},,".format(
                            cluster_id,
                            desc_parts[0],
                            sample
                        )
                    else:
                        output_line = "{},{},{},{},,".format(
                            cluster_id,
                            stabilities[cluster_id],
                            desc_parts[0],
                            sample
                        )

                    if url_present:
                        output_line += ",{}".format(":".join(desc_parts[1:]))

                    output_file.write(output_line + "\n")

        print(" done. ")
