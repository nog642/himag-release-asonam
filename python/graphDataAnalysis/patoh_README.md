# General README for PaToH

### Installation

Installation instructions:
1. Download and unzip `https://www.cc.gatech.edu/~umit/PaToH/patoh-Linux-x86_64.tar.gz`

### Running

Then, run PaToH by navigating to the folder where it is installed and running the following command

```
[patoh location]/Linux-x86_64/patoh <h-graph> <# clusters>
```

### Input/Output

The input is different, and the output is the same as hmetis.

Input format:

The first line contains 5 integers. The first one–either 1, or 0– shows the base value
used in indexing the vertices and edges. Next the number of vertices, edges, and pins should
be present. The fifth integer is 1 and describes the weighting scheme to be weights on edges.

Every line after is the weight followed by the vertices for each edge
