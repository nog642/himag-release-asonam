#!/usr/bin/env python3
from collections import defaultdict
import itertools
import json
import math
import os
from random import Random
from timeit import default_timer
from urllib.parse import quote_plus

from dataReadWrite.ReadWriteAll import ALGORITHMS
from graphDataAnalysis.GraphDataStagerException import GraphDataStagerException
from graphDataAnalysis.GraphLabels import GraphLabels
from lib import comb, IntToStrDict, reverse_dict

ALGO_NAMES = set(ALGORITHMS.keys()) | {"autohds-g"}  # set for nice repr


class GraphDataStager:

    DATA_NAMES = {
        "pokec": {
            "max_interest_len": 20,
            "min_interest_occurrence": 2,
            "label_inject_fraction": 0.5,  # percentage that is injected into graph
            "data_alpha": 0.0,
            "sum_edges": True,
            "k_regularization": 2,
            "save_autoHDS-G_native_format": False,
            "interests_file_name": "soc-pokec-profiles.txt",
            "network_file_name": "soc-pokec-relationships.txt"
        },
        "livejournal": {
            "min_interest_occurrence": 500,
            "label_inject_fraction": 0.5,  # percentage that is injected into graph
            "data_alpha": 0.0,
            "sum_edges": True,
            "k_regularization": 2,
            "save_autoHDS-G_native_format": False,
            "interests_file_name": "com-lj.all.cmty.txt",
            "network_file_name": "com-lj.ungraph.txt"
        },
        "sim2_partitional": {
            "save_autoHDS-G_native_format": True
        },
        "sim2_edge": {
            "num_edge_labels": False,  # False for exhaustive, else int
            "save_autoHDS-G_native_format": True
        },
        "socialbot": {
            "save_autoHDS-G_native_format": False
        }
    }

    COMMUNITY_DATA_SETS = {"pokec", "livejournal"}  # todo: check if thats the right way to do it

    def __init__(self, staging_dir, data_name, experiment_name, seed, num_points_sample,
                 sim_threshold, max_edges, debug, label_inject_fraction):

        # must be in valid data names
        if data_name not in GraphDataStager.DATA_NAMES:
            raise GraphDataStagerException("Valid data set names: {}, received: {}"
                                           .format(set(GraphDataStager.DATA_NAMES.keys()), data_name))

        if data_name in GraphDataStager.COMMUNITY_DATA_SETS:
            self.generate_method = "_generate_graph_and_labels_communities"
        else:
            self.generate_method = "_generate_graph_and_labels_" + data_name

        # check if the method exists for that data name
        if hasattr(GraphDataStager, self.generate_method) and callable(getattr(GraphDataStager, self.generate_method)):
            print("Found method: {} for datasets {}"
                  .format(self.generate_method, data_name))
        else:
            raise GraphDataStagerException(
                "Could not find a valid method {} for data name {}, please add"
                " in the GraphDataStager class!"
                .format(self.generate_method, data_name)
            )

        # TODO: this is a hack because we had to change this very often to optimize external dataset runs
        if (label_inject_fraction is not None) and (data_name in GraphDataStager.COMMUNITY_DATA_SETS):
            if (label_inject_fraction > 1.0) or (label_inject_fraction < 0.0):
                raise GraphDataStagerException("Invalid label_inject_fraction passed, must be between 0 and 1. Got: {}"
                                               .format(label_inject_fraction))
            self.DATA_NAMES[data_name]["label_inject_fraction"] = label_inject_fraction

        self.data_name = data_name
        self.experiment_name = experiment_name

        # example, pokec root dir
        self.input_data_dir = os.path.join(staging_dir, data_name)
        # input_data_dir must exist
        if not os.path.exists(self.input_data_dir):
            raise GraphDataStagerException("Input data dir path: {} not found!".format(self.input_data_dir))

        # example, pokec/node_100k.n_1.li_0.1
        self.output_data_dir = os.path.join(self.input_data_dir, experiment_name)

        if not os.path.exists(self.output_data_dir):
            os.makedirs(self.output_data_dir)

        self.graph_file_path = os.path.join(self.output_data_dir, "graph")
        self.labels_file_path = os.path.join(self.output_data_dir, "labels")

        self.sim_threshold = sim_threshold

        if self.sim_threshold >= 0:
            print("Similarity threshold: {}".format(self.sim_threshold))
        else:
            raise GraphDataStagerException("Similarity threshold must be >= 0! Recieved: {}"
                                           .format(self.sim_threshold))

        self.num_points_sample = num_points_sample
        # seed values so that same data will come each time with specific seed
        self.random = Random(seed)
        self.max_edges = max_edges
        self.debug = debug

        # create data set dir if not already there

        # set of all sampled vertices given a num_points_sample
        self.all_sample_nodes = set()

        # measurements related code this is computed lazily
        # do not access self._node_based_graph directly
        # access this through the property self.node_based_graph
        self._node_based_graph = None  # dict: node ID -> (dict: node ID -> weight)

        # needed for edge based labels generation
        self.edge_labels = dict()  # dict: (node ID 1, node ID 2) -> weight

        self.partitional_labels = dict()  # dict: node ID -> cluster ID

        # edges for the graph dataset sampled for saving
        # format: dict of (node ID, node ID) -> weight
        self.graph = dict()

        # set of nodes that exist in self.graph
        self.graph_nodes = set()

        # string -> int ID mapping
        # if this remains None, no mapping file will be written (in cases where
        #     there is no string ID)
        self.node_id_mapping = None

    def remove_disconnected_nodes(self):
        """
        Filters out any unconnected nodes from the graph before it is saved.
        Mutates self.graph_nodes.
        """
        num_nodes = len(self.graph_nodes)
        self.graph_nodes.clear()
        for node_a, node_b in self.graph:
            if node_a not in self.graph_nodes:
                self.graph_nodes.add(node_a)
            if node_b not in self.graph_nodes:
                self.graph_nodes.add(node_b)
        print("Removed {} disconnected nodes (Negative in case of data_alpha = 0)"
              .format(num_nodes - len(self.graph_nodes)))

    def save_graph(self):
        """
        save the generic generated graph (weighted)
        """
        edge_count = 0
        with open(self.graph_file_path, "w") as graph_file:
            for (node1, node2), weight in self.graph.items():
                edge_count += 1
                if edge_count % 250000 == 0:
                    print("Saved {} edges...".format(edge_count))

                graph_file.write("{}\t{}\t{}\n".format(node1, node2, weight))
        print("Saved {} edges to file: {}".format(edge_count, self.graph_file_path))

    def save_edge_labels(self):
        """
        save the generic generated graph (weighted)
        """
        edge_count = 0
        label_nodes = set()
        with open(self.labels_file_path, "w") as f:
            f.write(GraphLabels.LABEL_FORMAT_HEADERS[GraphLabels.LABEL_FORMAT.EDGE_BASED] + "\n")
            for edge, weight in self.edge_labels.items():
                node_1, node_2 = edge
                if node_1 not in label_nodes:
                    label_nodes.add(node_1)
                if node_2 not in label_nodes:
                    label_nodes.add(node_2)
                edge_count += 1
                if edge_count % 250000 == 0:
                    print("Saved {} edges ...".format(edge_count))

                f.write("{}\t{}\t{}\n".format(float(weight), *edge))
        print("Saved {} nodes {} edges to label file: {}".format(len(label_nodes), edge_count, self.labels_file_path))

    # TODO: add static method for saving partitional labels to file

    def _sample_nodes(self, all_nodes):
        """
        Samples nodes based on sampling etc.
        """
        # The all_nodes variable that is being passed (label nodes) is being iterated over later in the program, so
        # it is being saved as a copy if no sampling needed
        len_all_nodes = len(all_nodes)
        if self.num_points_sample is None:
            self.all_sample_nodes = all_nodes.copy()
            self.num_points_sample = len_all_nodes
        elif len_all_nodes < self.num_points_sample:
            print("Warning: shrunk number of nodes from {} to keep to the "
                  "maximum since only {} nodes were found".format(len_all_nodes, self.num_points_sample))
            self.num_points_sample = len_all_nodes
            self.all_sample_nodes = all_nodes.copy()
        elif len_all_nodes == self.num_points_sample:
            self.all_sample_nodes = all_nodes.copy()
        else:
            # sample nodes as asked for, for speed or desired dataset size by the user
            self.all_sample_nodes = set(self.random.sample(all_nodes, self.num_points_sample))

        print("Selected {} sampled nodes of {} nodes".format(len(self.all_sample_nodes), len_all_nodes))

    @staticmethod
    def _filter_by_nodes(data, filter_by_nodes):
        """
        Useful especially when testing and only part of a graph data file is
        loaded causing labels and graphs to be inconsistent.
        :param data: a dict or a set
        :return:
        """

        if isinstance(data, set):
            ret_data = set()
            for node in data:
                if node in filter_by_nodes:
                    ret_data.add(node)
        elif isinstance(data, dict):
            ret_data = dict()
            for node in data:
                if node in filter_by_nodes:
                    ret_data[node] = data[node]
        else:
            raise GraphDataStagerException("Unsupported type for filtering: {}".format(type(data)))

        print("Filtered down to {} entries from {}...".format(len(ret_data), len(data)))
        return ret_data

    def generate_graph_and_labels(self):
        """
        Wrapper that routes the call to the right hook for the dataset
        """
        getattr(self, self.generate_method)()

    def _generate_sim2_graph(self):
        """
        Loads the sim2 graph dataset removes any duplicates while loading by
        assuming graph is symmetrical.
        :return:
        """

        # pass 1 get graph nodes
        all_nodes = set()
        with open(os.path.join(self.input_data_dir, "graph.jsonl")) as f:
            for line in f:
                node_id = json.loads(line)["id"]
                all_nodes.add(node_id)

        self._sample_nodes(all_nodes)

        edges_processed = set()
        self.graph.clear()
        self.graph_nodes.clear()

        # pass 2 load the graph filter to sampled nodes
        with open(os.path.join(self.input_data_dir, "graph.jsonl")) as f:
            for line in f:
                line_dict = json.loads(line)
                node_id1 = line_dict["id"]

                if node_id1 not in self.all_sample_nodes:
                    continue

                for node_id2, weight in line_dict["connections"]:
                    if node_id2 not in self.all_sample_nodes:
                        continue

                    if node_id1 not in self.graph_nodes:
                        self.graph_nodes.add(node_id1)
                    if node_id2 not in self.graph_nodes:
                        self.graph_nodes.add(node_id2)

                    if node_id1 > node_id2:
                        edge_id = (node_id2, node_id1)
                    else:
                        edge_id = (node_id1, node_id2)

                    if edge_id in edges_processed:
                        continue
                    edges_processed.add(edge_id)
                    self.graph[edge_id] = weight

    def _load_sim2_labels(self):
        labels = dict()  # node ID -> cluster ID
        with open(os.path.join(self.input_data_dir, "labels_background.clusters.jsonl")) as f:
            for line in map(str.strip, f):
                if not line:
                    continue

                line_dict = json.loads(line)
                node_id = line_dict["id"]
                cluster_id = line_dict["label"]
                level = line_dict["level"]

                if level != 0:
                    raise GraphDataStagerException("multi-level labels are not supported")

                labels[node_id] = cluster_id

        return labels

    def _generate_graph_and_labels_sim2_partitional(self):
        """
        development dataset sim2 with partitional labels
        :return:
        """

        # graph
        self._generate_sim2_graph()
        # labels
        self.partitional_labels = self._load_sim2_labels()

        self.save_graph()

        with open(self.labels_file_path, "w") as f:
            f.write(GraphLabels.LABEL_FORMAT_HEADERS[GraphLabels.LABEL_FORMAT.CLUSTER_BASED] + "\n")
            for node_id, cluster_id in self.partitional_labels.items():
                f.write("{}\t{}\n".format(node_id, cluster_id))

    def _generate_graph_and_labels_sim2_edge(self):
        """
        development dataset sim2 with edge-based labels
        :return:
        """
        # graph
        self._generate_sim2_graph()
        # labels
        labels = self._load_sim2_labels()

        edge_labels = dict()

        if GraphDataStager.DATA_NAMES["sim2_edge"]["num_edge_labels"] is False:
            # exhaustive labels

            sorted_graph_nodes = sorted(self.graph_nodes)

            for edge in itertools.combinations(sorted_graph_nodes, 2):
                # itertools.combinations of sorted list gives sorted tuples

                label_1 = labels[edge[0]]
                label_2 = labels[edge[1]]

                if label_1 == "b" or label_2 == "b":
                    edge_labels[edge] = 0
                else:
                    edge_labels[edge] = label_1 == label_2

        else:
            while len(edge_labels) < GraphDataStager.DATA_NAMES["sim2_edge"]["num_edge_labels"]:

                if not len(edge_labels) % 10000 and len(edge_labels):
                    print("    {:,} of {:,} labels generated".format(len(edge_labels), GraphDataStager.DATA_NAMES["sim2_edge"]["num_edge_labels"]))

                node_id_1, node_id_2 = self.random.sample(self.graph_nodes, 2)

                if node_id_1 < node_id_2:
                    edge = (node_id_1, node_id_2)
                else:
                    edge = (node_id_2, node_id_1)

                if edge in edge_labels:
                    continue

                label_1 = labels[node_id_1]
                label_2 = labels[node_id_2]

                if label_1 == "b" or label_2 == "b":
                    edge_labels[edge] = 0
                else:
                    edge_labels[edge] = label_1 == label_2

        self.edge_labels = edge_labels

        self.save_graph()
        self.save_edge_labels()

    def _load_community_interest_data(self):

        print("##### Loading community interest data for: {}".format(self.data_name))
        start_time = default_timer()

        community_interests_path = os.path.join(self.input_data_dir, GraphDataStager.DATA_NAMES[self.data_name]["interests_file_name"])
        graph_index = dict()  # node_id -> interest_set
        node_count = 0
        uniq_interests = defaultdict(int)
        frequent_interests = 0
        total_interests = 0
        min_freq = GraphDataStager.DATA_NAMES[self.data_name]["min_interest_occurrence"]

        if self.data_name not in GraphDataStager.DATA_NAMES:
            raise NotImplementedError("community dataset not implemented: {}".format(self.data_name))

        with open(community_interests_path, "r") as interests_file:
            if self.data_name == "pokec":
                for line in interests_file:

                    node_count += 1
                    if node_count % 100000 == 0:
                        print("Found {} of {} nodes with interests...".format(len(graph_index), node_count))

                        if self.debug:
                            print("Stopping loading for testing. debug mode is ON!")
                            break

                    # Read pokec user node interests. Used to build the interests graph.
                    # For each row, the second value is the user ID (node) and the
                    #     12th value is the list of interests, comma delimited.
                    # Some lines do not have data and some don't have data for interests.
                    row_cols = line.split("\t")
                    if len(row_cols) < 12:
                        continue
                    interests = row_cols[11].split(", ")
                    if len(interests) == 0:
                        continue
                    # prune empty interests
                    interest_set = set()
                    for interest in interests:
                        if (len(interest.strip()) > 0) and (interest != "null") \
                                and (len(interest) < GraphDataStager.DATA_NAMES[self.data_name]["max_interest_len"]):
                            interest_set.add(interest)
                            total_interests += 1
                            interest_set.add(interest)
                    if len(interest_set) == 0:
                        # interest_set is empty
                        continue

                    node_id = int(row_cols[0])

                    graph_index[node_id] = interest_set

                # count interests with enough node frequency
                for interest, freq in uniq_interests.items():
                    if freq >= min_freq:
                        frequent_interests += 1

            elif self.data_name == "livejournal":
                # Load LiveJournal User Group Data (Used to Generate Data Graph)
                # Will generate a dict of user -> groups (graph_index) TODO: better name
                # Will generate a list of nodes with at least 2 groups (user_group_data_nodes)

                interest_id = 0

                for line in interests_file:
                    interest_id += 1
                    # the format nodes in a group joined by \t
                    nodes = {int(node) for node in line.split("\t")}
                    if interest_id % 100000 == 0:
                        print("Found {} nodes in {} interests with freq > {}..."
                              .format(len(graph_index), frequent_interests, min_freq))
                        if self.debug:
                            print("Stopping loading for testing. debug mode is ON!")
                            break

                    total_interests += 1
                    if len(nodes) < min_freq:
                        continue

                    frequent_interests += 1

                    for node in nodes:
                        if node not in graph_index:
                            graph_index[node] = set()
                        # converting the id to string allows us to use the same pipeline as pokec
                        graph_index[node].add(str(interest_id))
            else:
                raise NotImplementedError("community dataset not implemented: {}".format(self.data_name))

        # todo: fix print, gives 0 for both
        print("Done loading community interest data. Found {} unique interests, {} interests occuring with "
              "freq >= {}, (time={:.3f} s)"
              .format(len(uniq_interests), frequent_interests, min_freq, default_timer() - start_time))
        print("Found {} nodes with interests before sampling.".format(len(graph_index)))

        return graph_index

    def _generate_graph_and_labels_communities(self):
        """
        * saves graph file to self.output_data_dir/graph
        * generates self.graph
        * generates self.graph_nodes
        * may generate self.node_id_mapping (depending on the data set)
        * Generates the labels file
        """
        community_interests_path_cleaned = os.path.join(self.output_data_dir, "profiles.cleaned.txt")

        interest_graph_index = self._load_community_interest_data()
        community_networks_path = os.path.join(self.input_data_dir, GraphDataStager.DATA_NAMES[self.data_name]["network_file_name"])
        # load network graph to get set of nodes
        start_time = default_timer()

        print("##### Loading community network graph data (1) and getting nodes for: {}".format(self.data_name))
        network_nodes = set()
        edge_count = 0
        with open(community_networks_path, "r") as graph_file:

            if self.data_name == "livejournal":
                # discard 4 header lines exclusive to livejournal
                for _ in range(4):
                    next(graph_file)

            for edge in graph_file:  # edge is "[node1]\t[node2]"
                edge_count += 1
                if edge_count % 2500000 == 0:
                    print("Found {} edges of network graph...".format(edge_count))

                    if self.debug:
                        print("Stopping loading for testing. debug mode is ON!")
                        break

                # update nodes_in_graph with the two nodes in this edge
                node_1, node_2 = edge.split("\t")
                network_nodes.add(int(node_1))
                network_nodes.add(int(node_2))

        print("Done. (time={:.3f} s)".format(default_timer() - start_time))
        print("Found {} nodes in network graph".format(len(network_nodes)))

        intersecting_nodes = network_nodes.intersection(set(interest_graph_index.keys()))
        network_nodes = self._filter_by_nodes(network_nodes, intersecting_nodes)

        # For counting full size of interest graph before intersection, comment
        #     next line and look at estimated graph size
        interest_graph_index = self._filter_by_nodes(interest_graph_index, intersecting_nodes)

        self._sample_nodes(network_nodes)

        # This is not the case, but check just to make sure to remove nodes not
        #     in both network graph and interest graph.
        if len(network_nodes) != len(interest_graph_index):
            raise GraphDataStagerException("community data interests graph vs network graph have different nodes, "
                                           "need cleaning by removing extra ones in both")

        # The math shows that if you are regularizing as N/(D+R) where R is reg
        #     and N and D are # of shared tokens between posts vs total no.
        #     token between them, then this is the min. of tokens each posts
        #     need to have in order for their jaccard to be greater than the
        #     desired threshold, this allows us to prune most of the pairs
        #     (pre-filter)
        MIN_INTERESTS_NEEDED = math.ceil(self.sim_threshold * GraphDataStager.DATA_NAMES[self.data_name]["k_regularization"]
                                         / (1. - self.sim_threshold))

        # Populate node_id_mapping (string -> int) with all sample nodes so it
        #     has the nodes in interest graph and network graph.
        self.node_id_mapping = dict()
        for node in self.all_sample_nodes:
            interests = interest_graph_index[node]
            # This allows us to view interests in geneDIVER.
            # Make interests shorter (for the ptDescription) to avoid long
            #     interests when viewing URLs.
            str_node_id = "{}:https://www.google.com/search?q={}".format(
                node,
                quote_plus(",".join(interest[:5] for interest in sorted(interests)))
            )
            self.node_id_mapping[str_node_id] = node

        graph_rindex = dict()  # dict: interest -> set of nodes
        # prune graph index
        # build reverse index for speed

        # how many nodes did we add in the interest reverse index
        all_interest_nodes = set()
        for node in network_nodes:
            if node in self.all_sample_nodes:
                # If this node doesn't have enough interests, it will never have
                #     enough similarity (self.sim_threshold) due to
                #     regularization with any node, so do not add to node
                #     sample set and reverse index.
                if len(interest_graph_index[node]) < MIN_INTERESTS_NEEDED:  # TODO: why isn't this being done before sampling
                    self.all_sample_nodes.remove(node)  # TODO: changed this
                    del interest_graph_index[node]
                else:
                    # Only add if sampled and meets MIN_TERMS_NEEDED
                    for interest in interest_graph_index[node]:
                        if interest not in graph_rindex:
                            graph_rindex[interest] = set()
                        graph_rindex[interest].add(node)
                        if node not in all_interest_nodes:
                            all_interest_nodes.add(node)
            else:
                del interest_graph_index[node]
        del network_nodes

        # Prune out all interests that don't connect at least min_interest_occurrence people as it is just dead noise.
        print("Pruning out interests that are occurring less than {} times, also "
              "pruning out nodes that have only that interest..."
              .format(GraphDataStager.DATA_NAMES[self.data_name]["min_interest_occurrence"]))

        interest_prune_list = list()
        for interest in graph_rindex:
            if len(graph_rindex[interest]) < GraphDataStager.DATA_NAMES[self.data_name]["min_interest_occurrence"]:
                interest_prune_list.append(interest)
        for interest in interest_prune_list:
            for node in graph_rindex[interest]:
                interest_graph_index[node].remove(interest)
                if len(interest_graph_index[node]) == 0:
                    del interest_graph_index[node]
                    self.all_sample_nodes.remove(node)
            del graph_rindex[interest]

        print("Pruned to {} nodes, removed {} low frequency interests, left with {} unique interests"
              .format(len(self.all_sample_nodes), len(interest_prune_list), len(graph_rindex)))
        print("Saving pruned interests in: {}".format(community_interests_path_cleaned))
        with open(community_interests_path_cleaned, "w") as pcf:
            for node_id in interest_graph_index.keys():
                interest_list = ",".join(sorted(interest_graph_index[node_id]))
                pcf.write("{}\t{}\n".format(node_id, interest_list))

        # Save sample filtered network graph to staging dir.
        print("##### Loading community network data (2) and saving network graphe for sampled nodes.")
        start_time = default_timer()
        edge_count = 0
        network_edge_count = 0
        edge_labels_nodes = set()

        with open(community_networks_path, "r") as graph_file:

            if self.data_name == "livejournal":
                # discard 4 header lines exclusive to livejournal
                for i in range(4):
                    next(graph_file)

            for edge in map(str.strip, graph_file):  # edge is "[node1]\t[node2]"
                edge_count += 1
                if edge_count % 2500000 == 0:
                    print("Found {} edges of network graph...".format(edge_count))

                    if self.debug:
                        print("Stopping loading for testing. debug mode is ON!")
                        break

                # Update nodes_in_graph with the two nodes in this edge.
                node1, node2 = map(int, edge.split("\t"))

                # Filter out any node NOT in sample node set.
                if (node1 not in self.all_sample_nodes) or (node2 not in self.all_sample_nodes):
                    continue

                if node1 > node2:
                    edge_id = (node2, node1)
                else:
                    edge_id = (node1, node2)

                self.edge_labels[edge_id] = 1
                if node1 not in edge_labels_nodes:
                    edge_labels_nodes.add(node1)
                if node2 not in edge_labels_nodes:
                    edge_labels_nodes.add(node2)
                network_edge_count += 1

        print("Done. (time={:.3f} s), saved {} edges to community graph".format(default_timer() - start_time, network_edge_count))

        # load/generate graph into memory for algorithm to use later
        print("##### Generate interest graph with interest_graph_index and graph_rindex")
        start_time = default_timer()

        # tracks edges already calculated in the filter-set of reverse index so as not to avoid duplicates
        edges_processed = set()
        self.graph.clear()
        saved_count = 0

        print("No. of nodes in graph ridx: {}".format(len(all_interest_nodes)))
        nodes_found_in_ridx= set()
        # iterate over possible edges
        if GraphDataStager.DATA_NAMES[self.data_name]["data_alpha"] > 0:
            for interest, nodes in graph_rindex.items():
                for node_a, node_b in itertools.combinations(nodes, 2):
                    if node_a not in nodes_found_in_ridx:
                        nodes_found_in_ridx.add(node_a)
                    if node_b not in nodes_found_in_ridx:
                        nodes_found_in_ridx.add(node_b)

                    # create sorted edge id to make sure (a, b) and (b, a) are deduped
                    if node_a > node_b:
                        edge_id = (node_b, node_a)
                    else:
                        edge_id = (node_a, node_b)

                    if edge_id in edges_processed:
                        continue
                    edges_processed.add(edge_id)
                    interests_a = interest_graph_index[node_a]
                    interests_b = interest_graph_index[node_b]
                    numerator = len(interests_a & interests_b)

                    # if no. of shared interests is not >= MIN_TERMS_NEEDED this jaccard is going to be too small
                    # skip denominator calc
                    if numerator < MIN_INTERESTS_NEEDED:
                        continue
                    edge_jaccard = numerator / (len(interests_a | interests_b) +
                                                GraphDataStager.DATA_NAMES[self.data_name]["k_regularization"])
                    if edge_jaccard < self.sim_threshold:
                        continue

                    self.graph[edge_id] = edge_jaccard
                    # graph_nodes is a subset of all nodes in the graph.
                    # Nodes not having a high enough jaccard with any other
                    #     node are going to be missing but they are present in
                    #     self.all_sample_nodes
                    self.graph_nodes.add(node_a)
                    self.graph_nodes.add(node_b)

                    num_current_graph_nodes = len(self.graph_nodes)
                    if saved_count % 100000 == 0:
                        # Won't run on 0 because there will always be at least
                        #     2 nodes.

                        # edge_density is equal to ratio between the edges and
                        #     total amount of edges possible from the current
                        #     graph nodes.
                        edge_density = saved_count / (num_current_graph_nodes * (num_current_graph_nodes - 1) // 2)

                        # Number of edges expected by multiplying total amount
                        #     of edges possible from self.num_points_sample
                        # Uses len(self.all_sample_nodes) instead of
                        #     self.num_sample because pruning removes almost
                        #     40% of self.num_sample
                        expected_number_of_edges = comb(len(all_interest_nodes), 2) * edge_density

                        if expected_number_of_edges > self.max_edges * 1.25:
                            raise GraphDataStagerException(
                                "Edges expected significantly higher than "
                                "max_edges passed. Stopping program. "
                                "Expected_number of edges {}, max edges "
                                "allowed {}, edge_density: {}"
                                .format(expected_number_of_edges, self.max_edges, edge_density)
                            )

                    saved_count += 1

                    # Modulo progress print
                    if saved_count % 50000 == 0:
                        print("  Saved {} edges in {:.2f} seconds..."
                              .format(saved_count, default_timer() - start_time))
                        print("  Expected number of edges right now is {}"
                              .format(expected_number_of_edges))
                        print("Found {} nodes in ridx so far, can have: {}"
                              .format(len(nodes_found_in_ridx), len(all_interest_nodes)))
        else:
            print("Skipping data jaccard graph computation as data_alpha weight is 0!")
        print("Done. (time={:.3f} s), Produced {} edges for interests graph in memory"
              .format(default_timer() - start_time, saved_count))

        # inject a fraction of the labels into graph
        print("#################### Injecting labels into graph with fraction of: {}"
              .format(GraphDataStager.DATA_NAMES[self.data_name]["label_inject_fraction"]))

        sparse_injected_labels_jaccard_sum = 0  # combined jaccard of all injected labels that are also in the data graph
        all_injected_edges_count = 0  # total number of injected labels
        sparse_injected_edges_count = 0  # number of injected labels that are also in the data graph
        label_similarities_file_path = os.path.join(self.output_data_dir, "label_similarities.tsv")

        combined_graph_edges = set(self.edge_labels.keys())
        combined_graph_edges.update(self.graph.keys())
        num_combined_edges = len(combined_graph_edges)
        num_edges_saved = 0
        num_edges_processed = 0
        ticker_size = num_combined_edges // 10
        nodes_interesected_graph = set()

        with open(label_similarities_file_path, "w") as label_similarities_file:

            for edge_id in combined_graph_edges:
                num_edges_processed += 1

                if (num_edges_saved > 10) and (num_edges_processed % ticker_size == 0):
                    fraction_edges_saved = num_edges_saved / num_edges_processed
                    expected_num_edges = int(fraction_edges_saved * num_combined_edges)
                    num_nodes = len(self.graph_nodes)
                    edge_density_saved = num_edges_saved / (num_nodes * (num_nodes - 1) // 2)
                    expected_dense_edges = expected_num_edges / edge_density_saved
                    # general quadratic solution for number of nodes given number of edges in a dense graph:
                    # num nodes = (1 + sqrt(1 + 8 * all_edges)) / 2
                    expected_num_nodes = int((1 + (1 + 8 * expected_dense_edges)**0.5) / 2)

                    print("Expected final size of graph: nodes: {}, edges:{}, if this is not what "
                          "you want stop and restart!".format(expected_num_nodes, expected_num_edges))

                if (self.random.random() <= GraphDataStager.DATA_NAMES[self.data_name]["label_inject_fraction"]) and \
                        (edge_id in self.edge_labels):  # TODO: don't think this second condition needs to be here
                    sample_label = True
                    sample_edge_val = self.edge_labels[edge_id]
                else:
                    sample_label = False
                    sample_edge_val = 0.0

                node1, node2 = edge_id  # edges already sorted


                if node1 not in nodes_interesected_graph:
                    nodes_interesected_graph.add(node1)
                if node2 not in nodes_interesected_graph:
                    nodes_interesected_graph.add(node2)

                # We want to skip processing this if it was neither in graph nor in sample label.
                if (edge_id not in self.graph) and (not sample_label):
                    continue

                # compute jaccard if its missing in the graph
                # this could still be in the labels, but we only have to compute jaccard if it is not in the graph
                if edge_id not in self.graph:
                    # it has to be in the label graph if its not in the data graph
                    interests_a = interest_graph_index[node1]
                    interests_b = interest_graph_index[node2]
                    # edge_jaccard is guaranteed to be computable including
                    #     when it is 0 because all nodes in labels are also in
                    #     the data graph because of prefiltering.
                    edge_jaccard = (len(interests_a & interests_b)
                                    / (len(interests_a | interests_b) + GraphDataStager.DATA_NAMES[self.data_name]["k_regularization"]))
                    # add 1.0 to the jaccard value in the graph if its in the graph
                else:
                    # it has to be in the original graph if its not in the edge_label graph
                    edge_jaccard = self.graph[edge_id]
                if GraphDataStager.DATA_NAMES[self.data_name]["sum_edges"]:
                    # compute sum of weights
                    updated_edge_jaccard = edge_jaccard + sample_edge_val
                else:
                    # when labels are 1/0 then alpha controls what fraction of contribution comes from data
                    # when alpha is 0, the output graph is purely based on the label graph
                    # when alpha is 1, the label is not used
                    updated_edge_jaccard = (edge_jaccard * GraphDataStager.DATA_NAMES[self.data_name]["data_alpha"]
                                            + sample_edge_val * (1 - GraphDataStager.DATA_NAMES[self.data_name]["data_alpha"]))

                if updated_edge_jaccard < self.sim_threshold:
                    if edge_id in self.graph:
                        del self.graph[edge_id]
                    continue

                num_edges_saved += 1

                if sample_label:
                    del self.edge_labels[edge_id]  # cannot have edge in self.graph and self.edge_labels
                    all_injected_edges_count += 1
                    if all_injected_edges_count % 1000 == 0:
                        print("Injected {} edges...".format(all_injected_edges_count))
                    if edge_id not in self.graph:
                        # only injected labels that are in the graph are added to the label_similarities_file
                        label_similarities_file.write("{}\t{}\t{}\n".format(node1, node2, edge_jaccard))
                        sparse_injected_labels_jaccard_sum += edge_jaccard
                        sparse_injected_edges_count += 1
                        # We don't need to update the interest_graph_index and
                        #     graph_rindex even though it would be invalid for
                        #     the new nodes being added here. Most of the nodes
                        #     will already be there.
                        if node1 not in self.graph_nodes:
                            self.graph_nodes.add(node1)
                        if node2 not in self.graph_nodes:
                            self.graph_nodes.add(node2)
                self.graph[edge_id] = updated_edge_jaccard
                    
        print("Total number of nodes in the graph after label injection: {}".format(len(self.graph_nodes)))
        if sparse_injected_edges_count == 0:
            print("No injected edges found in graph")
        else:
            print("Sparse average label jaccard values: {}"
                  .format(sparse_injected_labels_jaccard_sum / sparse_injected_edges_count))
        if all_injected_edges_count == 0:
            print("No edges were injected into graph")
        else:
            print("Full average label jaccard values: {}"
                  .format(sparse_injected_labels_jaccard_sum / all_injected_edges_count))

        self.remove_disconnected_nodes()
        # Add cannot_link labels to edge_lables

        print("Found {} total no. of nodes and {} edges in intersected graph".format(len(nodes_interesected_graph), len(combined_graph_edges)))

        # this is not used any more! our measurement infers negative edges
        # cannot_link_labels = GraphDataStager.generate_communities_cannot_link_labels(
        #     labels_nodes=edge_labels_nodes,
        #     must_link_labels=self.edge_labels,
        #     graph=self.graph,
        #     seed=for the millionth time pass the damn seed here!> to make your experiments predictable
        # )
        # self.edge_labels.update(cannot_link_labels)

        # now save the labels and graph
        self.save_graph()
        self.save_edge_labels()

    def _generate_graph_and_labels_socialbot(self):

        if self.num_points_sample is not None:
            raise GraphDataStagerException("socialbot dataset does not support node sampling in GDA")

        tmp_graph = list()
        tmp_node_id_mapping = dict()  # dict: str node ID -> int node ID
        tmp_graph_nodes = set()

        id_gen = itertools.count()

        start_time = default_timer()
        print("loading graph from file...", end="", flush=True)

        with open(os.path.join(self.input_data_dir, "post_graph.jsonl")) as f:
            for line in f:
                line_dict = json.loads(line)
                str_node_id_1 = line_dict["id1"]
                str_node_id_2 = line_dict["id2"]
                weight = line_dict["sim"]

                if str_node_id_1 in tmp_node_id_mapping:
                    node_id_1 = tmp_node_id_mapping[str_node_id_1]
                else:
                    node_id_1 = next(id_gen)
                    tmp_node_id_mapping[str_node_id_1] = node_id_1
                if str_node_id_2 in tmp_node_id_mapping:
                    node_id_2 = tmp_node_id_mapping[str_node_id_2]
                else:
                    node_id_2 = next(id_gen)
                    tmp_node_id_mapping[str_node_id_2] = node_id_2

                if weight >= self.sim_threshold:
                    if node_id_1 not in tmp_graph_nodes:
                        tmp_graph_nodes.add(node_id_1)
                    if node_id_2 not in tmp_graph_nodes:
                        tmp_graph_nodes.add(node_id_2)
                    tmp_graph.append((node_id_1, node_id_2, weight))

        print(" done. (time={:.2f} s)".format(default_timer() - start_time))

        start_time = default_timer()
        print("reorganizing graph in memory...", end="", flush=True)
        # needs to be done so that node IDs are contiguous 0-indexed

        reverse_tmp_node_id_mapping = reverse_dict(tmp_node_id_mapping)
        tmp_to_node_id_mapping = dict()
        self.node_id_mapping = dict()
        for new_node_id, tmp_node_id in enumerate(tmp_graph_nodes):
            tmp_to_node_id_mapping[tmp_node_id] = new_node_id
            self.node_id_mapping[reverse_tmp_node_id_mapping[tmp_node_id]] = new_node_id
        del tmp_node_id_mapping
        del reverse_tmp_node_id_mapping

        self.graph.clear()
        while tmp_graph:
            tmp_node_id_1, tmp_node_id_2, weight = tmp_graph.pop()
            self.graph[tmp_to_node_id_mapping[tmp_node_id_1], tmp_to_node_id_mapping[tmp_node_id_2]] = weight
        del tmp_graph

        self.graph_nodes.clear()
        for tmp_node_id in tmp_graph_nodes:
            self.graph_nodes.add(tmp_to_node_id_mapping[tmp_node_id])
        del tmp_graph_nodes
        del tmp_to_node_id_mapping

        print(" done. (time={:.2f} s)".format(default_timer() - start_time))

        print("saving graph to file...")
        self.save_graph()

        # socialbot has human labels; shouldn't be output by stager
        # self.save_edge_labels()

    @property
    def node_based_graph(self):
        """
        Getter for self.node_based_graph.

        This system is good because some algorithms don't need
        self.node_based_graph at all, so this way the node-based graph is only
        computed if it is needed, AND only computed once.

        :return: node based graph
        :rtype: dict
        """
        if self._node_based_graph is None:

            # defaultdict makes the code much cleaner
            node_based_graph = defaultdict(dict)
            for (id1, id2), weight in self.graph.items():
                node_based_graph[id1][id2] = weight
                node_based_graph[id2][id1] = weight

            # conversion to dict avoids new keys being added by attempted key access, and is O(N)
            self._node_based_graph = dict(node_based_graph)

        return self._node_based_graph

    def _generate_0indexed_sequential_id_mapping(self):
        """
        Generate a mapping and reverse mapping for the graph nodes, where the
        new IDs are 0-indexed and sequential.
        GDA node IDs are the ones used in self.graph_nodes and self.graph and
        self.node_based_graph.
        :return: ID mapping (GDA node ID -> new node ID)
                 reverse ID mapping (new node ID -> GDA node ID)
        :rtype: (dict[int, int], dict[int, int])
        """
        id_mapping = dict()  # dict: new node ID -> GDA node ID
        reverse_id_mapping = dict()  # dict: GDA node ID -> new node ID
        for new_node_id, gda_node_id in enumerate(sorted(self.graph_nodes)):
            id_mapping[gda_node_id] = new_node_id
            reverse_id_mapping[new_node_id] = gda_node_id
        return id_mapping, reverse_id_mapping

    @staticmethod
    def _write_mapping(id_mapping, filename):
        """
        Write an ID mapping to a file.
        :param id_mapping: dict: old node ID -> new node ID
        :type id_mapping: dict[int, int]
        :param filename:
        :type filename: str
        """
        with open(filename, "w") as f:
            for old_node_id, new_node_id in id_mapping.items():
                f.write("{}\t{}\n".format(old_node_id, new_node_id))

    @staticmethod
    def check_algorithms(algorithms):
        """
        Checks if algos are valid, and if not, raises exception.
        :param algorithms:
        :type algorithms: collections.Iterable[str]
        """
        for algorithm in algorithms:
            if algorithm not in ALGO_NAMES:
                raise GraphDataStagerException(
                    "Valid algorithm names are: {}. Algorithm found {} is not a supported!".format(ALGO_NAMES, algorithm)
                )

    def generate_algorithm_graph(self, algorithm):
        """
        :param algorithm:
        :type algorithm: str
        """
        if len(self.graph) == 0:
            raise GraphDataStagerException("graph cannot be empty when calling generate_algorithm_graph")
        algorithm_dir = os.path.join(self.output_data_dir, algorithm)

        if algorithm == "autohds-g":

            if self.node_id_mapping is None:
                # simulates a dictionary
                # reverse_id_mapping[1234] == "1234"
                reverse_id_mapping = IntToStrDict()
            else:
                reverse_id_mapping = reverse_dict(self.node_id_mapping)  # int ID -> string ID

            # autohds-g is the reference algorithm being measured and needs to be run through genediver so it is staged
            # in the top level output dir
            if GraphDataStager.DATA_NAMES[self.data_name]["save_autoHDS-G_native_format"]:
                with open(os.path.join(self.output_data_dir, "graph.jsonl"), "w") as algorithm_graph_file:
                    for node in self.node_based_graph:
                        algorithm_graph_file.write(json.dumps({
                            "id": node,
                            "connections": tuple(self.node_based_graph[node].items())
                        }) + "\n")

                if self.node_id_mapping is not None:
                    self._write_mapping(reverse_id_mapping, os.path.join(self.output_data_dir, "graph.mapping.tsv"))

            else:

                with open(os.path.join(self.output_data_dir, "prestaging_graph.jsonl"), "w") as algorithm_graph_file:
                    for (id1, id2), sim in self.graph.items():
                        algorithm_graph_file.write(json.dumps({
                            "id1": reverse_id_mapping[id1],
                            "id2": reverse_id_mapping[id2],
                            "sim": sim
                        }) + "\n")

            open(os.path.join(self.output_data_dir, "experiment_params.txt"), "a").close()  # touch

        else:
            # create algorithm directory
            if not os.path.exists(algorithm_dir):
                os.makedirs(algorithm_dir)

            writer = ALGORITHMS[algorithm](algorithm_dir)
            # we need an ID mapping to make sure the node IDs are contiguous
            id_mapping, _ = self._generate_0indexed_sequential_id_mapping()

            # self.graph is (node1,node2): weight, but write graph takes the connection format of:
            # [{"id":1, "connections":[(node2, weight)]}]
            # todo: only used here, so doesn't need to be a self variable right?
            connections_graph = dict()
            for (node_id_1, node_id_2), weight in self.graph.items():
                node_id_1 = id_mapping[node_id_1]
                node_id_2 = id_mapping[node_id_2]
                if node_id_1 not in connections_graph:
                    connections_graph[node_id_1] = list()
                if node_id_2 not in connections_graph:
                    connections_graph[node_id_2] = list()
                connections_graph[node_id_1].append((node_id_2, weight))
                connections_graph[node_id_2].append((node_id_1, weight))

            connections_list = list()
            for node_id_1, connections in connections_graph.items():
                node_information = {
                    "id": node_id_1,
                    "connections": connections
                }
                connections_list.append(node_information)
            writer.write_graph(
                graph=connections_list,
                num_nodes=len(self.graph_nodes),
                num_edges=len(self.graph)
            )

            # write node ID mapping to file in algo staging dir
            self._write_mapping(
                id_mapping,
                os.path.join(algorithm_dir, "id_mapping.tsv")
            )

    def save_mapping(self):
        """
        Write a TSV file out to the data set directory containing the node ID
        mapping ("old_id\tnew_id").
        If the nodes were not mapped, the file will not be saved.
        :return: whether the mapping was saved
        :rtype: bool
        """
        nodes = self.graph_nodes.copy()
        if self.edge_labels:
            for node_id_1, node_id_2 in self.edge_labels:
                if node_id_1 not in nodes:
                    nodes.add(node_id_1)
                if node_id_2 not in nodes:
                    nodes.add(node_id_2)
        with open(os.path.join(self.output_data_dir, "nodes"), "w") as f:
            f.write("\n".join(map(str, nodes)))
        del nodes

        if self.node_id_mapping is None:
            return False
        self._write_mapping(
            self.node_id_mapping,
            os.path.join(self.output_data_dir, "gda_id_mapping.tsv")
        )
        return True

    def print_metrics(self):
        """
        prints metrics
        """
        print("Graph Data Stager metrics: " + json.dumps({
            "num_nodes": len(self.graph_nodes),
            "num_label_edges": len(self.edge_labels),
            "num_partitional_labels": len(self.partitional_labels),
            "num_graph_edges": len(self.graph)
        }, indent=4))

    @staticmethod
    def generate_communities_cannot_link_labels(labels_nodes, must_link_labels, graph, seed):
        """
        generates cannot link labels given must link labels
        :param labels_nodes:
        :param must_link_labels:
        :param graph:
        :param seed:
        :return:
        """
        # Generate cannot_link labels by finding edge_ids with nodes in
        #     edge_labels_nodes that do not meet the jaccard specifications
        print("##### Generating cannot link labels")
        num_must_link_labels = len(must_link_labels)

        # TODO: this needs to be in the CLI
        negative_edge_multiples = 2.0
        random = Random(seed)

        max_iterations = comb(len(labels_nodes), 2)
        matrix_density = num_must_link_labels / max_iterations
        # we want more negative than positive edges
        target_num_cannot_link_labels = int(negative_edge_multiples * num_must_link_labels)
        # we need to process a little bit extra to get target_num_cannot_link_labels negative edges
        negative_edge_try_count = 1.0 / (1 - matrix_density) * target_num_cannot_link_labels
        # we will produce 2 sets of vertices from original label_nodes using sampling with replacement
        # and then we will zip them together to get the edges
        node_a_sample = list()
        node_b_sample = list()
        # we do this in chunks to make the program run faster even though theoretically this isn't a correct sample
        chunk_size = round(negative_edge_try_count / 1000)
        if chunk_size < 1:
            chunk_size = 1
        num_iterations = int(negative_edge_try_count / chunk_size)
        ticker_size = int(num_iterations / 20)
        for i in range(num_iterations):
            node_a_chunk = random.sample(labels_nodes, chunk_size)
            node_a_sample.extend(node_a_chunk)
            node_b_chunk = random.sample(labels_nodes, chunk_size)
            node_b_sample.extend(node_b_chunk)
            if i % ticker_size == 0:
                print("Sampled {} chunks...".format(i))

        num_cannot_link_labels = 0
        cannot_link_labels = dict()
        ticker_size = int(negative_edge_try_count / 20)
        i = 0
        for node_a, node_b in zip(node_a_sample, node_b_sample):
            # create sorted edge id since self.graph and self.edge_labels both have sorted edge_ids
            if node_a > node_b:
                edge_id = (node_b, node_a)
            else:
                edge_id = (node_a, node_b)
            # cannot link labels can't be must-link labels or edges in the graph
            # random.sample will produce duplicates so don't add if its already been added
            if (edge_id in graph) or (edge_id in must_link_labels) or (edge_id in cannot_link_labels):
                continue

            cannot_link_labels[edge_id] = 0
            num_cannot_link_labels += 1
            if num_cannot_link_labels % ticker_size == 0:
                print("Generated {} cannot link labels...".format(num_cannot_link_labels))

            i += 1
        return cannot_link_labels

    def save_data_params(self):
        """
        adds the experiment_params.txt
        :return:
        """
        params = {"sim": self.sim_threshold, "num_points": self.num_points_sample}
        params.update(self.DATA_NAMES[self.data_name])

        with open(os.path.join(self.output_data_dir, "params.json"), "w") as f:
            f.write(json.dumps(params))
