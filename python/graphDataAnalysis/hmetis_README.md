# General README for hmetis

### (converting data, using hmetis, and getting results)

## convert_data.py

In this file, pass in the following parameters:

```
--sample 0.01 -d pokec -a hmetis -rs 123 -sd /[rootdirectory]/hds_measurements/
```

The sample tell us how much data to pull from the pokec dataset
In this case, we will generate a file of 900 connected nodes which we will use

The `-rs` is a random seed number, which we dont need to mess with (it can be anything)
`-sd` is directory where the dataset is located (in the root of where the hmetis folder will be created)

## hmetis

### Downloading

First Download hmetis from this site:
[hmetis download](http://glaros.dtc.umn.edu/gkhome/metis/hmetis/download)

### Running

Then, run hmetis by navigating to the folder where it is installed and running the following command

```
[hmetis location]/shmetis [path of the graph file] [num_clusters] 5
```

This will generate a graph.part.\[num_clusters\] file which will be used by the `run_measurements.py` file

## run_measurements.py

Example:

```
-d "pokec" -a "hmetis" -s "[root]/hds_measurements/"
```

After running this, the program will output the stats for the data in the console
