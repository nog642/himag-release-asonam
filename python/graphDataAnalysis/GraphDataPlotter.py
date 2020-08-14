#!/usr/bin/env python3
import json
import os

import matplotlib.pyplot as plt

from dataReadWrite.ReadWriteAll import ALGORITHMS
from graphDataAnalysis.GraphDataPlotterException import GraphDataPlotterException
from lib import warn

ALGO_NAMES = set(ALGORITHMS.keys()) | {"autohds-g"}  # set for nice repr


class GraphDataPlotter:

    # todo: this shouldn't be hacked here since we aren't using different line styles.
    LINESTYLES = ((0, ()), (0, ()), (0, ()), (0, ()), (0, ()), (0, ()), (0, ()), (0, ()), (0, ()), (0, ()), (0, ()),
                  (0, ()), (0, ()))
    COLORS = ("xkcd:blue", "xkcd:red", "xkcd:green", "xkcd:pink",
              "xkcd:orange", "xkcd:purple", "xkcd:yellow", "xkcd:black", "xkcd:lime green",
              "xkcd:gray", "xkcd:fuchsia", "xkcd:chocolate", "xkcd:cyan", "xkcd:olive", "xkcd:coral", "xkcd:tan",
              "xkcd:midnightblue")

    ALGO_DISPLAY_NAMES = {algorithm: ReadWriteAlgorithm.ALGORITHM_DISPLAY_NAME
                          for algorithm, ReadWriteAlgorithm in ALGORITHMS.items()}
    ALGO_DISPLAY_NAMES.update({  # non-DRW algorithms
        "metis": "METIS",
        "scikit": "scikit-learn Spectral Clustering",
        "autohds-g": "HIMAG",

        # TODO: temporary
        "hmetis.overclustered": "hMETIS-2k",
        "kahip.overclustered": "KaHIP-2k",
        "kahypar.overclustered": "KaHyPar-2k",
        "patoh.overclustered": "PaTOH-2k"

    })
    # you can add any algorithm to the dict above to override the default display name

    SIMILARITY_ALGO_DISPLAY_NAMES = {
        "edge-precision": "Edge Precision",
        "edge-ari": "Edge-ARI",
        "point-precision": "Point Precision"
    }

    # check to make sure all algorithms have display names
    if ALGO_NAMES:
        for algorithm in ALGO_NAMES:
            if algorithm not in ALGO_DISPLAY_NAMES:
                raise AssertionError("algorithm '{}' does not have a display name defined in GraphDataPlotter"
                                     .format(algorithm))
        del algorithm  # if we don't do this algorithm will become a permanent class attribute of GraphDataPlotter

    def __init__(self, data_set_dir, data_name, algorithms, experiment_name, k_ignore):

        # if data_name not in DATA_NAMES:
        #     raise GraphDataPlotterException("Data name not in valid Data set names! Allowed names: {}, got: '{}'"
        #                                     .format(set(DATA_NAMES.keys()), data_name))

        self.similarity_algorithm = None  # str: similarity algorithm used

        self.measurements_data = None  # list of (algorithm, shaving method, list of (fraction, ari))

        self.data_name = data_name

        self.algorithms = algorithms

        self.experiment_name = experiment_name

        self.k_ignore = k_ignore  # will not plot the first k_ignore points

        self.data_set_dir = data_set_dir

        if not os.path.isdir(self.data_set_dir):
            raise GraphDataPlotterException("Directory '{}' does not exist.".format(self.data_set_dir))

    def get_measurement_data(self):
        """
        Generates the measurement data
        """
        print("Reading measurement data...")
        self.measurements_data = list()
        for algorithm in self.algorithms:
            if algorithm == "autohds-g":
                algo_dirpath = os.path.join(self.data_set_dir, self.experiment_name)
            else:
                algo_dirpath = os.path.join(self.data_set_dir, algorithm)

            measurements_file_paths = [os.path.join(algo_dirpath, filename)
                                       for filename in os.listdir(algo_dirpath)
                                       if filename.startswith("measurements")]

            if not measurements_file_paths:
                warn("Skipping directory '{}' since it does not contain a 'measurements' file."
                     .format(algorithm), Warning)
                continue

            for measurements_file_path in measurements_file_paths:

                with open(measurements_file_path) as measurements_file:

                    # first line is different and tells the type of measurement
                    line = next(measurements_file)
                    measurement_params = json.loads(line)
                    try:
                        self.similarity_algorithm = measurement_params["measurement"]
                        if algorithm == "autohds-g":
                            shaving_method = None
                        else:
                            shaving_method = measurement_params["shaving_method"]
                    except KeyError as e:
                        raise GraphDataPlotterException(
                            "Invalid fist line in measurements file: {}".format(line)
                        ) from e

                    algorithm_data = list()
                    try:
                        for line in measurements_file:
                            measurement = json.loads(line)
                            algorithm_data.append((measurement["fraction"], measurement["similarity"]))
                    except (KeyError, json.decoder.JSONDecodeError) as e:
                        raise GraphDataPlotterException(
                            "Could not parse line in measurements file: {}".format(line)
                        ) from e

                self.measurements_data.append((algorithm, shaving_method, algorithm_data))
        print("Read measurement data!")

    def plot(self, title="Algorithm performance", markers=False, bottom_zero=False, show=False):
        """
        Plots measurement data in the form of list of
        ("hmetis", [(fraction, ari)])
        :param title: Title of the plot
        :type title: str
        :param bottom_zero: Force the bottom limit of the y-axis to be 0.
        :type bottom_zero: bool
        :param show:
        :type show: bool
        """
        print("Plotting data...")

        linstyles_iter = iter(GraphDataPlotter.LINESTYLES)
        colors_iter = iter(GraphDataPlotter.COLORS)

        plt.clf()

        algorithms = list()
        for algorithm, shaving_method, measurements in self.measurements_data:
            if shaving_method is None:
                algorithms.append(algorithm)
            else:
                algorithms.append("{}.{}".format(algorithm, shaving_method))

            try:
                linestyle = next(linstyles_iter)
                color = next(colors_iter)
            except StopIteration:
                raise GraphDataPlotterException("Not enough line styles and/or colors (need {})"
                                                .format(len(self.measurements_data))) from None

            x = list()
            y = list()
            for fraction, ari in measurements[self.k_ignore:]:
                x.append(fraction)
                y.append(ari)

            label = GraphDataPlotter.ALGO_DISPLAY_NAMES[algorithm]
            # autohds-g doesn't need the -flow added to it
            if shaving_method is not None:
                label += "-" + shaving_method

            # print("plotting:\n    x: {}\n    y: {}".format(x, y))
            if markers:
                plt.plot(
                    x,
                    y,
                    "o",
                    linestyle=linestyle,
                    label=label,
                    linewidth=2,
                    # markeredgewidth=0.5,
                    # markerfacecolor="none",
                    # markersize=0.5,
                    c=color
                )
            else:
                plt.plot(
                    x,
                    y,
                    linestyle=linestyle,
                    label=label,
                    linewidth=2,
                    # markeredgewidth=0.5,
                    # markerfacecolor="none",
                    # markersize=0.5,
                    c=color
                )

        plt.title(title)
        plt.xlabel("Fraction of points clustered")
        plt.ylabel(GraphDataPlotter.SIMILARITY_ALGO_DISPLAY_NAMES[self.similarity_algorithm])
        if bottom_zero:
            plt.ylim(bottom=0)
        plt.legend(loc="best")
        plt.tight_layout()

        fpath = os.path.join(self.data_set_dir, "{}__{}__{}__plot.png".format(
            self.data_name,
            ",".join(algorithms),
            self.similarity_algorithm
        ))
        plt.savefig(fpath)
        print("Saved plot to file '{}'!".format(fpath))

        if show:
            plt.show()
