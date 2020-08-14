#!/usr/bin/env python3
from collections import defaultdict
import json, os, copy
from timeit import default_timer


class NativeReadWrite:

    def __init__(self, staging_dir, experiment_name):
        self._check_dir_exists(staging_dir, "staging directory")

        self.staging_dir = staging_dir
        self.experiment_name = experiment_name

        self.experiment_dir = os.path.join(staging_dir, experiment_name)

    @staticmethod
    def _check_dir_exists(dirpath, display_name):
        if not os.path.exists(dirpath):
            raise ValueError("{} '{}' does not exist".format(display_name,
                                                             dirpath))
        if not os.path.isdir(dirpath):
            raise ValueError("{} '{}' is not a directory".format(display_name,
                                                                 dirpath))

    def count_graph_nodes(self):

        num_nodes = 0
        start_time = default_timer()
        last_time = start_time

        with open(os.path.join(self.staging_dir, self.experiment_name + ".jsonl")) as graph_file:
            for i, line in enumerate(map(str.strip, graph_file), 1):

                if i % 10000 == 0:
                    now = default_timer()
                    print("\tReading data for adjacency matrix row {:,} "
                          "({:.2f} s cumulative) (Δcumulative={:.3f} s)"
                        .format(
                        i,
                        now - start_time,
                        now - last_time
                    ))
                    last_time = default_timer()
                # each line represents a node
                num_nodes += 1

        return num_nodes

    def count_graph(self, jaccard_threshold):

        num_nodes = 0
        unique_edges = set()
        start_time = default_timer()
        last_time = start_time

        with open(os.path.join(self.staging_dir, self.experiment_name + ".jsonl")) as graph_file:
            for i, line in enumerate(map(str.strip, graph_file), 1):

                if i % 1000 == 0:
                    now = default_timer()
                    print("\tReading data for adjacency matrix row {:,} "
                          "({:.2f} s cumulative) (Δcumulative={:.3f} s)"
                        .format(
                        i,
                        now - start_time,
                        now - last_time
                    ))
                    last_time = default_timer()

                    # format {"connections": [[1, 0.5], [1241, 0.5151515151515151]], "id": 0}
                node_information = json.loads(line)
                node_id_1 = node_information["id"]
                for node_id_2, weight in node_information["connections"]:
                    if weight >= jaccard_threshold:
                        if node_id_1 < node_id_2:
                            edge_id = str(node_id_1) + "." + str(node_id_2)
                        elif node_id_2 < node_id_1:
                            edge_id = str(node_id_2) + "." + str(node_id_1)
                        else:
                            # self edge ignored
                            continue
                        if edge_id not in unique_edges:
                            unique_edges.add(edge_id)

                num_nodes += 1  # each line represents a node

        return num_nodes, len(unique_edges)

    def read_graph(self, jaccard_threshold):
        """
        Read graph from graph line JSON.
        :return: input_graph: dict: (node1, node2) -> weight
                 num_nodes: number of nodes
        :rtype: (list[dict[str, Any]], int, int)
        """
        input_graph = list()
        num_nodes = 0

        start_time = default_timer()
        last_time = start_time

        unique_edges = set()

        with open(os.path.join(self.staging_dir, self.experiment_name + ".jsonl")) as graph_file:
            for i, line in enumerate(map(str.strip, graph_file), 1):

                if len(line.strip()) == 0:
                    # ignore empty line
                    continue

                if i % 1000 == 0:
                    now = default_timer()
                    print("\tReading data for adjacency matrix row {:,} "
                          "({:.2f} s cumulative) (Δcumulative={:.3f} s)"
                        .format(
                        i,
                        now - start_time,
                        now - last_time
                    ))
                    last_time = default_timer()

                    # format {"connections": [[1, 0.5], [1241, 0.5151515151515151]], "id": 0}

                node_information = json.loads(line)
                node_id_1 = node_information["id"]
                pruned_connections = list()

                for node_id_2, weight in node_information["connections"]:
                    if weight >= jaccard_threshold:
                        pruned_connections.append((node_id_2, weight))

                        if node_id_1 < node_id_2:
                            edge_id = str(node_id_1) + "." + str(node_id_2)
                        elif node_id_2 < node_id_1:
                            edge_id = str(node_id_2) + "." + str(node_id_1)
                        else:
                            # self edge ignored
                            continue
                        if edge_id not in unique_edges:
                            unique_edges.add(edge_id)

                num_nodes += 1  # each line represents a node

                if len(pruned_connections) == 0:
                    continue

                input_graph.append({
                    "id": node_id_1,
                    "connections": pruned_connections
                })

        return input_graph, num_nodes, len(unique_edges)

    def read_mapping(self):
        """
        Reads mapping of runGraphHDS IDs to external IDs for nodes.
        :return: hdsg_to_external_id_mapping: dict: node ID -> node string ID
        :rtype: dict[int, str]
        """
        hdsg_to_external_id_mapping = dict()
        filename = os.path.join(self.staging_dir,
                                self.experiment_name + ".mapping.tsv")
        with open(filename) as f:
            for i, line in enumerate(map(str.strip, f), 1):
                try:
                    node_id, node_string, _ = line.split("\t")
                except ValueError as e:
                    raise RuntimeError(
                        "wrong number of columns in line {} of {}"
                        .format(i, filename)
                    ) from e
                node_id = int(node_id)

                hdsg_to_external_id_mapping[node_id] = node_string

        return hdsg_to_external_id_mapping

    def read_graph_lab(self):
        """
        Read Gene DIVER graph_lab file, produced by Gene DIVER during
        clustering.
        Note that this information is NOT produced by runGraphHDS.py.
        Point description IS the external node ID; all internal IDs are
        unreliable between Gene DIVER, runGraphHDS.py, hMETIS, and other
        algorithms so DO NOT pre-process ID mapping.
        :return: cluster_points: dict: Cluster ID -> set of points
                 stabilities: dict: cluster ID -> stability
        :rtype: (dict[int, set[str]], dict[int, float])
        """
        self._check_dir_exists(self.experiment_dir, "experiment directory")

        cluster_points = defaultdict(set)
        stabilities = dict()
        with open(os.path.join(self.experiment_dir, "graph_lab.csv")) as f:

            next(f)  # discard first line (header)

            for line in map(str.strip, f):
                # line format: clusterId, stability, ptIdx, ptDescription
                # ptIdx does NOT correspond to node IDs used in the graph file, and
                #     should be ignored.
                cluster_id, stability, _, point_description = line.split(",")
                cluster_id = int(cluster_id)

                # stability is always the same for a given cluster ID
                if cluster_id not in stabilities:
                    stabilities[cluster_id] = float(stability)

                cluster_points[cluster_id].add(point_description)

        return dict(cluster_points), stabilities
