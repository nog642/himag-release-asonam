# General README for kaHIP

### Installation

Installation instructions:
1. Download and unzip `http://algo2.iti.kit.edu/schulz/software_releases/KaHIP_2.12.tar.gz`
2. Install Scons (http://www.scons.org/) with `sudo apt install scons`
3. Install Argtable (http://argtable.sourceforge.net/) with `sudo apt install libargtable2-0`
4. Install OpenMPI (https://www.open-mpi.org/faq/?category=building#easy-build)
5. Run `sudo ldconfig`
6. `./compile.sh`
7. If you cannot get `compile.sh` to work, try `compile_withcmake.sh`

### Running

Then, run kaHIP by navigating to the folder where it is installed and running the following command

```
[kaHIP location]/kaffpa <h-graph> --k=<# clusters> --preconfiguration=strong
```

### Input/Output

The input for kaHIP is the same as metis, and the output is the same as hmetis/metis.
