#!/usr/bin/env python3
import json, os, re

from graphHDS.GraphHDSV2 import GraphHDSException


class AutoHDSGraphConverter:
    """
    general converter that converts transaction level tsv
    (node1\tnode2\similarity_value) to format used by hds-g
    """
    # used to detemplate urls
    URL_PT_ID = "{PT_ID}"

    def __init__(self, input_graph_path, node_weight_path, output_dir, experiment_name, url_template=None):
        """
        :param input_graph_path:
        :param node_weight_path:
        :param output_dir:
        :param experiment_name: unique name of this graph generation variant,
                                useful for measurements name-spacing
        :param url_template if None augmentation is not performed on id mapping file
        """

        if node_weight_path is not None and not os.path.isfile(node_weight_path):
            raise GraphHDSException("Node weight path is not a valid file: {}".format(node_weight_path))

        if not os.path.isfile(input_graph_path):
            raise GraphHDSException("Input graph path is not a valid file: {}".format(input_graph_path))

        if not os.path.isdir(output_dir):
            raise GraphHDSException("Output directory path does not exist: {}".format(output_dir))

        self._input_graph_path = input_graph_path
        self._node_weight_path = node_weight_path
        self._url_template = url_template

        # Generate output file names
        output_graph_name = "{}.jsonl".format(experiment_name)
        output_map_name = "{}.mapping.tsv".format(experiment_name)

        self._output_graph_path = os.path.join(output_dir, output_graph_name)
        self._output_map_path = os.path.join(output_dir, output_map_name)

        # Dictionary of integer-strings as keys with a list of lists as values
        self.hdsg_dict = dict()
        # Dictionary of post IDs as keys with unique integers as values
        self.map_dict = dict()

        self.node_weights = dict()
        self.min_raw_weight = None

        if self._node_weight_path is not None:
            # set node weights
            line_number = 0

            print("Reading node weights from: {}".format(self._node_weight_path))
            with open(self._node_weight_path, "rb") as nw:
                for line_b in nw:
                    line = line_b.decode("utf-8", errors="ignore")
                    line = re.sub(r'[^\x00-\x7F]+', ' ', line)
                    line_number += 1
                    cols = line.split("\t")
                    if len(cols) != 2:
                        raise GraphHDSException("Needed two columns, found {} not a valid node weight row in "
                                            "node weight file {} at line: {}".format(len(cols),
                                                                                     self._node_weight_path, line_number))
                    node_id, node_weight_str = cols
                    node_weight = float(node_weight_str)
                    if self.min_raw_weight is None or (node_weight < self.min_raw_weight):
                        self.min_raw_weight = node_weight
                    self.node_weights[node_id] = node_weight

    def load_generated_graph(self, sim_threshold):
        """
        :param sim_threshold:
        """

        unique_nodes = 0

        line_number = 0
        print("Reading graph from {}".format(self._input_graph_path))
        with open(self._input_graph_path, "r") as i:
            try:
                for edge_line in i:
                    edge_line = re.sub(r'[^\x00-\x7F]+', ' ', edge_line)
                    # do not check in, only for debugging
                    #if unique_nodes > 400:
                    #    break
                    line_number += 1
                    edge = json.loads(edge_line)
                    if line_number % 100000 == 0:
                        print("Read {} lines...".format(line_number))
                    try:
                        node1 = edge["id1"].encode("ascii", "ignore")
                        node2 = edge["id2"].encode("ascii", "ignore")
                        sim = edge["sim"]

                    except KeyError:
                        raise GraphHDSException("One or more of required edge keys not found: id1, id2, sim "
                                                "in line: {} at line no. {}".format(edge_line, line_number))

                    # Exclude undesired edges
                    if sim < sim_threshold:
                        continue

                    # Add missing entries to mapping dictionary
                    if node1 not in self.map_dict:
                        unique_nodes += 1
                        self.map_dict[node1] = unique_nodes - 1
                    if node2 not in self.map_dict:
                        unique_nodes += 1
                        self.map_dict[node2] = unique_nodes - 1

                    # Get integer mappings from mapping dictionary
                    node1_map_int_string = self.map_dict[node1]
                    node2_map_int_string = self.map_dict[node2]

                    # Add entries to output graph dictionary
                    if node1_map_int_string not in self.hdsg_dict:
                        self.hdsg_dict[node1_map_int_string] = [[node2_map_int_string, sim]]
                    else:
                        self.hdsg_dict[node1_map_int_string].append([node2_map_int_string, sim])

                    if node2_map_int_string not in self.hdsg_dict:
                        self.hdsg_dict[node2_map_int_string] = [[node1_map_int_string, sim]]
                    else:
                        self.hdsg_dict[node2_map_int_string].append([node1_map_int_string, sim])
            # todo handle encoding errors
            except UnicodeDecodeError as e:
                print("Skipping line could not handle encode")
        print("Found {} unique nodes from {} lines with sim threshold of {}\n".format(unique_nodes, line_number,
                                                                                      sim_threshold))

    def save_hds_g_compatible_graph(self):
        # Write out line JSON graph
        print("Writing graph to {}".format(self._output_graph_path))
        line_count = 0
        try:
            with open(self._output_graph_path, "w") as gf:
                for point in self.hdsg_dict:
                    point_connections_dict = {"id": point, "connections": self.hdsg_dict[point]}
                    point_connections_line_str = json.dumps(point_connections_dict, sort_keys=True)
                    gf.write("{}\n".format(point_connections_line_str))
                    line_count += 1
            print("{} line JSONs saved\n".format(line_count))
        except IOError as e:
            raise GraphHDSException("HDS-G compatible graph failed to write out. Error: {}".format(e))

    def save_hds_g_compatible_mapping_file(self):
        # Write out mapping file
        print("Writing mapping file to {}".format(self._output_map_path))
        line_count = 0
        try:
            with open(self._output_map_path, "w") as m:
                for point_id, unique_int in self.map_dict.items():
                    d_point_id = point_id.decode("UTF-8")
                    # save point original id, mapped id, point raw weight
                    if len(self.node_weights) == 0:
                        raw_weight = 1.0
                    else:
                        if d_point_id in self.node_weights:
                            raw_weight = self.node_weights[d_point_id]
                        else:
                            print("Warning missing node weight assigning default min weight of {}".format(self.min_raw_weight))
                            raw_weight = self.min_raw_weight
                    if self._url_template is not None:
                        # insert url template format and then replace it
                        d_point_id = ":".join([d_point_id, self._url_template.replace(self.URL_PT_ID, d_point_id)])

                    m.write(u"{}\t{}\t{}\n".format(unique_int, d_point_id, raw_weight))
                    line_count += 1
            print("{} mappings saved\n".format(line_count))
        except IOError as e:
            raise GraphHDSException("HDS-G compatible mapping file failed to write out. Error: {}".format(e))
