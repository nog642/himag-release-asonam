#!/usr/bon/env python3
import json

CONFIG = {
    "power": 1,
    "graph_sim_threshold": 0.0,
    "stager_sim_threshold": 0.0,
    "data_name": "sim2_edge",  # sim2_edge or sim2_partitional
    "algos": ("autohds-g", "hmetis", "kahip", "kahypar", "patoh"),
    "autohdsg_flow": 400,
    "min_shave": 0.0,
    "seed": 50,
    "similarity_algo": "point-precision",
    "shave_type": "flow_shave"
}

TEMPLATE = """
RUNS
====


preprocessing
=============

(cd ~/hds-g/sim2; python ~/hds-g/sim2/preprocess.py --staging-dir ~/sim2)


{experiment_name_1} {experiment_name_2}
=======================================

mkdir ~/sim2/{experiment_name_1}

ln -rs ~/sim2/spatial.jsonl ~/sim2/{experiment_name_1}/spatial.jsonl

ln -rs ~/sim2/labels_background.clusters.jsonl ~/sim2/{experiment_name_1}/labels_background.clusters.jsonl

python ~/hds-g/graphHDS/spatial2graph.py --staging-dir ~/sim2/{experiment_name_1} \\
                                         --graph-data-name {experiment_name_1} \\
                                         --power {power} \\
                                         --sim-threshold {graph_sim_threshold}

ln -rs ~/sim2/{experiment_name_1} ~/sim2/{experiment_name_1}/{data_name}

ln -rs ~/sim2/{experiment_name_1}/{experiment_name_1}.jsonl ~/sim2/{experiment_name_1}/graph.jsonl

=====================================

python ~/hds-g/graphDataAnalysis/convert_data.py --input-dir ~/sim2/{experiment_name_1} \\
                                                 --data-name {data_name} \\
                                                 --experiment-name {experiment_name_2} \\
                                                 --algorithms {comma_algos} \\
                                                 --seed {seed} \\
                                                 --sim-threshold {stager_sim_threshold} \\
                                                 --max-edges 10000000000000

ln -rs ~/sim2/{experiment_name_1}/{experiment_name_2}/graph.jsonl ~/sim2/{experiment_name_1}/{experiment_name_2}/{experiment_name_2}.jsonl

python ~/hds-g/graphHDS/runGraphHDS2.py --staging-dir ~/sim2/{experiment_name_1}/{experiment_name_2} \\
                                        --no-mapping \\
                                        -n {autohdsg_flow} \\
                                        --shave-rate .01 \\
                                        --min-shave {min_shave} \\
                                        --seed {seed} \\
                                        --experiment-name {experiment_name_2}

(cd ~/sim2/{experiment_name_1}/{experiment_name_2}/{experiment_name_2}; genediver)
(cd ~/sim2/{experiment_name_1}/{experiment_name_2}/hmetis; shmetis graph 5 15)
(cd ~/sim2/{experiment_name_1}/{experiment_name_2}/kahip; kaffpa graph --k=5 --preconfiguration=strong)
(cd ~/sim2/{experiment_name_1}/{experiment_name_2}/kahypar; KaHyPar -h graph -k 5 -e 0.01 -o cut -m recursive -p ~/cut_rKaHyPar_dissertation.ini)
(cd ~/sim2/{experiment_name_1}/{experiment_name_2}/patoh; patoh graph 5)

python -c '
import json
import os
staging_dir = os.path.expanduser("~/sim2/{experiment_name_1}/{experiment_name_2}")
with open(os.path.join(staging_dir, "params.json")) as f:
    gloabl_params = json.load(f)
gloabl_params["algorithms"] = {json_algos}
gloabl_params["data_set"] = "{data_name}"
gloabl_params["experiment_name"] = "{experiment_name_2}"
gloabl_params["min_stability"] = 0.0
gloabl_params["trial_set"] = "{experiment_name_2}"
with open(os.path.join(staging_dir, "params.json"), "w") as f:
    json.dump(gloabl_params, f, indent=2, sort_keys=True)
'

python ~/hds-g/graphDataAnalysis/run_measurements.py --seed {seed} \\
                                                     --staging-dir ~/sim2/{experiment_name_1}/{experiment_name_2} \\
                                                     --similarity-algo point-precision \\
                                                     --shave-type flow_shave \\
                                                     --shaving-algo 1 \\
                                                     --debug
python ~/hds-g/graphDataAnalysis/run_measurements.py --seed {seed} \\
                                                     --staging-dir ~/sim2/{experiment_name_1}/{experiment_name_2} \\
                                                     --similarity-algo point-precision \\
                                                     --shave-type rand_shave \\
                                                     --shaving-algo 1 \\
                                                     --debug
python ~/hds-g/graphDataAnalysis/ari_plot.py --staging-dir ~/sim2/{experiment_name_1}/{experiment_name_2} \\
                                             --markers

python ~/hds-g/graphDataAnalysis/run_measurements.py --seed {seed} \\
                                                     --staging-dir ~/sim2/{experiment_name_1}/{experiment_name_2} \\
                                                     --similarity-algo edge-ari \\
                                                     --shave-type flow_shave \\
                                                     --shaving-algo 1 \\
                                                     --debug
python ~/hds-g/graphDataAnalysis/run_measurements.py --seed {seed} \\
                                                     --staging-dir ~/sim2/{experiment_name_1}/{experiment_name_2} \\
                                                     --similarity-algo edge-ari \\
                                                     --shave-type rand_shave \\
                                                     --shaving-algo 1 \\
                                                     --debug
python ~/hds-g/graphDataAnalysis/ari_plot.py --staging-dir ~/sim2/{experiment_name_1}/{experiment_name_2} \\
                                             --markers

python ~/hds-g/graphDataAnalysis/run_measurements.py --seed {seed} \\
                                                     --staging-dir ~/sim2/{experiment_name_1}/{experiment_name_2} \\
                                                     --similarity-algo edge-precision \\
                                                     --shave-type flow_shave \\
                                                     --shaving-algo 1 \\
                                                     --debug
python ~/hds-g/graphDataAnalysis/run_measurements.py --seed {seed} \\
                                                     --staging-dir ~/sim2/{experiment_name_1}/{experiment_name_2} \\
                                                     --similarity-algo edge-precision \\
                                                     --shave-type rand_shave \\
                                                     --shaving-algo 1 \\
                                                     --debug
python ~/hds-g/graphDataAnalysis/ari_plot.py --staging-dir ~/sim2/{experiment_name_1}/{experiment_name_2} \\
                                             --markers


"""


def format_template(power, graph_sim_threshold, stager_sim_threshold,
                    data_name, algos, autohdsg_flow, min_shave, seed,
                    similarity_algo, shave_type):
    return TEMPLATE.format(
        experiment_name_1="{data_name}__p{power}__s{graph_sim_threshold}".format(
            data_name=data_name,
            power=power,
            graph_sim_threshold=graph_sim_threshold
        ),
        power=power,
        experiment_name_2="s{stager_sim_threshold}__n{autohdsg_flow}".format(
            stager_sim_threshold=stager_sim_threshold,
            autohdsg_flow=autohdsg_flow
        ),
        data_name=data_name,
        comma_algos=",".join(algos),
        seed=seed,
        graph_sim_threshold=graph_sim_threshold,
        stager_sim_threshold=stager_sim_threshold,
        autohdsg_flow=autohdsg_flow,
        min_shave=min_shave,
        json_algos=json.dumps(algos),
        similarity_algo=similarity_algo,
        shave_type=shave_type
    )


def main():
    print(format_template(**CONFIG))


if __name__ == "__main__":
    main()
