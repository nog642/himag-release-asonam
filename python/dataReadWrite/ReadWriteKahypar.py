#!/usr/bin/env python3
from dataReadWrite.ReadWriteHmetisFormat import ReadWriteHmetisFormat


class ReadWriteKahypar(ReadWriteHmetisFormat):

    ALGORITHM_DISPLAY_NAME = "KaHyPar"
    FILENAME_REGEX = r"graph\.part[0-9]+\.epsilon[0-9\.]+\.seed\-[0-9]+\.KaHyPar"
    WEIGHTED = False

    def __init__(self, algo_staging_dir):
        super().__init__(algo_staging_dir)
