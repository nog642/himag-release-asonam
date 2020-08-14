#!/usr/bin/env python3
import os

from dataReadWrite.ReadWriteHmetis import ReadWriteHmetis


class ReadWriteWhmetis(ReadWriteHmetis):

    ALGORITHM_DISPLAY_NAME = "hMETIS"
    FILENAME_REGEX = r"graph\.part\.[0-9]+"
    WEIGHTED = True

    def __init__(self, algo_staging_dir):
        super().__init__(algo_staging_dir)
