#!/usr/bin/env python3


def read_hmetis_output(filepath):
    """
    Read the clustering output of hMETIS.
    :param filepath: e.g. graph.part.49
    :type filepath: str
    :return: iterator over (node ID, cluster ID)
    :rtype: collections.Iterator[(int, int)]
    """
    with open(filepath) as f:
        for node_id, line in enumerate(f, 1):
            yield node_id, int(line)
