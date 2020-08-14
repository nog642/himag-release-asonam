#!/usr/bin/env python3
from collections import deque
from datetime import datetime
import json
import os


class ExperimentLoggerException(Exception):
    pass


class LSAIExperimentLogger:

    def __init__(self, experiments_root_dir, description, use_last_version, experiment_name=None):
        """
        :param experiments_root_dir:
        :param description:
        :param use_last_version: if True it will use last version found else
                                 return the next version after last version
                                 found. This flag is only used if
                                 experiment_name is None
        :param experiment_name:
        """

        self.experiments_root_dir = os.path.expanduser(experiments_root_dir)

        # Create or increment output directory
        self.experiments_log_file = os.path.join(self.experiments_root_dir, "experiments_log.txt")
        self.experiment_params_file = os.path.join(self.experiments_root_dir, "experiment_params.txt")
        self.description = description

        if not os.path.isfile(self.experiment_params_file):
            raise ExperimentLoggerException("Could not find required experiment params "
                                            "file for logging: {}".format(self.experiment_params_file))

        # load consolidated experiment params from params file to be logged
        self.consolidated_params = dict()
        line_count = 0
        with open(self.experiment_params_file, "r") as epf:
            for line in epf:
                line_count += 1
                try:
                    step_params = json.loads(line)
                    for key, val in step_params.items():
                        self.consolidated_params[key] = val
                except ValueError:
                    raise ExperimentLoggerException("Could not parse experiment params file: "
                                                    "{}, line: {}".format(self.experiment_params_file, line_count))

        # experiment name is auto-generated (normal usage) to help with easy
        #     logging and tracking but a user can override with custom names
        if experiment_name is None:
            # experiment name is a versioned name of type yyyy-mm-dd, yyyy-mm-dd.1, yyyy-mm-dd.2 ...
            # first one that does not exist yet when searched in that order
            date_string = datetime.today().strftime("%Y-%m-%d")
            sub_version = 0
            suffix = ("" if sub_version == 0 else "_{}".format(sub_version))
            last_experiment_name = None
            self.experiment_name = date_string + suffix

            # check if a sub-dir with this name exists
            while LSAIExperimentLogger._path_with_prefix_exists(self.experiments_root_dir, self.experiment_name):
                sub_version += 1
                suffix = ("" if sub_version == 0 else ".{}".format(sub_version))
                last_experiment_name = self.experiment_name
                self.experiment_name = date_string + suffix

            # if requested to return last version set experiment to last version
            if use_last_version:
                if last_experiment_name is not None:
                    self.experiment_name = last_experiment_name
                else:
                    raise ExperimentLoggerException(
                        "This seems to be the first step for this version, you"
                        " cannot use previous version: code bug"
                    )
        else:
            self.experiment_name = experiment_name

        self.experiment_output_dir = os.path.join(self.experiments_root_dir, self.experiment_name)

    @staticmethod
    def _path_with_prefix_exists(root_dir_path, base_name):
        """
        checks to see if any path of type root_dir_path/base_name* exists
        :param root_dir_path:
        :param base_name:
        :return:
        """

        for file_or_dir_name in os.listdir(root_dir_path):
            if file_or_dir_name.startswith(base_name):
                return True

        return False

    def get_experiment_name(self):
        """
        use this method to access correct experiment name after object is initialized
        :return:
        """
        return self.experiment_name

    def update_log(self):
        """
        Updates the log for the current experiment run by pre-pending lines at the beginning of the existing
        log file. If not found creates a new log file. Log file at root_dir/experiment name
        :return: String of text for logging to a file
        """

        log_text = "------------------------------------------------------------------------------\n" \
                   "{}: {}\n".format(self.experiment_name, self.description)
        log_text += "------------------------------------------------------------------------------\n" \
                    "notes:\n\n" \
                    "parameters:\n"
        for key, val in self.consolidated_params.items():
            log_text += "  {}: {}\n".format(key, val)
        log_text += "\n"
        LSAIExperimentLogger._prepend_to_log(log_text, self.experiments_log_file)
        print(log_text)

    @staticmethod
    def _prepend_to_log(text, file_path):
        """
        Adds a line to the beginning of an existing log file or otherwise creates a new file

        TODO: check if experiment is already in the log to prevent duplicates

        :param text: The string of text to prepend to the log file
        """
        if os.path.isfile(file_path):
            try:
                with open(file_path, "r") as f:
                    lines = deque(f.readlines())
            except IOError as e:
                raise ExperimentLoggerException("Unable to read file {}. "
                                                "Error: {}".format(file_path, e))

            lines.appendleft(text)

            try:
                with open(file_path, "w") as f:
                    f.writelines(lines)
            except IOError as e:
                raise ExperimentLoggerException("Unable to write to file {}. "
                                                "Error: {}".format(file_path, e))
        else:
            try:
                with open(file_path, "w") as f:
                    f.write(text)
                print("Log file initialized at {}".format(file_path))
                print("\t{}".format(text))
            except IOError as e:
                raise ExperimentLoggerException("Unable to create new file {}. "
                                                "Error: {}".format(file_path, e))

    def show_experiment(self, name):
        """
        TODO
        Given an experiment name, parse the log file and display the experiment
        details in an easy to read, multi-line format. This can be called by a
        standalone CLI for quick analysis, and should be helpful when the
        experiment descriptions are long and there are more parameters embedded
        into the log line.
        :param name:
        """
        pass
