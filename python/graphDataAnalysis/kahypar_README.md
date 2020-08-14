# General README for KaHyPar

### Installation

Installation instructions:
1. `git clone --depth=1 --recursive https://github.com/SebastianSchlag/kahypar.git`
2. `cd kahypar && mkdir build && cd build`
3. `sudo apt-get install libboost-all-dev`
4. `cmake .. -DCMAKE_BUILD_TYPE=RELEASE`
5. `make` (warning takes like 10 minutes)
6. If steps 4 or 5 did not work, add `set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++14")` after the first line of `kahypar/lib/CMakeLists.txt` or `kahypar/CMakeLists.txt`



### Running

Then, run KaHyPar by navigating to the folder where it is installed and running the following command

```
[KaHyPar location]/build/kahypar/application/KaHyPar -h <path-to-hgr> -k <# blocks> -e <imbalance (e.g. 0.03)> -o cut -m recursive -p [KaHyPar location]/config/cut_rKaHyPar_dissertation.ini
```

### Input/Output

The input output for kahypar is the same as hmetis.
