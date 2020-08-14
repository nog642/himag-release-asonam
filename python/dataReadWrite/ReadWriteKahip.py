#!/usr/bin/env python3
from dataReadWrite.ReadWriteMetisFormat import ReadWriteMetisFormat


class ReadWriteKahip(ReadWriteMetisFormat):

    ALGORITHM_DISPLAY_NAME = "KaHIP"
    FILENAME_REGEX = r"tmppartition[0-9]+"
    WEIGHTED = False

    def __init__(self, algo_staging_dir):
        super().__init__(algo_staging_dir)
