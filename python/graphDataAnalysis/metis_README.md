# General README for metis

### (converting data, using metis, and getting results)

## convert_data.py

In this file, pass in the following parameters:

```
--sample 0.01 -d pokec -a metis -rs 123 -sd /[rootdirectory]/hds_measurements/
```

The sample tell us how much data to pull from the pokec dataset
In this case, we will generate a file of 900 connected nodes which we will use

The `-rs` is a random seed number, which we dont need to mess with (it can be anything)
`-sd` is directory where the dataset is located (in the root of where the metis folder will be created)

## metis

### Downloading

First Download metis from this site:
[metis download](http://glaros.dtc.umn.edu/gkhome/metis/metis/download)

### Running

Then, run metis by navigating to the folder where it is installed and running the following command

```
[metis location]/build/Linux-x86_64/programs/gpmetis graph 8
```

the `8` is the number of clusters we want to produce
This will generate a graph.part.8 file which will be used by the `run_measurements.py` file

## run_measurements.py

Example:

```
-d "pokec" -a "metis" -s "[root]/hds_measurements/"
```

After running this, the program will output the stats for the data in the console
