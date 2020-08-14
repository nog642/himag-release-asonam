#!/usr/bin/env python3
"""
General library for hds-g repo.
"""
from collections import defaultdict
import csv
from functools import partial
from random import Random
import sys
from timeit import default_timer
import warnings

from scipy.special import comb as _scipy_comb


__all__ = ("CallableClass", "comb", "filter_probability", "IdentityDict",
           "IntToStrDict", "missingdict", "PrettyDefaultdict",
           "PrettyMissingdict", "CSVReadingException", "read_csv",
           "reverse_dict", "reverse_index", "stopwatch", "warn")


class CallableClass(type):

    def __new__(mcs, name, bases, namespace):
        if "_call" not in namespace:
            raise Exception("CallableClass must define _call()")

        namespace["__call__"] = namespace["_call"]
        cls = super().__new__(mcs, name, bases, namespace)
        type.__init__(cls, name, bases, namespace)
        return cls()

    def __init__(cls, name, bases, namespace):
        pass


comb = partial(_scipy_comb, exact=True)


def filter_probability(iterable, probability, seed=None):
    """
    Filters an iterable, letting through items based on random chance.
    :param iterable: Iterable to filter.
    :type iterable: collections.Iterable
    :param probability: Probability of an item passing through (between 0 and
                        1).
    :type probability: numbers.Real
    :param seed: Seed for the RNG (optional). This RNG will be independent from
                 any other RNGs.
    :type seed: int | None
    :return: An iterator over the items that pass through.
    """

    random_generator = Random(seed)

    for item in iterable:
        if random_generator.random() < probability:
            yield item


class IdentityDict(dict):

    def __getitem__(self, item):
        return item


class IntToStrDict(dict):

    def __getitem__(self, item):
        return str(item)


class missingdict(defaultdict):
    """
    collections.defaultdict except missing values are not stored in memory.
    """

    def __missing__(self, key):
        return self.default_factory()


class PrettyDefaultdict(defaultdict):
    """
    collections.defaultdict except the repr is the same as a regular dict.
    """
    __repr__ = dict.__repr__


class PrettyMissingdict(missingdict):
    """
    missingdict except the repr is the same as a regular dict.
    """
    __repr__ = dict.__repr__


class CSVReadingException(Exception):
    """
    Exception type for custom CSV reading (read_csv).
    """


def read_csv(filepath, required_fieldnames=None):
    """
    For reading CSV files with headers.

    Wraps csv.DictReader. Adds the following:
    * Performs checks for the number of columns in each row.
    * Checks for required fieldnames in the header.
    * Contains the logic for opening the file.
    * Yields the row number along with the row.
    :param filepath: CSV filepath.
    :type filepath: str
    :param required_fieldnames: Fieldnames required to be in header.
    :type required_fieldnames: collections.Iterable
    :return: Yields (row number, row). Rows are dicts where key=colname.
    :rtype: collections.Iterator[(int, dict[str, str])]
    """
    with open(filepath) as f:

        # csv.reader handles quoting (where commas are in the cell text)
        # default delimiter and quotechar are correct
        csv_reader = csv.DictReader(f)

        fieldnames = set(csv_reader.fieldnames)
        for fieldname in required_fieldnames:
            if fieldname not in fieldnames:
                raise CSVReadingException(
                    "required fieldname {!r} not found in file {!r}"
                    .format(fieldname, filepath)
                )

        num_cols = len(fieldnames)
        del fieldnames

        for row_number, row in enumerate(csv_reader, 1):

            if len(row) != num_cols:
                raise CSVReadingException(
                    "wrong number of cols in row {} of file {!r}"
                    .format(row_number, filepath)
                )

            yield row_number, row


def reverse_dict(dict_in):
    """
    Takes a dict where the keys are A and the values are B, and converts it to
    a dict where the keys are B and the values are A.
    :param dict_in:
    :type dict_in: dict[collections.Hashable, collections.Hashable]
    :return:
    :rtype: dict[collections.Hashable, collections.Hashable]
    """
    return {v: k for k, v in dict_in.items()}


def reverse_index(dict_in):
    """
    Takes a dict where the keys are A and the values are lists/sets of B, and
    converts it to a dict where they keys are B and the values are A.
    :param dict_in:
    :type dict_in: dict[collections.Hashable, collections.Iterable[collections.Hashable]]
    :return:
    :rtype: dict[collections.Hashable, collections.Hashable]
    """
    ridx = {}
    for k, v in dict_in.items():
        for item in v:
            ridx[item] = k
    return ridx


def tiny_reverse_index(k, v):
    """
    weird helper needed for building a fake reverse index for one list for a fixed key special usecase
    :param dict_in:
    :return:
    """
    ridx = dict()
    for item in v:
        ridx[item] = k
    return ridx


def stopwatch(f, args, kwargs=None):
    if kwargs is None:
        kwargs = {}
    start = default_timer()
    retval = f(*args, **kwargs)
    return default_timer() - start, retval


def _show_warning(message, category, filename, lineno, file=sys.stderr, line=None):
    """
    Custom warning hook that doesn't write the line itself.
    :param message:
    :param category:
    :param filename:
    :param lineno:
    :param file:
    :param line:
    """
    if file is None:
        # sys.stderr is None - warnings get lost
        return
    try:
        file.write(warnings.formatwarning(message, category, filename, lineno, ''))
    except (IOError, UnicodeError):
        pass  # the file (probably stderr) is invalid - this warning gets lost.

warnings.showwarning = _show_warning

warn = warnings.warn
