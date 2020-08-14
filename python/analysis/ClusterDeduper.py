#!/usr/bin/env python3
"""
Selects top k non-overlapping clusters by selecting either parent that is more
stable or the children IF the minimum stability is high.
"""
from collections import defaultdict
import itertools
import operator


class ClusterDeduper:
    """
    Finds child-parent relationships and removes children if parent is better
    than worse child, otherwise it removes parent.
    """

    def __init__(self, clustering, cluster_stabilities):
        """
        :param clustering: cluster_id -> set of points
        :type clustering: dict[int, set[collections.Hashable]]
        :param cluster_stabilities:
        :type cluster_stabilities: dict[int, numbers.Real]
        """
        self.clustering = clustering
        self.cluster_stabilities = cluster_stabilities

        self._descendant_cache = dict()

    def _get_descendant_relationship(self, cluster_id_1, cluster_id_2):
        """
         returns ancestor -> descendant in that sequence as tuple. If no relationship returns None
        :param cluster_id_1:
        :type cluster_id_1: collections.Hashable
        :param cluster_id_2:
        :type cluster_id_2: collections.Hashable
        :return: parent, descendant if relationship exists, else None
        :rtype: (collections.Hashable, collections.Hashable) | None
        """

        cache_id = cluster_id_1, cluster_id_2
        if cache_id in self._descendant_cache:
            return self._descendant_cache[cache_id]

        cluster_intersection = self.clustering[cluster_id_1] & self.clustering[cluster_id_2]

        ret_val = None

        if len(cluster_intersection) > 0:
            if cluster_intersection == self.clustering[cluster_id_1]:
                ret_val = cluster_id_2, cluster_id_1
            elif cluster_intersection == self.clustering[cluster_id_2]:
                ret_val = cluster_id_1, cluster_id_2
            else:
                # this should never happen as the input is a hierarchy
                raise AssertionError(
                    "clusters {} and {} have non-empty intersection, but "
                    "one is not a subset of the other."
                )
        # no intersection found; no parent-descendant relationship
        self._descendant_cache[cache_id] = ret_val

        return ret_val

    def get_deduped_clusters(self, min_stability=0):
        """
        Warning: dict values of return dict refer to the same sets as
        self.cluster. If you mutate one, it mutates the other.
        :return: deduped_clusters: clustering with non-overlapping clusters.
                 excluded_clusters: set of cluster IDs removed by deduping.
        :rtype: (dict[int, set[collections.Hashable]], set[int])
        """

        # create ALL clusters descendants tree
        descendant_clusters = defaultdict(set)
        ancestor_clusters = defaultdict(set)
        cluster_ids = self.clustering.keys()

        print("Calculating descendants...")
        for cluster_id_1, cluster_id_2 in itertools.combinations(cluster_ids, 2):
            result = self._get_descendant_relationship(cluster_id_1, cluster_id_2)
            if result is not None:
                parent_id, descendant_id = result
                descendant_clusters[parent_id].add(descendant_id)
                ancestor_clusters[descendant_id].add(parent_id)

        excluded_clusters = set()
        clusters_selected = set()

        # all clusters that could have overlap
        most_stable_clusters = sorted(self.cluster_stabilities.items(), key=operator.itemgetter(1), reverse=True)

        for cluster_id, stability in most_stable_clusters:
            if stability < min_stability:
                print("Excluding cluster {} with stability < {}".format(cluster_id, min_stability))
                excluded_clusters.add(cluster_id)
            # find all relatives
            relatives = set()
            if cluster_id in descendant_clusters:
                relatives.update(descendant_clusters[cluster_id])
            if cluster_id in ancestor_clusters:
                relatives.update(ancestor_clusters[cluster_id])
            # if any relatives have been selected then you can't keep this one
            if relatives.intersection(clusters_selected):
                excluded_clusters.add(cluster_id)
            else:
                clusters_selected.add(cluster_id)

        return {cluster_id: self.clustering[cluster_id]
                for cluster_id in self.clustering
                if cluster_id not in excluded_clusters}, excluded_clusters
