#!/usr/bin/env python3
from dataReadWrite.ReadWriteHmetis import ReadWriteHmetis
from dataReadWrite.ReadWriteKahip import ReadWriteKahip
from dataReadWrite.ReadWriteKahypar import ReadWriteKahypar
from dataReadWrite.ReadWritePatoh import ReadWritePatoh
from dataReadWrite.ReadWriteWhmetis import ReadWriteWhmetis

ALGORITHMS = {
    "hmetis": ReadWriteHmetis,
    "whmetis": ReadWriteWhmetis,
    "kahypar": ReadWriteKahypar,
    "kahip": ReadWriteKahip,
    "patoh": ReadWritePatoh
}

ALGO_RUN_TEMPLATES = {

    "hmetis": "shmetis graph {num_clusters} 15",  # 15 is the unbalance factor

    "kahip": "kaffpa graph --k={num_clusters} --preconfiguration=strong",

    # "metis": "gpmetis graph {num_clusters}",

    # 0.01 is the imbalance factor
    # NOTE: For KaHyPar, all files under kahypar/config should be symlinked to
    #       your home directory (or just cut_rKaHyPar_dissertation.ini)
    "kahypar": "KaHyPar -h graph -k {num_clusters} -e 0.01 -o cut -m recursive -p ~/cut_rKaHyPar_dissertation.ini",

    "patoh": "patoh graph {num_clusters}"

}

assert all(algo in ALGORITHMS for algo in ALGO_RUN_TEMPLATES)
