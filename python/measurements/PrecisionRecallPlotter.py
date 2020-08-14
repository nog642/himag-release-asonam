#!/usr/bin/env python3
import sys

from adjustText import adjust_text

try:
    import matplotlib.pyplot as plt
except ImportError as e:
    # Matplotlib requires Tkinter
    print("Unable to import matplotlib. Error: {}".format(e))
    print("Run the following command in your Terminal:")
    print("\tsudo apt install python3-tk")
    print("See: https://stackoverflow.com/a/36327323")
    sys.exit(1)


class PrecisionRecallPlotter:

    def __init__(self):
        # Prepare plot
        plt.xlabel("recall")
        plt.ylabel("precision")
        plt.xlim(0, 1)
        plt.ylim(0, 1)

        self._plot_legend = list()
        self._texts = list()
        self._point_markers = ["x", "o", "s", "*", "^", "p", "+", "D"]

    def plot_line(self, line_label, recalls_dict, precisions_dict):

        # Add an entry to the legend
        self._plot_legend.append(line_label)

        # Plot a line
        plt.plot(recalls_dict.values(), precisions_dict.values(), marker=self._point_markers[0])

        # Remove the used marker from the list of available markers
        self._point_markers.remove(self._point_markers[0])

        # Generate the label text annotations
        for xy in zip(recalls_dict.values(), precisions_dict.values()):
            rounded_xy = tuple([round(k, 3) if isinstance(k, float) else k for k in xy])
            self._texts.extend([plt.text(xy[0], xy[1], "(%s, %s)" % rounded_xy,
                                         ha="center", va="center", fontsize="x-small")])

    def display_plot(self):
        # Prevent text labels from colliding
        #   https://github.com/Phlya/adjustText/wiki
        adjust_text(self._texts)  # , arrowprops=dict(arrowstyle="-")

        # Add the legend to the plot
        plt.legend(self._plot_legend)

        # Light grey grid
        plt.grid(color="#d3d3d3")

        # display the plot
        plt.show()
