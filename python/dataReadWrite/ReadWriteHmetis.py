#!/usr/bin/env python3
from dataReadWrite.ReadWriteHmetisFormat import ReadWriteHmetisFormat


class ReadWriteHmetis(ReadWriteHmetisFormat):

    ALGORITHM_DISPLAY_NAME = "hMETIS"
    FILENAME_REGEX = r"graph\.part\.[0-9]+"
    WEIGHTED = False

    def __init__(self, algo_staging_dir):
        super().__init__(algo_staging_dir)
