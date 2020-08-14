#!/usr/bin/env python3
from abc import ABCMeta, abstractmethod
import os


class ReadWriteAbstract(metaclass=ABCMeta):

    @abstractmethod
    def __init__(self, algo_staging_dir):
        self._check_attribute("ALGORITHM_DISPLAY_NAME")
        self._check_attribute("FILENAME_REGEX")
        self._check_attribute("WEIGHTED")

        staging_dir = os.path.dirname(algo_staging_dir)
        if not os.path.isdir(staging_dir):
            raise ValueError("staging directory '{}' does not exist".format(staging_dir))
        self.algo_staging_dir = algo_staging_dir

        # this is the directory where the data for the algo is staged
        if not os.path.isdir(self.algo_staging_dir):
            print("Creating staging dir at {}".format(self.algo_staging_dir))
            os.makedirs(self.algo_staging_dir)

    def get_all_algos(self):
        pass

    @staticmethod
    def get_algorithm_object(algorithm_name):
        pass

    @staticmethod
    def algorithm_exists(algorithm_name):
        pass

    @staticmethod
    def _get_class_name(algorithm_name):
        pass

    def _check_attribute(self, attr_name):
        if not hasattr(self, attr_name):
            TypeError("You must define the {} attribute in subclasses of "
                      "ReadWriteAbstract".format(attr_name))

    @abstractmethod
    def write_graph(self, graph, num_nodes, num_edges, node_weights=None):
        """
        Takes graph with float weights and 0-indexed integer node IDs and
        writes it to the staging directory.
        :param graph:
        :type graph: collections.Iterable[dict[str, int | collections.Sequence[(int, float)]]]
        :param num_nodes: total number of nodes in the graph, NOT the same as
                          the number of nodes in the thresholded graph
        :type num_nodes: int
        :param num_edges: total number of edges in the graph
        :type num_edges: int
        :param node_weights: node id to node weight
        :type node_weights: dict[int, float]
        """
        raise NotImplementedError

    @abstractmethod
    def read_clustering(self):
        """
        Read the output of the algorithm.
        :return: dict: cluster ID -> set of node IDs
        :rtype: dict[int, set[int]]
        """
        raise NotImplementedError
