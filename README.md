HIMAG Dataset & Code Release

Datasets
========

In the `./datasets/` directory, we release the following five datasets:
* Marketing: Education
* Marketing: Wellness
* Pokec social graph
* LiveJournal social graph
* Sim-2 test data

**Marketing datasets** were generated by processing raw data crawled from
Instagram. The raw source data is not being released with this paper. However,
we are releasing the graphs for use by the community. They are available in
`./datasets/marketing/`.

The **Pokec social graph** was created by processing the raw graph made
available by the Stanford Network Analysis Project at
[snap.stanford.edu/data/soc-Pokec.html](https://snap.stanford.edu/data/soc-Pokec.html).

The **LiveJournal social graph** was also created by processing the raw graph
made available by the Stanford Network Analysis Project at
[snap.stanford.edu/data/com-LiveJournal.html](https://snap.stanford.edu/data/com-LiveJournal.html).

The social graphs are available in `./datasets/social_graphs`.

**Sim-2** spatial data is re-used from the Auto-HDS paper, and is transformed
into a graph (**Sim-2 Graph**). The original spatial data is available in
`./datasets/sim2/spatial/`. The data was converted to a graph using
`dist(a, b)/max_dist` as the edge weight, as explained in our paper. The graph
is available in `./datsets/sim2/graph/`.

See also the licenses at `./datasets/marketing/LICENSE` and
`./datasets/topic_model/LICENSE`.


Gene DIVER 3.0
==============

Gene DIVER 3.0 is extended from Gene DIVER 2.0. Both are written in Java.

Gene DIVER 3.0 is located in `./GeneDIVER3.0`, where both the source code and
compiled JAR are available.

There is also a convenience script `./GeneDIVER3.0/genediver64.sh` to start it
on UNIX if `jdk1.7.0_79` is located in `$HOME`.

See also the license at `./GeneDIVER3.0/LICENSE`.


Experimental Tools
==================

In `./python` are contained all the tools we used to run experiments.

The following is required to be installed for full functionality:
* Python 3
* virtualenvwrapper (see [instructions](https://virtualenvwrapper.readthedocs.io/en/latest/install.html#basic-installation))
* Java (for Gene DIVER 3.0)
* hMETIS (see instructions at `./python/graphDataAnalysis/hmetis_README.md`)
* KaHIP (see instructions at `./python/graphDataAnalysis/kahip_README.md`)
* KaHyPar (see instructions at `./python/graphDataAnalysis/kahypar_README.md`)
* PaTOH (see instructions at `./python/graphDataAnalysis/patoh_README.md`)

To build the Python virtualenv, `cd` into `./python` in a Bash terminal, and
source the `setup.sh` script.

See also the license at `./python/LICENSE`.


### Sim-2 results reproduction

Run `./python/sim2/automated_run.py` to get a list of steps to reproduce Sim-2
results.


### Social graph results reproduction

These steps are for Pokec. The process is almost identical for LiveJournal

**Step 1:** Set up staging directory

Create a directory for staging and move `soc-pokec-profiles.txt` and
`soc-pokec-relationships.txt` into it.

**Step 2:** Convert data to graph.

Run `./python/graphDataAnalysis/convert_data.py` with appropriate arguments.

**Step 3:** Stage the graph

Run `./python/graphHDS/stage_graph_for_autohds.py` with appropriate arguments.

Then, symlink the generated `pokec/experiment_name/graph.jsonl` to
`pokec/experiment_name/himag_experiment_name.json`, and symlink
`pokec/experiment_name/graph.mapping.tsv` to
`pokec/experiment_name/himag_experiment_name.mapping.tsv`.

**Step 4:** Run HIMAG

Run `./python/graphHDS/runGraphHDS2.py` with appropriate arguments.

Run `./GeneDIVER3.0/genediver64.sh` and select
`pokec/experiment_name/himag_experiment_name/graph.txt`.

**Step 5:** Stage the data for other algorithms

For the algorithms that you want to do **2k** runs for, copy their generated
directories to `<algo_name>.overclustered`.

Run `./python/graphDataAnalysis/prepare_algos.py` with appropriate arguments.

**Step 6:** Run other algorithms

The previous step will have printed commands to run the other algorithms. Run
them.

**Step 7:** Run measurements

Run `./python/graphDataAnalysis/run_measurements.py` with appropriate
arguments.

**Step 7:** Generate plots (optional)

Run `./python/graphDataAnalysis/ari_plot.py` with appropriate arguments.

### Marketing results reproduction

The labels were already generated based on clusterings for the algorithms, so
generating measurements does not involve running the algorithms again. The
tools for dealing with this data are in `./python/labeling/`.

### Notes

* Exhaustive cannot-link labels are needed to compute Edge ARI correctly. Since our Marketing datasets were judged manually, Edge ARI was not possible to compute, so only Point Precision results are presented on them.
* To plot the performance by fraction of data clustered, we took the most stable non-overlapping clusters from HIMAG. This gives us not only the total fraction of data clustered, but also allows us to plot increasing fraction of data clustered by including progressively less stable clusters.
* The number of clusters to predict (**k**) and the fraction of data clustered are passed to other methods based on the output of HIMAG to make the comparison fair. We also ran other methods with double the clusters (**2k**) to improve their performance in some cases where they performed poorly compared to HIMAG when the *k* was the same.
* The results of all of the methods we compete against were much worse on the Marketing data for **k** than for **2k**. Since labeling was expensive, we only present results for **2k** on those datasets.
* Since HIMAG clusters only a fraction of data, two different methods were used to shave the clusters obtained from the partitional algorithms to produce smaller clusters and to have the same fraction of data clustered as HIMAG. **RAND** represents randomly selecting a fraction of the points from each cluster, while **FLOW** represents shaving each cluster by removing the least dense nodes until the desired number of nodes remain.
* A regularization term was added to the denominator of the Jaccard before computing the ratio, as otherwise, nodes with a small number of terms generate noisy high similarity edges. This substantially improves results on these datasets for all algorithms.
* We also pre-thresholded most graphs for speed, as the low similarity edges don't capture any additional information for finding high quality dense sub-graphs. A threshold of 0.25 was used to prune edges on Marketing data.
* For the standard social graphs, the "interests" were the terms used for computing the Jaccard similarities between two people.  We use the community profile that these two datasets provide, namely "hobbies" for Pokec and "communities" for LiveJournal, to compute this interests graph. Only 2% of the edges were used for building the graphs, while the remaining 98% of the graph edges were held back and used as "labels".
