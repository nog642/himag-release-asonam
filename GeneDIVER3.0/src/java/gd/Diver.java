package gd;

/*
 * Main program for Auto-HDS clustering
 * Gunjan Gupta.
 * August 2006
 *  Version 1.0
 * IMPORTANT: Assumes Java initialization of boolean and int to false and 0 respectively
 * when initializing new arrays. Look for WARNING keyword JIA
 */
import java.io.*;
import java.util.*;

// these vectors are sortable, from left to right.
// and consist of comparable objects such as integers
// e.g. [0 0 1] < [0 2 3] and [1 0 0] > [0 1 1]
class SortableIntVector implements Comparable<SortableIntVector> {

    public SortableIntVector() {
        try {
            jbInit();
        } catch (Exception ex) {
            ex.printStackTrace();
        }
    }

    int[] rowData = null;
    int id = -1;

    SortableIntVector(int[] objectList, int idIn) {
        int numItems = objectList.length;
        rowData = new int[numItems];
        for (int i = 0; i < numItems; i++) {
            rowData[i] = objectList[i];
        }
        id = idIn;
    }

    public int compareTo(SortableIntVector objIn) {
        // check the elements from left to right
        int objSize = objIn.rowData.length;
        int curSize = rowData.length;
        int useSize = curSize;
        // use smaller of the two
        if (objSize < curSize) {
            useSize = objSize;
        }

        int retVal = 0;
        for (int i = 0; i < useSize; i++) {
            retVal = (int) Math.round(Math.signum((rowData[i] - objIn.rowData[i])));
            if (retVal != 0) {
                break;
            }
        }
        return retVal;
    }

    private void jbInit() throws Exception {
    }
};

class Diver {

    public static final String HDSFILEEXTENSION = ".hds";
    public static final String SORTEDHDSFILEEXTENSION = "_sorted.hds";
    public static final String LABELFILEEXTENSION = "_lab.csv";

    public static final int DEFAULT_DISC_BUFFER = 40000000;
    // Default DISC BUFFER SIZE round 40-80 Megabytes
    protected int DISC_BUFFER = DEFAULT_DISC_BUFFER;

    // Auto-HDS works well with these 3 distance measures, and they are implemented
    // already. Choice specified as input when passing vector data file
    public static final int EUCLIDEAN = 0;
    public static final int PEARSON = 1;
    public static final int COSINE = 2;

    // ESSENTIAL CLUSTERING RESULTS STORED AS GLOBAL VARS
    // HMA(Auto-HDS) tree: obtained after running Auto-HDS relabeling
    // algo on hdsLabels
    public int[][] hmaLabels = null;

    // number of hma clusters
    int numHMAClusters = 0;

    // last HMA level that still has some non-runt points in it
    int lastNonEmptyHMALevel = -1;

    // index of points at the base of each HMA cluster
    Vector<Integer[]> hmaBaseMembers = null;

    // hma clusters base positions
    public Vector<Integer> hmaBaseLevels = null;

    // hma peak/plateau levels - last level where a cluster survives
    public int[] hmaPeakLevels = null;

    // stability values of each of the clusters, adjusted using the
    // shaving rate formula
    public double[] clusterStability = null;

    // index to a sorted list of clusters, ordered by decreasing stability
    public int[] clusterRankOrder = null;

    // counts of points of various labels found in each cluster
    int hmaBaseLabels[][] = null;

    int[] hmaClusterSize = null;

    // stores the first row index in the sorted points list where a member point of each
    // cluster occurs
    int[] firstClusterIndex = null;

    // Raw HDS tree: computed tree levels stored here as cluster labels
    public int[][] hdsLabels = null;

    // sorted ids of hdsLabels using dictionary sort ordering
    public int[] sortedTreeIdx = null;

    // number of clusters in each iteration of the HDS tree
    int[] numClusters = null;

    // column index of class column
    int classColIdx = -1;

    // storage of class labels, for browsing clustering in HMA gui
    int[] ptClassLabel = null;

    // unique class labels found corresponding to ptClassLabel
    int[] classlabels = null;

    // tells the space file reader to skip first data line
    // (usually when it contains field names)
    boolean skipFirstDataLine = false;

    // if this is passed as true Gene DIVER will reuse previous clustering only 
    // does not try to recluster. useful for external graph clustering being 
    // passed in
    boolean skipDataFileClustering = false;

    public static final String[] distPrintName = {
        "Eucidean", "Pearson", "Cosine"};

    // selected distance measure value
    protected int MEASURE = Diver.EUCLIDEAN;

    // maximum no. of clustering levels, unless decay levels are really small,
    // will never have 1000 levels
    int MAXLEVEL = 1000;

    // index of the densest points for when no. of dense pts is
    // largest, i.e. round(numPt*(1-fshave))
    int[] denseIdx = null;

    // list of sizes to cluster
    int[] denseSizeList = null;

    // index of nbrs for each of the dense points
    int[][] dptsNbrs = null;

    // nbrs size list for each dense point for each size in denseSizeList
    int[][] dptsNbrSize = null;

    // used to store indexes of dense points for quick lookup
    // for each of the possible clustering sizes
    boolean[][] isDense = null;

    // list of reps corresponding to denseSizeList
    double[] repsList = null;

    // heap corresponding to the denseIdx
    double[] nepsColVal = null;

    int[] nepsColIdx = null;

    // automatically estimated neighborhood ball readius reps
    // for the clustering when no. of dense pts is largest, i.e. round(numPt*(1-fshave))
    double maxreps = -1;

    Diver(int discBufferIn, int distMeasureIn, int classColIdxIn, boolean skipFirstIn, boolean skipDataFileClusteringIn) {
        DISC_BUFFER = discBufferIn;
        MEASURE = distMeasureIn;
        classColIdx = classColIdxIn;
        skipFirstDataLine = skipFirstIn;
        skipDataFileClustering = skipDataFileClusteringIn;
    }

    // computes the no. of points in dense clusters for the
    // distinct clusterings corresponding to the shaving rate of rshave
    // and the largest desired cluster size related to fshave
    public int[] getDenseList(double fshave, double rshave, int numPt) {
        int[] denseSize = new int[MAXLEVEL];

        double remainP = 1 - rshave;
        int iter = 1, level = 1;
        int biggestSize = (int) Math.round((1 - (float) fshave) * numPt);
        int iterNumDense = biggestSize;
        denseSize[0] = biggestSize;
        do {
            iterNumDense = Math.round((float) (Math.pow(remainP, iter) * biggestSize));
            // check if this new size is different from last one, rounding
            // will sometimes make it the same
            if (iterNumDense < denseSize[level - 1]) {
                denseSize[level] = iterNumDense;
                level++;
            }
            iter++;
        } while (iterNumDense > 1);

        // now return this unique list of sizes
        int[] retDenseList = new int[level];
        for (int i = 0; i < level; i++) {
            retDenseList[i] = denseSize[i];
        }
        return retDenseList;
    }

    // resize the dense sizes based on the ACTUAL count of dense point flags
    // needed because some times there are two points at identical distances
    // resulting in actual counts being off by 1 at times
    protected void validateDenseSizes() {
        int numPt = isDense.length;
        for (int j = 0; j < denseSizeList.length; j++) {
            int actualSize = 0;
            for (int i = 0; i < numPt; i++) {
                if (isDense[i][j]) {
                    actualSize = actualSize + 1;
                }
            }
            if (actualSize != denseSizeList[j]) {
                System.out.println("Found " + actualSize + " dense points at level " + j);
                System.out.println("Size asked for was " + denseSizeList[j]);
                System.out.println("Changing level " + j + " clustering size to " + actualSize);
                denseSizeList[j] = actualSize;
            }
        }
    }

    // sorts the generated HDS tree by labels across all elements
    protected void sortHDSRawTree() {
        // extract the tree labels to create a sortable string
        int numPt = hdsLabels.length;
        int numiter = hdsLabels[0].length;

        SortableIntVector[] hdsTreeTmp = new SortableIntVector[numPt];
        for (int i = 0; i < numPt; i++) {
            hdsTreeTmp[i] = new SortableIntVector(hdsLabels[i], i);
        }

        Arrays.sort(hdsTreeTmp);

        // now recover the sorted index and store it
        sortedTreeIdx = new int[numPt];
        for (int i = 0; i < numPt; i++) {
            sortedTreeIdx[i] = hdsTreeTmp[i].id;
        }
    }

    // computes the Sq. Euclidean distance of a given point from ALL other points
    protected double[] computeSqEucDistance(double[][] vdataIn, int ptIdx) {
        double[] retVal = new double[vdataIn.length];
        retVal[ptIdx] = 0; // distance with itself
        for (int i = 0; i < ptIdx; i++) {
            retVal[i] = 0;
            for (int j = 0; j < vdataIn[0].length; j++) {
                // d= d+ (x_i(j) - pt(j))^2;
                retVal[i] = retVal[i] + Math.pow(vdataIn[i][j] - vdataIn[ptIdx][j], 2);
            }
        }
        // note we are skipping the ptIdx
        for (int i = (ptIdx + 1); i < vdataIn.length; i++) {
            retVal[i] = 0;
            for (int j = 0; j < vdataIn[0].length; j++) {
                // d= d+ (x_i(j) - pt(j))^2;
                retVal[i] = retVal[i] + Math.pow(vdataIn[i][j] - vdataIn[ptIdx][j], 2);
            }
        }
        return retVal;
    }

    // gets the nearest nbrs, recomputes them if needed by calling appropriate
    // methods, or loads previously computed ones.
    public boolean getNNbrs(String fileIn, int neps, double fshave, double rshave,
            boolean onlyDS, boolean matrixFlag, String delim,
            int debugFlag) {
        boolean retVal = true;

        int lastNeps = -1;
        double lastfshave = -1;

        boolean foundDistFile = true;
        // presorted and heaped distance file
        String readyDistFile = ModelUtil.removeExtension(fileIn) + ".dist";
        try {
            DataInputStream fi = new DataInputStream(new BufferedInputStream(new FileInputStream(
                    readyDistFile), DISC_BUFFER));
            // now read to see how much neps was processed last time
            fi.readBoolean(); // dump variable scratch flag, know it will be true
            lastNeps = fi.readInt();
            lastfshave = fi.readDouble();
            fi.close();
        } catch (IOException e) {
            // presorted dist file not found
            foundDistFile = false;
        }

        // count the no. of points in the data file
        int numLine = ModelUtil.getNumNonEmptyLines(fileIn, DISC_BUFFER, true);

        int numPt = numLine;
        if (skipFirstDataLine == true) {
            numPt = numLine - 1;
        }

        int numCol = ModelUtil.getNumColumns(fileIn, DISC_BUFFER, delim);

        // distance matrix available
        if (matrixFlag == true) {
            // no previously computed distance file present
            if (foundDistFile == false) {
                createScratchFileFromDistFile(fileIn, numLine, neps, fshave, onlyDS,
                        delim, debugFlag);
                createReadyIndexFromScratch(fileIn, numPt, rshave, onlyDS, debugFlag);
            } else // conditions under which the previous sorting would be sufficient
            // in such a case we also do not update/overwrite the old ready file
             if ((lastNeps >= neps) && (lastfshave <= fshave)) {
                    createNNbrFromOldReady(fileIn, numPt, neps, fshave, rshave, onlyDS,
                            debugFlag);
                } else {
                    // partial sorting only might be available in ready file
                    createScratchFileFromOldReady(fileIn, numPt, neps, fshave, onlyDS,
                            debugFlag);
                    createReadyIndexFromScratch(fileIn, numPt, rshave, onlyDS, debugFlag);
                }
        } else // no previously computed distance file present
         if (foundDistFile == false) {
                retVal = createScratchFileFromSpaceFile(fileIn, numLine, numCol, neps, fshave,
                        onlyDS, delim, debugFlag);
                if (retVal == false) {
                    return retVal;
                }
                createReadyIndexFromScratch(fileIn, numPt, rshave, onlyDS, debugFlag);
            } else // conditions under which the previous sorting would be sufficient
            // in such a case we also do not update/overwrite the old ready file
             if ((lastNeps >= neps) && (lastfshave <= fshave)) {
                    createNNbrFromOldReady(fileIn, numPt, neps, fshave, rshave, onlyDS,
                            debugFlag);
                } else {
                    // partial sorting only might be available in ready file
                    createScratchFileFromOldReady(fileIn, numPt, neps, fshave, onlyDS,
                            debugFlag);
                    createReadyIndexFromScratch(fileIn, numPt, rshave, onlyDS, debugFlag);
                }

        // now compute the HDS tree
        //computeHDSTreeSmart(fileIn, debugFlag);
        computeHDSTree(fileIn, debugFlag);

        sortHDSRawTree();

        // Save the computed raw tree as .auto file
        saveHDSTree(fileIn);
        // Save other data essential to be able to reload later
        // and skipping HDS clustering
        saveHDSData(fileIn, debugFlag);

        return retVal;
    }

    // performs the same function as createScratchFileFromDistFile, except is able to convert
    // an old ready (.dist) file into a scratch file
    protected void createScratchFileFromOldReady(String fileIn, int numLine,
            int neps, double fshave,
            boolean onlyDS, int debugFlag) {
        // final presorted and heaped distance file
        String oldReadyFile = ModelUtil.removeExtension(fileIn) + ".dist";

        // partial presorted heaped scratch distance file
        String scratchFile = ModelUtil.removeExtension(fileIn) + ".scratch";

        if (debugFlag > 0) {
            System.out.println("Creating variable scratch file " + scratchFile
                    + "\n from old ready file " + oldReadyFile);
            System.out.println(
                    "Variable scratch file will contain heaped matrix rows with at least sorted "
                    + neps + " closest nbrs...");
        }

        int debugWidth = ModelUtil.getDebugWidth(numLine, 500, 10000);

        DataOutputStream fo = null;
        try {
            fo = new DataOutputStream(new BufferedOutputStream(new FileOutputStream(scratchFile), DISC_BUFFER));
        } catch (IOException e) {
            System.err.println("Unable to open this file for writing: " + scratchFile);
            return;
        }

        // now open the scratch file for writing the dist. matrix rows
        // with only the first neps elements sorted
        try {
            DataInputStream fi = new DataInputStream(new BufferedInputStream(new FileInputStream(
                    oldReadyFile), DISC_BUFFER));

            // FIRST PIECE OF INFO STORED IN SCRATCH FILE. ALLOWS READY FILES
            // TO OPTIONALLY BE TREATED AS READY FILES
            // this tells us whether the scratch file contains only neps sorting
            // or variable sorting for each row. If variable, the sorted length is
            // then read. If constant, sorted length assumed to be neps. Scratch files
            // created from scratch are always false, while for those coming from recycled
            // old Ready file, this value is true. This helps i reading rows of scratch
            // file correctly by function createReadyIndexFromScratch()
            fo.writeBoolean(true);
            fi.readBoolean(); // ignore corresponding scratch flag from old ready file

            // read the old neps and fshave
            fi.readInt();
            fi.readDouble();

            // save the neps that is being used for scratch
            fo.writeInt(neps);

            // a main objective of the scratch call is to initialize these two, needed
            // later by createReadyIndexFromScratch() function call
            nepsColVal = new double[numLine];
            nepsColIdx = new int[numLine];

            double[] row = new double[numLine];
            int[] rowIdx = new int[numLine];
            int denseCnt = -1;
            int lastnumSorted = -1, numSorted = -1;

            // no. of densest points to cluster for the largest possible clustering
            // in the HDS hierarchy
            denseCnt = Math.round(numLine * (1 - (float) fshave));

            // shaving fraction
            fo.writeDouble(fshave);

            long tic = (new Date()).getTime();

            for (int i = 0; i < numLine; i++) {
                lastnumSorted = fi.readInt();
                // read i^th row heap from old ready file
                for (int k = 0; k < numLine; k++) {
                    row[k] = fi.readDouble();
                    rowIdx[k] = fi.readInt();
                }
                // find the first neps neihbors of this point
                // only need to sort a bit more if needed :-) COOL CPU SAVER!
                numSorted = lastnumSorted;
                if (lastnumSorted < neps) {
                    HeapSort.continuePartIdxSort(row, rowIdx, lastnumSorted, neps);
                    numSorted = neps;
                }

                // now save the partially sorted row and index to disk in a serialized manner
                // for further sorting later, along with the sorted size
                fo.writeInt(numSorted);
                for (int k = 0; k < numLine; k++) {
                    fo.writeDouble(row[k]);
                    fo.writeInt(rowIdx[k]);
                }

                // index of the neps^th nbr, that is stored ass-backward at the end
                int nepsLastIdx = rowIdx[numLine - neps];

                // save the neps^th neihbor's point distance for this point
                nepsColIdx[i] = i;
                nepsColVal[i] = row[nepsLastIdx];

                if (debugFlag > 0) {
                    if ((i + 1) % debugWidth == 0) {
                        System.out.println("Sorted " + i + " out of " + numLine
                                + " rows...");
                    }
                }
            }

            // find the densest points, and their order by neps nbrs radius
            HeapSort.partIdxSort(nepsColVal, nepsColIdx, denseCnt);

            // compute the index of the ordered densest points, presists in memory
            denseIdx = HeapSort.extractTopNeps(nepsColIdx, denseCnt);

            // now compute max reps as the least dense point's neps radius among all the
            // dense points. persisted in memory
            maxreps = nepsColVal[denseIdx[denseCnt - 1]];

            if (debugFlag > 1) {
                System.out.println("Max reps= " + maxreps + " for clustering "
                        + denseCnt
                        + " out of " + numLine + " points.");

                System.out.println("Densest points and their neps ball rads:");
                for (int j = 0; j < 10; j++) {
                    System.out.println("[" + denseIdx[j] + "]="
                            + nepsColVal[denseIdx[j]]);
                }
                long toc = (new Date()).getTime();
                System.out.println("Parsing+Sorting=" + (toc - tic) + " millsecs");
            }

            // done creating scratch file
            fo.close();
            fi.close();

            // now we can delete the old ready file as it is obsolete
            File oldRdFile = new File(oldReadyFile);
            boolean success = oldRdFile.delete();
            if (success == false) {
                System.err.println("Could not delete old ready file: " + oldReadyFile);
                return;
            } else // now delete the scratch file by making it zero bytes
             if (debugFlag > 0) {
                    System.out.println("Deleting old ready file: " + oldReadyFile);
                }
        } catch (IOException e) {
            System.err.println("Unable to open this file for writing: " + scratchFile);
            return;
        }
    }

    // now we use the scratch file to expand the neigborhood around each point to cover reps
    // distance neighbors, needed for the HDS and DS algorithms to work.
    protected void createNNbrFromOldReady(String fileIn, int numPt, int neps,
            double fshave, double rshave,
            boolean onlyDS, int debugFlag) {
        // already presorted and heaped distance file
        String readyFile = ModelUtil.removeExtension(fileIn) + ".dist";

        // to store the heaped sorted rows from the
        // the old ready file, one row at a time
        double[] row = new double[numPt];
        int[] rowIdx = new int[numPt];

        // read from scratch file
        double lastfshave = -1;
        int lastneps = -1;
        boolean lastonlyDS = false;

        int denseCnt = -1, lastnumSorted = -1;

        int debugWidth = ModelUtil.getDebugWidth(numPt, 500, 10000);

        try {
            DataInputStream fi = new DataInputStream(new BufferedInputStream(new FileInputStream(readyFile),
                    DISC_BUFFER));

            // read back everything in exactly the order it was saved
            fi.readBoolean(); // dump the flag for variableScratch, we know it will be true for a ready file
            // last neps
            lastneps = fi.readInt();

            // last shaving fraction/rate
            lastfshave = fi.readDouble();

            if (debugFlag == 1) {
                System.out.println("Reading presorted ready file " + readyFile);
                System.out.println("Already contains heaped matrix rows for neps "
                        + lastneps + " and fshave " + lastfshave);
            }

            // compute the clustering sizes based on the DS only flag
            if (onlyDS == true) {
                denseSizeList = new int[1];
                denseSizeList[0] = Math.round(numPt * (float) (1 - fshave));
            } else {
                denseSizeList = getDenseList(fshave, rshave, numPt);
            }

            // largest cnt of dense points
            denseCnt = denseSizeList[0];

            if ((debugFlag > 0) && (denseSizeList.length > 1)) {
                System.out.println(denseSizeList.length
                        + " distinct Auto-HDS levels will be created of clustering size "
                        + denseSizeList[denseSizeList.length - 1] + " to "
                        + denseSizeList[0]);
            }

            // nbr indexes for each point
            dptsNbrs = new int[numPt][];

            nepsColVal = new double[numPt];
            nepsColIdx = new int[numPt];

            long tic = (new Date()).getTime();

            for (int i = 0; i < numPt; i++) {
                // how many were sorted last time
                lastnumSorted = fi.readInt();

                // read i^th row heap
                for (int k = 0; k < numPt; k++) {
                    row[k] = fi.readDouble();
                    rowIdx[k] = fi.readInt();
                }

                // index of the neps^th nbr, that is stored ass-backward at the end
                int nepsLastIdx = rowIdx[numPt - neps];

                // save the neps^th neihbor's point distance for this point
                nepsColIdx[i] = i;
                nepsColVal[i] = row[nepsLastIdx];
                if (debugFlag > 0) {
                    if ((i + 1) % debugWidth == 0) {
                        System.out.println("Pass 1 reading " + i + " out of " + numPt
                                + " rows of old ready file.");
                    }
                }
            }

            // now find the reps values
            // find the densest points, and their order by neps nbrs radius
            HeapSort.partIdxSort(nepsColVal, nepsColIdx, denseCnt);

            // compute the index of the ordered densest points, presists in memory
            denseIdx = HeapSort.extractTopNeps(nepsColIdx, denseCnt);

            // now compute max reps as the least dense point's neps radius among all the
            // dense points. persisted in memory
            maxreps = nepsColVal[denseIdx[denseCnt - 1]];

            if (debugFlag > 1) {
                System.out.println("Max reps= " + maxreps + " for clustering "
                        + denseCnt + " out of " + numPt + " points.");

                System.out.println("Densest points and their neps ball rads:");
                for (int j = 0; j < 10; j++) {
                    System.out.println("[" + denseIdx[j] + "]=" + nepsColVal[denseIdx[j]]);
                }
                long toc = (new Date()).getTime();
                System.out.println("Parsing+Sorting=" + (toc - tic) + " millsecs");
            }

            // compute the reps corresponding to all the clusterings sizes
            repsList = new double[denseSizeList.length];
            for (int i = 0; i < denseSizeList.length; i++) {
                repsList[i] = nepsColVal[denseIdx[denseSizeList[i] - 1]];
            }

            // done reading first time, close it now
            fi.close();
        } catch (IOException e) {
            System.err.println("Unable to open this file for reading: " + readyFile);
            return;
        }

        // allocate related lists
        isDense = new boolean[numPt][denseSizeList.length];

        dptsNbrSize = new int[numPt][];

        int avgNbrSize = 0;
        // now we need to estimate everything else, and prune the extra
        // nbrs based on current requirements, so we need to re-read the file in.
        try {
            DataInputStream fi = new DataInputStream(new BufferedInputStream(new FileInputStream(readyFile),
                    DISC_BUFFER));

            // have to read these to skip them
            // variableScratch flag, last neps and fshave
            fi.readBoolean();
            fi.readInt();
            fi.readDouble();

            for (int i = 0; i < numPt; i++) {
                // how many were sorted last time
                lastnumSorted = fi.readInt();

                // read i^th row heap
                for (int k = 0; k < numPt; k++) {
                    row[k] = fi.readDouble();
                    rowIdx[k] = fi.readInt();
                }

                // find out for which of reps in repsList, the current point is dense
                // since this is sorted, point will not be dense beyond a certain reps
                int lastDensePos = 0;

                for (int k = 0; k < repsList.length; k++) { // initialize dense flags for this pt
                    isDense[i][k] = false;
                }

                // now compute no. of nbrs within the reps list radiuses
                //but ONLY for reps values for which the point is dense
                dptsNbrSize[i] = new int[repsList.length];

                // neps radius of this point
                double nepsr = row[rowIdx[numPt - neps]];

                if (nepsr <= repsList[0]) { // at least this point is dense in first shaving iteration
                    int k = 0;
                    boolean doneFlag = false;
                    for (int j = lastnumSorted - 1; j > 0; j--) {
                        double curVal = row[rowIdx[numPt - j]];
                        while (curVal <= repsList[k]) {
                            dptsNbrSize[i][k] = j;
                            isDense[i][k] = true;
                            k++;
                            if (k > repsList.length - 1) { // computed for all, stop now
                                lastDensePos = k - 1;
                                doneFlag = true;
                                break;
                            }
                            if (repsList[k] < nepsr) { // check if ball too small for this reps
                                lastDensePos = k - 1;
                                doneFlag = true;
                                break;
                            }
                        }
                        if (doneFlag == true) {
                            break;
                        }
                    }
                    // set remainder nbrhood sizes to -1
                    // nbrhood not needed since pt not dense for these reps values
                    for (int j = lastDensePos + 1; j < repsList.length; j++) {
                        dptsNbrSize[i][j] = -1;
                    }

                    dptsNbrs[i] = new int[lastnumSorted - 1];

                    // now store nbrs list corresponding to the max reps size needed
                    dptsNbrs[i] = new int[dptsNbrSize[i][0]];
                    for (int j = 0; j < dptsNbrSize[i][0]; j++) {
                        dptsNbrs[i][j] = rowIdx[numPt - j - 1];
                    }

                    if (debugFlag > 0) {
                        avgNbrSize = avgNbrSize + dptsNbrs[i].length;
                    }
                } else {
                    // not a dense point even in first shaving iteration, so no need
                    // to store nbrs or their sizes for each reps
                    dptsNbrs[i] = null;
                    dptsNbrSize[i] = null;
                }
                if (debugFlag > 0) {
                    if ((i + 1) % debugWidth == 0) {
                        System.out.println("Pass 2, processed " + i + " out of " + numPt
                                + " rows...");
                    }
                }
            }

            // done reading a second time, close it now
            fi.close();

            if (debugFlag > 0) {
                System.out.println("Average nbrhood size: "
                        + Math.round(avgNbrSize / denseCnt));
            }
        } catch (IOException e) {
            System.err.println("Unable to open this file for reading: " + readyFile);
            return;
        }

        // may need to increase dense size, when created based on reps radii
        validateDenseSizes();

    }

    // now we use the scratch file to expand the neigborhood around each point to cover reps
    // distance neighbors, needed for the HDS and DS algorithms to work.
    protected void createReadyIndexFromScratch(String fileIn, int numPt,
            double rshave, boolean onlyDS,
            int debugFlag) {
        // final presorted and heaped distance file
        String readyFile = ModelUtil.removeExtension(fileIn) + ".dist";

        // partial presorted heaped scratch distance file
        String scratchFile = ModelUtil.removeExtension(fileIn) + ".scratch";

        if (debugFlag == 1) {
            System.out.println("Creating ready file " + readyFile
                    + "\n from scratch file " + scratchFile);
            System.out.println("Ready file will contain heaped matrix rows \n with all sorted nbrs within distance "
                    + maxreps);
        }

        // read from scratch file
        double fshave = -1;
        int denseCnt = -1;
        int neps = -1;
        boolean variableScratch = false;
        int lastnumSorted = -1;

        int avgNbrSize = 0;

        int debugWidth = ModelUtil.getDebugWidth(numPt, 500, 10000);

        DataOutputStream fo = null;
        try {
            fo = new DataOutputStream(new BufferedOutputStream(new FileOutputStream(readyFile), DISC_BUFFER));
        } catch (IOException e) {
            System.err.println("Unable to open this file for writing: " + readyFile);
            return;
        }

        try {
            DataInputStream fi = new DataInputStream(new BufferedInputStream(new FileInputStream(scratchFile),
                    DISC_BUFFER));

            // FIRST PIECE OF INFO STORED IN SCRATCH FILE. ALLOWS READY FILES
            // TO OPTIONALLY BE TREATED AS READY FILES
            // this tells us whether the scratch file contains only neps sorting
            // or variable sorting for each row. If variable, the sorted length is
            // then read. If constant, sorted length assumed to be neps. Scratch files
            // created from scratch are always false, while for those coming from recycled
            // old Ready file, this value is true. This helps i reading rows of scratch
            // file correctly by function createReadyIndexFromScratch()
            fo.writeBoolean(true);
            variableScratch = fi.readBoolean();

            // read back everything in exactly the order it was saved
            // read neps
            neps = fi.readInt();
            fo.writeInt(neps);

            // the scratch file is a genuine scratch file, not recycled ready file
            // then variableScratch will be false, and exactly neps nearest nbrs
            // will be available in each row
            if (variableScratch == false) {
                lastnumSorted = neps;
            }
            // shaving fraction
            fshave = fi.readDouble();
            fo.writeDouble(fshave);

            // compute the clustering sizes based on the DS only flag
            if (onlyDS == true) {
                denseSizeList = new int[1];
                denseSizeList[0] = Math.round(numPt * (float) (1 - fshave));
            } else {
                denseSizeList = getDenseList(fshave, rshave, numPt);
            }

            if ((debugFlag > 0) && (denseSizeList.length > 1)) {
                System.out.println(denseSizeList.length
                        + " distinct Auto-HDS levels will be created of clustering size "
                        + denseSizeList[denseSizeList.length - 1] + " to "
                        + denseSizeList[0]);
            }

            // max dense pts cnt
            denseCnt = denseSizeList[0];

            // allocate related lists
            repsList = new double[denseSizeList.length];

            isDense = new boolean[numPt][denseSizeList.length];

            dptsNbrSize = new int[numPt][];

            // nbr indexes for each point
            dptsNbrs = new int[numPt][];

            // compute the reps corresponding to all these clusterings
            // save the sizes used and corresponding reps for future runs
            for (int i = 0; i < denseSizeList.length; i++) {
                repsList[i] = nepsColVal[denseIdx[denseSizeList[i] - 1]];
            }

            // now read the heaped and neps nbr sorted rows in
            // sort them upto the max reps radius and save them back
            // in the read file
            double[] row = new double[numPt];
            int[] rowIdx = new int[numPt];

            for (int i = 0; i < numPt; i++) {
                // if a recycled ready file, we need to read the numSorted value
                if (variableScratch == true) {
                    lastnumSorted = fi.readInt();
                }

                // read i^th row heap
                for (int k = 0; k < numPt; k++) {
                    row[k] = fi.readDouble();
                    rowIdx[k] = fi.readInt();
                }

                // sort additional elements until the value exceeds
                // reps. Note that for non-dense points no additional sorting will happen
                int numSorted = lastnumSorted;
                // this is the size of the nbrhood within (<=) radius maxreps
                int lastValidNbr = -1;

                if (row[rowIdx[numPt - lastnumSorted]] <= maxreps) { // extension of sorting needed to guarantee one extra sorted
                    numSorted = HeapSort.extendPartIdxSort(row, rowIdx, lastnumSorted,
                            maxreps);
                    lastValidNbr = numSorted - 1;
                } else { // just need to find the first valid size, simple linear search :-(
                    lastValidNbr = numSorted;
                    while (maxreps < row[rowIdx[numPt - lastValidNbr]]) {
                        lastValidNbr--;
                    }
                }

                // store information about how many or sorted so you will know
                // how many to read back
                fo.writeInt(numSorted);

                // save all nbrs and their distance heaps in ready file
                // useful for extending later
                for (int k = 0; k < numPt; k++) {
                    fo.writeDouble(row[k]);
                    fo.writeInt(rowIdx[k]);
//              System.out.println("row["+i+"]["+rowIdx[k]+"]="+ row[k]);
                }

                // find out for which of reps in repsList, the current point is dense
                // since this is sorted, point will not be dense beyond a certain reps
                int lastDensePos = 0;

                for (int k = 0; k < repsList.length; k++) { // initialize dense flags for this pt
                    isDense[i][k] = false;
                }

                // now compute no. of nbrs within the reps list radiuses
                //but ONLY for reps values for which the point is dense
                dptsNbrSize[i] = new int[repsList.length];

                // neps radius of this point
                double nepsr = row[rowIdx[numPt - neps]];

                if (nepsr <= repsList[0]) { // at least this point is dense in first shaving iteration
                    int k = 0;
                    boolean doneFlag = false;
                    for (int j = lastValidNbr; j > 0; j--) {
                        double curVal = row[rowIdx[numPt - j]];
                        while (curVal <= repsList[k]) {
                            dptsNbrSize[i][k] = j;
                            isDense[i][k] = true;
                            k++;
                            if (k > repsList.length - 1) { // computed for all, stop now
                                lastDensePos = k - 1;
                                doneFlag = true;
                                break;
                            }
                            if (repsList[k] < nepsr) { // check if ball too small for this reps
                                lastDensePos = k - 1;
                                doneFlag = true;
                                break;
                            }
                        }
                        if (doneFlag == true) {
                            break;
                        }
                    }
                    // set remainder nbrhood sizes to -1
                    // nbrhood not needed since pt not dense for these reps values
                    for (int j = lastDensePos + 1; j < repsList.length; j++) {
                        dptsNbrSize[i][j] = -1;
                    }

                    // also save the nbrs now sorted nbrs indexes for the i^th point
                    // note that the numSorted^th point is not a real nbr as it is outside
                    // the bound of the maxreps
                    dptsNbrs[i] = new int[lastValidNbr];
                    for (int j = 0; j < lastValidNbr; j++) {
                        int val = rowIdx[numPt - j - 1];
                        dptsNbrs[i][j] = val;
                    }
                    if (debugFlag > 0) {
                        avgNbrSize = avgNbrSize + lastValidNbr;
                    }
                } else {
                    // not a dense point even in first shaving iteration, so no need
                    // to store nbrs or their sizes for each reps
                    dptsNbrs[i] = null;
                    dptsNbrSize[i] = null;
                }

                if (debugFlag > 0) {
                    if ((i + 1) % debugWidth == 0) {
                        System.out.println("Processed " + i + " out of " + numPt
                                + " rows...");
                    }
                }
            }

            fi.close();
            fo.close();

            if (debugFlag > 0) {
                System.out.println("Average nbrhood size: "
                        + Math.round(avgNbrSize / denseCnt));
            }

            // delete scratch file, not needed any more
            File scFile = new File(scratchFile);
            boolean success = scFile.delete();
            if (success == false) {
                System.err.println("Could not delete scratch file: " + scratchFile);
                return;
            } else // now delete the scratch file by making it zero bytes
             if (debugFlag > 0) {
                    System.out.println("Deleting scratch file: " + scratchFile);
                }
        } catch (IOException e) {
            System.err.println("Unable to open this file for reading: " + scratchFile);
            return;
        }

        // make sure the dense sizes stored are in sync with actuall dense found
        validateDenseSizes();
    }

    // creates a temporary distance file with sorted neps^th nearest neihbors, heaps for each row
    // and also the reps and the corresponding column of dense points are identified and saved
    protected void createScratchFileFromDistFile(String fileIn, int numLine,
            int neps, double fshave,
            boolean onlyDS, String delimIn,
            int debugFlag) {

        LineNumberReader fLin = null;

        // open the distance matrix file and read line by line, in a buffered manner
        try {
            fLin = new LineNumberReader(new FileReader(fileIn), DISC_BUFFER);
        } catch (IOException e) {
            System.err.println("Unable to open distance file " + fileIn
                    + " for reading.");
            return;
        }

        String element = null;

        // temporary scratch distance file
        String scratchFile = ModelUtil.removeExtension(fileIn) + ".scratch";

        if (debugFlag > 0) {
            System.out.println("Creating scratch file " + scratchFile
                    + "\n from distance matrix file " + fileIn);
            System.out.println(
                    "Scratch file will contain heaped matrix rows with sorted " + neps
                    + " closest nbrs...");
        }

        // now open the scratch file for writing the dist. matrix rows
        // with only the first neps elements sorted
        DataOutputStream fo = null;

        int debugWidth = ModelUtil.getDebugWidth(numLine, 500, 10000);

        try {
            fo = new DataOutputStream(new BufferedOutputStream(new FileOutputStream(scratchFile), DISC_BUFFER));

            // FIRST PIECE OF INFO STORED IN SCRATCH FILE. ALLOWS READY FILES
            // TO OPTIONALLY BE TREATED AS READY FILES
            // this tells us whether the scratch file contains only neps sorting
            // or variable sorting for each row. If variable, the sorted length is
            // then read. If constant, sorted length assumed to be neps. Scratch files
            // created from scratch are always false, while for those coming from recycled
            // old Ready file, this value is true. This helps i reading rows of scratch
            // file correctly by function createReadyIndexFromScratch()
            boolean variableSorting = false;
            fo.writeBoolean(variableSorting);

            // save the neps that is being used
            fo.writeInt(neps);

            // no. of densest points to cluster for the largest possible clustering
            // in the HDS hierarchy
            int denseCnt = Math.round(numLine * (1 - (float) fshave));

            // shaving fraction
            fo.writeDouble(fshave);

            nepsColVal = new double[numLine];
            nepsColIdx = new int[numLine];

            double[] row = new double[numLine];
            int[] rowIdx = new int[numLine];

            long tic = (new Date()).getTime();

            String buffer = new String("");
            StringTokenizer st = null;
            for (int i = 0; i < numLine; i++) {
                buffer = fLin.readLine();
                if (buffer.trim().length() > 0) { // a non-empty line
                    // parse the numbers
                    st = new StringTokenizer(buffer, delimIn);
                }
                int j = 0;
                while (st.hasMoreTokens()) {
                    try {
                        element = st.nextToken();
                        row[j] = Double.parseDouble(element);
                        rowIdx[j] = j;
                        j++;
                    } catch (NumberFormatException e) {
                        System.out.println("Error parsing row " + i + " column " + j);
                        System.out.println("Not a valid number: " + element);
                        return;
                    }
                }
                // find the first neps neihbors of this point
                // by sorting first neps elements : CUSTOM SORTING FUNCTION :-)
                HeapSort.partIdxSort(row, rowIdx, neps);

                // index of the neps^th nbr, that is stored ass-backward at the end
                int nepsLastIdx = rowIdx[numLine - neps];

                // save the neps^th neihbor's point distance for this point
                nepsColIdx[i] = i;
                nepsColVal[i] = row[nepsLastIdx];

                // now save the partially sorted row and index to disk in a
                // serialized manner for further sorting later
                for (int k = 0; k < numLine; k++) {
                    fo.writeDouble(row[k]);
                    fo.writeInt(rowIdx[k]);
                }

                if (debugFlag > 0) {
                    if ((i + 1) % debugWidth == 0) {
                        System.out.println("Sorted " + i + " out of " + numLine
                                + " rows...");
                    }
                }
            }

            // find the densest points, and their order by neps nbrs radius
            HeapSort.partIdxSort(nepsColVal, nepsColIdx, denseCnt);

            // compute the index of the ordered densest points, presists in memory
            denseIdx = HeapSort.extractTopNeps(nepsColIdx, denseCnt);

            // now compute max reps as the least dense point's neps radius among all the
            // dense points. persisted in memory
            maxreps = nepsColVal[denseIdx[denseCnt - 1]];

            if (debugFlag > 1) {
                System.out.println("Max reps= " + maxreps + " for clustering "
                        + denseCnt
                        + " out of " + numLine + " points.");

                System.out.println("Densest points and their neps ball rads:");
                for (int j = 0; j < 10; j++) {
                    System.out.println("[" + denseIdx[j] + "]="
                            + nepsColVal[denseIdx[j]]);
                }
                long toc = (new Date()).getTime();
                System.out.println("Parsing+Sorting=" + (toc - tic) + " millsecs");
            }

            // done with the scratch file
            fo.close();
            fLin.close();
        } catch (IOException e) {
            System.err.println("Unable to open this file for writing: " + scratchFile);
            return;
        }
    }

    // Same as createScratchFileFromDistFile except can do the same from a vector-space data file
    // with each point represented by a row of features. Thus does not need a distance matrix as input
    // USES the Euclidean distance measure
    protected boolean createScratchFileFromSpaceFile(String fileIn, int numLine,
            int numCol, int neps,
            double fshave, boolean onlyDS,
            String delimIn, int debugFlag) {
        boolean retVal = true;

        // Select the valid feature columns to be used for distance matrix computations
        int[] useColIdx = null;
        int numDim = numCol;
        int numPt = numLine;

        int debugWidth = ModelUtil.getDebugWidth(numPt, 500, 10000);

        if (skipFirstDataLine == true) {
            numPt = numLine - 1;
        }

        if (classColIdx != -1) { // if class label column is present
            if (classColIdx > numCol - 1) {
                retVal = false;
                System.err.println("Class column index " + classColIdx + " invalid");
                System.err.println("Has to be between 0 and " + (numCol - 1));
            }
            useColIdx = new int[numCol - 1];
            for (int j = 0; j < classColIdx; j++) {
                useColIdx[j] = j;
            }
            for (int j = classColIdx + 1; j < numCol; j++) {
                useColIdx[j - 1] = j;
            }
            // one less since class column ignored
            numDim = numCol - 1;
        } else {
            useColIdx = new int[numCol];
            for (int j = 0; j < numCol; j++) {
                useColIdx[j] = j;
            }
        }

        // vector data
        double[][] vdata = new double[numPt][numDim];

        if (classColIdx != -1) // class column idx is available, load it also then
        {
            ptClassLabel = new int[numPt];
        }

        // temporary scratch distance file
        String scratchFile = ModelUtil.removeExtension(fileIn) + ".scratch";

        if (debugFlag > 0) {
            System.out.println("Using " + distPrintName[MEASURE]
                    + " distance on data file with " + numPt + " points in "
                    + numDim + " dimensions...");
            System.out.println("Creating scratch file " + scratchFile
                    + "\n from data file " + fileIn);
            System.out.println(
                    "Scratch file will contain heaped distance matrix rows with sorted "
                    + neps + " closest nbrs...");
        }

        System.out.println("Reading vector data...");

        // open the distance matrix file and read line by line, in a buffered manner
        // assumes first line contains variable names, and skips it
        try {
            retVal = ModelUtil.readVectorDoubleData(fileIn, numPt, numCol, useColIdx, ptClassLabel, classColIdx, delimIn,
                    vdata, true, DISC_BUFFER, debugWidth,
                    debugFlag);
            if (retVal == false) {
                return retVal;
            }

            if (classColIdx != -1) {
                // now extract the unique class label values and store it also
                classlabels = ModelUtil.uniqueInt(ptClassLabel);
            }
        } catch (IOException e) {
            System.err.println("Unable to open data file " + fileIn + " for reading.");
            return false;
        }

        // we need to rescale data for computing distances if the distance measures
        // are Diver.COSINE or Diver.PEARSON
        double rowMean = 0, rowVar = 0;

        if (MEASURE == Diver.PEARSON) {
            // z-score each data point individually across dimensions
            for (int i = 0; i < numPt; i++) {
                rowMean = 0;
                // compute row mean
                for (int j = 0; j < numDim; j++) {
                    rowMean = rowMean + vdata[i][j];
                }
                rowMean = rowMean / numDim;
                rowVar = 0;
                // subtract row mean and compute row variance
                for (int j = 0; j < numDim; j++) {
                    // subtract row mean from data
                    vdata[i][j] = vdata[i][j] - rowMean;
                    rowVar = rowVar + Math.pow(vdata[i][j], 2);
                }
                // normalized variance (d-1 based)
                rowVar = rowVar / (numDim - 1);
                // now normalize row by variance
                for (int j = 0; j < numDim; j++) {
                    // normalize by variance now
                    if (rowVar > 0) // make sure no division by zero
                    {
                        vdata[i][j] = vdata[i][j] / rowVar;
                    } else {
                        System.out.println("Error: Row " + (j + 1) + " is all zero, Pearson distance cannot be defined!");
                    }
                }

                if (debugFlag > 0) {
                    if ((i + 1) % debugWidth == 0) {
                        System.out.println("z-scored " + i + " out of " + numPt
                                + " data points...");
                    }
                }
            }
        }

        double l2norm = 0;
        if (MEASURE == Diver.COSINE) {
            for (int i = 0; i < numPt; i++) {
                l2norm = 0;
                // compute row l2norm
                for (int j = 0; j < numDim; j++) {
                    l2norm = l2norm + Math.pow(vdata[i][j], 2);
                }
                l2norm = Math.pow(l2norm, 0.5);
                // now normalize row data by it's l2norm
                for (int j = 0; j < numDim; j++) {
                    // normalize by l2-norm
                    vdata[i][j] = vdata[i][j] / l2norm;
                }
                if (debugFlag > 0) {
                    if ((i + 1) % debugWidth == 0) {
                        System.out.println("Variance normalized " + i + " out of " + numPt
                                + " data points...");
                    }
                }
            }
        }

        // AT THE END OF THIS PROCESS, IF WE NOW COMPUTE Sq. Euclidean distance
        // BETWEEN TRANSFORMED DATA ABOVE, WE WILL GET Pearson, Cosine or Sq. Euclidean
        // Distance between points, except for a final normalization of 2(d-1) required for
        // Pearson.
        // now open the scratch file for writing the dist. matrix rows
        // with only the first neps elements sorted
        DataOutputStream fo = null;

        try {
            fo = new DataOutputStream(new BufferedOutputStream(new FileOutputStream(scratchFile), DISC_BUFFER));

            // FIRST PIECE OF INFO STORED IN SCRATCH FILE. ALLOWS READY FILES
            // TO OPTIONALLY BE TREATED AS READY FILES
            // this tells us whether the scratch file contains only neps sorting
            // or variable sorting for each row. If variable, the sorted length is
            // then read. If constant, sorted length assumed to be neps. Scratch files
            // created from scratch are always false, while for those coming from recycled
            // old Ready file, this value is true. This helps i reading rows of scratch
            // file correctly by function createReadyIndexFromScratch()
            boolean variableSorting = false;
            fo.writeBoolean(variableSorting);

            // save the neps that is being used
            fo.writeInt(neps);

            // no. of densest points to cluster for the largest possible clustering
            // in the HDS hierarchy
            int denseCnt = Math.round(numPt * (1 - (float) fshave));

            // shaving fraction
            fo.writeDouble(fshave);

            nepsColVal = new double[numPt];
            nepsColIdx = new int[numPt];

            double[] dataRow = new double[numDim];

            double[] row = new double[numPt];
            int[] rowIdx = new int[numPt];

            long tic = (new Date()).getTime();

            String buffer = new String("");
            StringTokenizer st = null;

            debugWidth = ModelUtil.getDebugWidth(numPt, 5, 10);

            for (int i = 0; i < numPt; i++) {

                // now compute the distance for this point
                row = computeSqEucDistance(vdata, i);

                // normalize by 2(d-1) to get Pearson Distance
                // note we normalized vdata for Pearson and Cosine earlier
                // so computing sq. euclidean actually gives Pearson and Cosine directly
                if (MEASURE == Diver.PEARSON) {
                    for (int j = 0; j < numPt; j++) {
                        row[j] = row[j] / ((double) (2 * (numCol - 1)));
                    }
                }
                // initialize row indexes, needed for sorting
                for (int j = 0; j < numPt; j++) {
                    rowIdx[j] = j;
                }

                // find the first neps neihbors of this point
                // by sorting first neps elements : CUSTOM SORTING FUNCTION :-)
                HeapSort.partIdxSort(row, rowIdx, neps);

                // index of the neps^th nbr, that is stored ass-backward at the end
                int nepsLastIdx = rowIdx[numPt - neps];

                // save the neps^th neihbor's point distance for this point
                nepsColIdx[i] = i;
                nepsColVal[i] = row[nepsLastIdx];

                // now save the partially sorted row and index to disk in a serialized manner
                // for further sorting later
                for (int k = 0; k < numPt; k++) {
                    fo.writeDouble(row[k]);
                    fo.writeInt(rowIdx[k]);
                }

                if (debugFlag > 0) {
                    if ((i + 1) % debugWidth == 0) {
                        System.out.println("Computed distance, sorted " + i + " out of "
                                + numPt + " rows...");
                    }
                }
            }

            // find the densest points, and their order by neps nbrs radius
            HeapSort.partIdxSort(nepsColVal, nepsColIdx, denseCnt);

            // compute the index of the ordered densest points, presists in memory
            denseIdx = HeapSort.extractTopNeps(nepsColIdx, denseCnt);

            // now compute max reps as the least dense point's neps radius among all the
            // dense points. persisted in memory
            maxreps = nepsColVal[denseIdx[denseCnt - 1]];

            if (debugFlag > 1) {
                System.out.println("Max reps= " + maxreps + " for clustering "
                        + denseCnt
                        + " out of " + numPt + " points.");

                System.out.println("Densest points and their neps ball rads:");
                for (int j = 0; j < 10; j++) {
                    System.out.println("[" + denseIdx[j] + "]="
                            + nepsColVal[denseIdx[j]]);
                }
                long toc = (new Date()).getTime();
                System.out.println("Parsing+Sorting=" + (toc - tic) + " millsecs");
            }
            // done with the scratch file
            fo.close();

            // also save the class label data just extracted
            saveClassLabelData(fileIn, debugFlag);
        } catch (IOException e) {
            System.err.println("Unable to open this file for writing: " + scratchFile);
            return false;
        }
        return retVal;
    }

    // computes Auto-HDS /HMA tree from HDS tree by merging labels
    // returns true on success
    protected boolean computeAutoHDS(int runtSize, String fileIn, double rshave) {
        System.out.println("Computing Auto-HDS for runtSize of " + runtSize);
        boolean retVal = true;

        int numPt = isDense.length;

        int numiter = denseSizeList.length; // no of. distinct clustering iterations
        hmaLabels = new int[numPt][numiter]; //assume all Java initialized to 0

        // go from left to right
        boolean nobreakup = true;

        // no. of multi-level HMA clusters found
        // they start with the number of unique clusters we have at the first
        // level (since our HDS hierarch is compacted, it is already labeled 1 to 3
        // e.g. at first level when there are 3 clusters
        numHMAClusters = numClusters[0];

        // copy first row from hds label to hma label since they will be the same
        for (int i = 0; i < numPt; i++) {
            hmaLabels[i][0] = hdsLabels[i][0];
        }

        lastNonEmptyHMALevel = numiter - 1;
        // now propagate the rest
        for (int j = 0; j < numiter - 1; j++) {
            // compute the number of dense non-runt points in last level
            int denseCnt = 0;
            for (int i = 0; i < numPt; i++) {
                if (hmaLabels[i][j] > 0) // isDense[i][j] will not work because we need to ignore pts that are runt in last level
                {
                    denseCnt = denseCnt + 1;
                }
            }

            int[] denseIdxList = new int[denseCnt];
            int[] hmaCurLabelList = new int[denseCnt];
            int[] hdsNextLabelList = new int[denseCnt];

            int pos = 0;
            for (int i = 0; i < numPt; i++) {
                if (hmaLabels[i][j] > 0) // isDense[i][j] will not work because we need to ignore pts that are runt in last level
                {
                    denseIdxList[pos] = i;
                    hmaCurLabelList[pos] = hmaLabels[i][j];
                    hdsNextLabelList[pos] = hdsLabels[i][j + 1];
                    pos++;
                }
            }

            if (j == 0) {
                // process first level for all unique non-zero cluster labels
                hmaBaseLevels = new Vector<Integer>(20);
                int[] firstBaseLabels = ModelUtil.uniqueInt(hmaCurLabelList);
                // ensure ordered list of labels
                Arrays.sort(firstBaseLabels);
                for (int i = 0; i < firstBaseLabels.length; i++) {
                    if (firstBaseLabels[i] != 0) {
                        // all these hma clusters start at level 0
                        hmaBaseLevels.add(new Integer(0));
                    }
                }
            }

            // number of nonrunt clusters from last step
            int[] nonRuntj = ModelUtil.uniqueInt(hmaCurLabelList);
            int numjClusters = nonRuntj.length;

            if (numjClusters == 0) {
                lastNonEmptyHMALevel = j - 1;
                break;
            }

            // if there is only one cluster, simple to do this, also no runt could have occured until nobreakup==false
            if ((numClusters[j] == 1) && (numClusters[j + 1] == 1) && (nobreakup)) {
                for (int i = 0; i < denseCnt; i++) {
                    if (hdsLabels[denseIdxList[i]][j + 1] > 0) // dense in next level
                    {
                        hmaLabels[denseIdxList[i]][j + 1] = 1;
                    }
                }
            } else // relabeling with runt check
            {
                if (nobreakup == true) {
                    nobreakup = false; // clusters have split
                }

                int[] labelList = new int[numjClusters];
                Vector<Integer[]> clusterIdxList = new Vector<Integer[]>(numjClusters);

                ModelUtil.histogram(hmaCurLabelList, numjClusters, labelList, clusterIdxList);

                // for each cluster
                for (int k = 0; k < numjClusters; k++) {
                    // for all the points in the cluster
                    Integer[] idxList = clusterIdxList.get(k);
                    // find their labels and sizes in the next level
                    int[] nextLevelCLabels = new int[idxList.length];

                    for (int i = 0; i < idxList.length; i++) {
                        nextLevelCLabels[i] = hdsNextLabelList[idxList[i]];
                    }
                    // now enumerate all unique subclusters in the next level of this cluster
                    int[] subTotCList = ModelUtil.uniqueInt(nextLevelCLabels);
                    int numTotC = subTotCList.length;
                    int numSubC = numTotC;

                    // find the number of non-0 subcluster labels
                    for (int i = 0; i < numTotC; i++) {
                        if (subTotCList[i] == 0) {
                            numSubC = numSubC - 1;
                            break;
                        }
                    }

                    if (numSubC > 1) {
                        int[] sublabelList = new int[numTotC];
                        Vector<Integer[]> subclusterIdxList = new Vector<Integer[]>(numTotC);
                        ModelUtil.histogram(nextLevelCLabels, numTotC, subTotCList, subclusterIdxList);

                        // find the list of non-runt sub-clusters, also excluding the 0 id subset
                        Vector<Integer> nonRuntSubLabelIdx = new Vector<Integer>(numSubC);
                        for (int i = 0; i < numTotC; i++) {
                            // check if current subcluster is non-zero AND is bigger than runt size
                            if ((subclusterIdxList.get(i).length > runtSize) && (subTotCList[i] != 0)) {
                                nonRuntSubLabelIdx.add(new Integer(i));
                            }
                        }

                        int numNonRuntStableLabelIdx = nonRuntSubLabelIdx.size();
                        // now check to see if more than one subcluster found larger than runt size

                        if (numNonRuntStableLabelIdx > 1) {
                            // each of those non-runt clusters are new HMA clusters, and should be
                            // labeled as such

                            for (int m = 0; m < numNonRuntStableLabelIdx; m++) {
                                Integer[] subcidx = subclusterIdxList.get(nonRuntSubLabelIdx.get(m).intValue());
                                numHMAClusters = numHMAClusters + 1;
                                for (int p = 0; p < subcidx.length; p++) {
                                    hmaLabels[denseIdxList[idxList[subcidx[p].intValue()]]][j + 1] = numHMAClusters;
                                }
                                hmaBaseLevels.add(numHMAClusters - 1, (new Integer(j + 1))); // store the level where this cluster starts
                            }
                        } else {
                            // only one non-runt sub-cluster found propagate its
                            // member point labels to next level, ignoring all particle/runt related subclusters

                            for (int m = 0; m < numNonRuntStableLabelIdx; m++) {
                                Integer[] subcidx = subclusterIdxList.get(nonRuntSubLabelIdx.get(m).intValue());
                                for (int p = 0; p < subcidx.length; p++) {
                                    hmaLabels[denseIdxList[idxList[subcidx[p].intValue()]]][j + 1] = labelList[k];
                                }
                            }
                        }
                    } else // propagate current label of this cluster to next level dense children
                    {
                        for (int i = 0; i < idxList.length; i++) {
                            if (hdsLabels[denseIdxList[idxList[i]]][j + 1] > 0) // dense in next level
                            {
                                hmaLabels[denseIdxList[idxList[i]]][j + 1] = labelList[k];
                            }
                        }
                    }
                }
            }
        }

        //save the AutoHDS results for later reuse by another run
//      saveAutoHDSData(fileIn, 1);
        // characterizes HMA Base clusters
        characterizeHMABaseClusters(fileIn, rshave, 1);

        return retVal;
    }

    // computes the base clusters of HMA and count no. of points of various classes
    // if available
    private void characterizeHMABaseClusters(String fileIn, double rshave, int debugFlag) {
        // load the class label data if it is not loaded yet, and is available
        if (classlabels == null) {
            boolean status = loadClassLabelData(fileIn, debugFlag);
            if (status == false) // load failed
            {
                if (classColIdx != -1) {
                    System.err.println("No class label information found, for class column" + classColIdx);
                    System.out.println("Class labels info will not be generated.");
                    classColIdx = -1;
                }
                classlabels = null;
            }
        }

        hmaBaseMembers = new Vector<Integer[]>(numHMAClusters);
        hmaClusterSize = new int[numHMAClusters];
        int numClasses = -1;
        if (classlabels != null) {
            numClasses = classlabels.length;
            hmaBaseLabels = new int[numHMAClusters][numClasses];
        }
        int numPt = isDense.length;
        // for each hma base cluster find the first level at which it occurs
        for (int j = 0; j < numHMAClusters; j++) {
            int label = j + 1;
            int startLevel = hmaBaseLevels.get(j); // level of (j+1)^th cluster

            // now find all the indices of pts with hma label j+1 at startLevel
            Vector<Integer> curList = new Vector<Integer>(1000);
            for (int i = 0; i < numPt; i++) {
                if (hmaLabels[i][startLevel] == label) {
                    curList.add(new Integer(i));
                }
            }
            // no. of elements in this HMA cluster
            hmaClusterSize[j] = curList.size();
            // now recover the indices and the no. of such points found
            Integer[] idxList = new Integer[hmaClusterSize[j]];
            curList.toArray(idxList);
            hmaBaseMembers.add(idxList);
            // now find the distribution of class labels for this cluster
            for (int i = 0; i < idxList.length; i++) {
                for (int k = 0; k < numClasses; k++) {
                    if (ptClassLabel[idxList[i]] == classlabels[k]) {
                        hmaBaseLabels[j][k] = hmaBaseLabels[j][k] + 1;
                    }
                }
            }
        }

        // other quantities required for cluster ranking etc.
        computeClusterStabilityAndRanks(rshave);

        // also find the first index in the sorted list for each cluster
        // needed by GUI plotter for panning and zooming to clusters
        firstClusterIndex = new int[numHMAClusters];
        for (int i = 0; i < numHMAClusters; i++) {
            firstClusterIndex[i] = -1;
        }
        // now scan each row of the hdsLabels to locate first positions
        // of each of the clusters
        int numCol = denseSizeList.length;
        for (int i = 0; i < numPt; i++) {
            int idx = sortedTreeIdx[i]; // go to next topmost point/row
            for (int j = 0; j < numCol; j++) // scan the labels in the row
            {
                int foundLabel = hmaLabels[idx][j];
                if (foundLabel > 0) //dense label found
                {
                    if (firstClusterIndex[foundLabel - 1] == -1) // cluster not found yet
                    {
                        firstClusterIndex[foundLabel - 1] = i; // i^th top row is where this cluster first occurs
                    }
                    // else found already - this is not the smallest row any more for that cluster
                }
            }
        }
    }

    // computes the stability of the hma clusters and their rankings
    protected void computeClusterStabilityAndRanks(double rshave) {
        // compute the peak levels and stability of each hma cluster
        int numLevels = isDense[0].length;
           
        int numPt = isDense.length;

        // allocate space for the things we are computing
        hmaPeakLevels = new int[numHMAClusters];
        clusterStability = new double[numHMAClusters];
        clusterRankOrder = new int[numHMAClusters];

        for (int i = 0; i < numHMAClusters; i++) {
            Integer[] memberList = hmaBaseMembers.get(i);
            // now find the densest point in this cluster
            // this is where the last point will appear
            int hmaclustLabel = i + 1;
            int baseLevel = hmaBaseLevels.get(i);
            int peakLevel = baseLevel;

            for (int j = 0; j < memberList.length; j++) {
                // count the last level where present, starting from the
                // base level
                for (int k = baseLevel; k < numLevels; k++) {
                    if (hmaLabels[memberList[j]][k] == hmaclustLabel) {
                        if (k > peakLevel) {
                            peakLevel = k;
                        }
                    } else {
                        break; // done checking on this point
                    }
                }
            }
            hmaPeakLevels[i] = peakLevel;

            double logBaseLevel = 0.0, logPeakLevel = 0.0;
            double baseLevelFraction = 0.0;
        
            // we are looking up log of no. of dense points just before the start level
            if (baseLevel > 0) {
                baseLevelFraction = (double) denseSizeList[baseLevel - 1]/(double)numPt;
            }
            else 
            {
                // if the start level is first level previous level is a virtual 
                // level with more points than 100% to get consistent stability                
                baseLevelFraction = (double) denseSizeList[baseLevel]/(double)numPt / (1.0 - rshave);
            }
                                        
            
            double peakLevelFraction = (double) denseSizeList[peakLevel]/numPt;
        
            // log of no. of points at the last level it appears
            logBaseLevel = Math.log(baseLevelFraction);
            logPeakLevel = Math.log(peakLevelFraction);            
            
            // as of 2019, we decide to compute absolute stability that does not vary
            // with shaving rate. so by putting 0.01 for r_shave here we always get
            // stability in terms of a standard shaving rate regardless of how fast you shave
            // and shaving rate is now just used for speedups
            clusterStability[i] = (logPeakLevel - logBaseLevel) / Math.log(0.99);
//         System.out.println(clusterStability[i]);
//         System.out.println("baseLevel "+baseLevel);
//         System.out.println("peakLevel "+peakLevel);
        }

        // now sort the clusters by stability and store their ranking index
        // biggest items get stored in front, so thats all that is needed.
        for (int i = 0; i < numHMAClusters; i++) // create sorting index
        {
            clusterRankOrder[i] = i;
        }
        HeapSort.idxSort(clusterStability, clusterRankOrder);
    }

    // generates Auto-HDS tree from the nearest nbrs already computed
    protected void computeHDSTreeSmart(String fileIn, int debugFlag) {
        int[] ptIdxList = null;
        int numPt = isDense.length;

        int numiter = denseSizeList.length; // no of. distinct clustering iterations
        // initialize the the raw cluster tree container, each column having one clustering
        hdsLabels = new int[numPt][numiter]; // JIA

        // for storing cluster count
        numClusters = new int[numiter];

        int[] tmpLabels = new int[numPt];

        long tic = (new Date()).getTime();

        if (numiter < 1) {
            System.out.println("Nothing to cluster");
            return;
        }

        // generated list of dense points in first iteration
        int cdenseCnt = denseSizeList[numiter - 1];
        ptIdxList = new int[cdenseCnt];
        int ctr = 0;
        for (int i = 0; i < numPt; i++) {
            if (isDense[i][numiter - 1]) {
                ptIdxList[ctr] = i;
                ctr++;
            }
        }

        // now propagate labels for all these points
        propagateLabels(numiter - 1, ptIdxList, cdenseCnt, 0);
        // now compact the clusters
        numClusters[numiter - 1] = relabelClusters(numiter - 1);

        if (debugFlag > 0) {
            System.out.println(numClusters[numiter - 1] + " clusters found at level " + (numiter - 1)
                    + ",num clustered = " + cdenseCnt);
        }
        // now reuse and iterate smartly for the remaining levels
        boolean[] updateNeededFlag = new boolean[numPt];

        // generated list of dense points in this iteration
        for (int j = (numiter - 2); j >= 0; j--) {
            // find the set of all the new dense pts
            for (int i = 0; i < numPt; i++) {
                if (isDense[i][j] == false) // pts not dense at this level
                {
                    updateNeededFlag[i] = false;
                } else {
                    // check if this point was not dense in the last level
                    // then we need to propagate it
                    if (isDense[i][j + 1] == false) {
                        updateNeededFlag[i] = true;
                        // If first time dense, then all dense nbrs need to be propagated
                        for (int k = 0; k < dptsNbrSize[i][j]; k++) {
                            int idx = dptsNbrs[i][k];
                            if (isDense[idx][j]) {
                                updateNeededFlag[idx] = true;
                            }
                        }
                    } else {
                        // find the new nbrs of this dense pt, all of them need
                        // to be propagated.
                        for (int k = dptsNbrSize[i][j + 1]; k < dptsNbrSize[i][j]; k++) {
                            int idx = dptsNbrs[i][k];
                            if (isDense[idx][j]) {
                                updateNeededFlag[idx] = true;
                            }
                        }
                    }

                    // also, for all dense points, copy the labels of last level onto
                    // the current one to prepare them for incremental update
                    // don't need to copy non-dense as hdsLabels are for non-dense are already
                    hdsLabels[i][j] = hdsLabels[i][j + 1];
                }
            }
            // now extract all the pts idx that need update. Made of either newly
            // dense pts, or new nbrs as compared to last iteration
            int updateCnt = 0;
            for (int i = 0; i < numPt; i++) {
                if (updateNeededFlag[i]) {
                    updateCnt++;
                }
            }
            ptIdxList = new int[updateCnt];
            ctr = 0;
            for (int i = 0; i < numPt; i++) {
                if (updateNeededFlag[i]) {
                    ptIdxList[ctr] = i;
                    ctr++;
                }
            }

            // now propagate labels for all these points
            propagateLabels(j, ptIdxList, denseSizeList[j] * 2, numClusters[j + 1]);

            // now compact the clusters
            numClusters[j] = relabelClusters(j);

            if (debugFlag > 0) {
                System.out.println(numClusters[j] + " clusters found at level " + j
                        + ",num clustered = " + denseSizeList[j]);
            }
        }

        if (debugFlag > 0) {
            long toc = (new Date()).getTime();
            System.out.println("Recursive tree construction time=" + (toc - tic)
                    + " millsecs");
        }
    }

    // perform HDS on each level separately
    protected void computeHDSTree(String fileIn, int debugFlag) {
        int[] ptIdxList = null;
        int numPt = isDense.length;

        int numiter = denseSizeList.length; // no of. distinct clustering iterations
        // initialize the the raw cluster tree container, each column having one clustering
        hdsLabels = new int[numPt][numiter]; // JIA

        // for storing cluster count
        numClusters = new int[numiter];

        int[] tmpLabels = new int[numPt];

        long tic = (new Date()).getTime();

        for (int j = 0; j < numiter; j++) {
            // generated list of dense points in this iteration
            int cdenseCnt = denseSizeList[j];
            ptIdxList = new int[cdenseCnt];
            int ctr = 0;
            for (int i = 0; i < numPt; i++) {
                if (isDense[i][j]) {
                    ptIdxList[ctr] = i;
                    ctr++;
                }
            }

            // now propagate labels for all these points
            propagateLabels(j, ptIdxList, denseSizeList[j], 0);
            // now compact the clusters
            numClusters[j] = relabelClusters(j);
            if (debugFlag > 0) {
                System.out.println(numClusters[j] + " clusters found at level " + j
                        + ",num clustered = " + denseSizeList[j]);
            }
        }

        if (debugFlag > 0) {
            long toc = (new Date()).getTime();
            System.out.println("Brute force tree construction time=" + (toc - tic)
                    + " millsecs");
        }
    }

    // loads class-label related data saved earlier
    protected boolean loadClassLabelData(String fileIn, int debugFlag) {
        boolean retVal = true;
        int numPt = isDense.length;
        String classLabelFile = ModelUtil.removeExtension(fileIn) + "_class.info";

        if (debugFlag > 0) {
            System.out.println("Loading class-label data from file " + classLabelFile);
        }
        DataInputStream fi = null;
        try {
            fi = new DataInputStream(new BufferedInputStream(new FileInputStream(classLabelFile), DISC_BUFFER));

            classColIdx = fi.readInt();
            ptClassLabel = new int[numPt];
            for (int i = 0; i < numPt; i++) {
                ptClassLabel[i] = fi.readInt();
            }
            int numClasses = fi.readInt();
            classlabels = new int[numClasses];
            for (int i = 0; i < numClasses; i++) {
                classlabels[i] = fi.readInt();
            }
            fi.close();
        } catch (IOException e) {
            retVal = false;
        }
        return retVal;
    }

    protected boolean saveClassLabelData(String fileIn, int debugFlag) {
        if (classColIdx == -1) {
            System.err.println("No class label data to save");
            return false;
        }

        boolean retVal = true;
        int numPt = ptClassLabel.length;
        String classLabelFile = ModelUtil.removeExtension(fileIn) + "_class.info";

        if (debugFlag > 0) {
            System.out.println("Saving class-label data into file " + classLabelFile);
        }
        DataOutputStream fo = null;
        try {
            fo = new DataOutputStream(new BufferedOutputStream(new FileOutputStream(classLabelFile), DISC_BUFFER));
            fo.writeInt(classColIdx);

            for (int i = 0; i < numPt; i++) {
                fo.writeInt(ptClassLabel[i]);
            }
            if (classlabels == null) {
                System.err.println("Class labels missing though class column is " + classColIdx);
                retVal = false;
            } else {
                int numClasses = classlabels.length;
                fo.writeInt(numClasses);
                for (int i = 0; i < numClasses; i++) {
                    fo.writeInt(classlabels[i]);
                }
            }
            fo.close();
        } catch (IOException e) {
            retVal = false;
        }
        return retVal;
    }

    protected boolean regenerateBinInfoFile(String fileIn, boolean graphData, String [] ptDescription) {
        boolean retVal = true;

        // point description to index mapping
        HashMap<String,Integer> ptDescMapping = new HashMap<String,Integer>(ptDescription.length);
        
        for (int i =0; i< ptDescription.length; i++)
        {
            ptDescMapping.put(ptDescription[i].trim(), i);
        }
        
        // read other files to use the data to regenerate the binary info file        
        String sortedIdxFile = ModelUtil.removeExtension(fileIn) + "_sorted.idx";

        String rawHdsFile = ModelUtil.removeExtension(fileIn) + ".hds";

        // regenerate this binary file
        String hdsDataFile = ModelUtil.removeExtension(fileIn) + "_hds.info";

        // tempoarary data in memory to be converted
        int numPt = ModelUtil.getNumLines(sortedIdxFile);

        // read cluster label data into memory if found as a special file called
        // graph_cluster_labels.txt        
        String graphClusterLabelsFile = ModelUtil.removeExtension(fileIn) + "_cluster_labels.txt";
        File gCF = (new File(graphClusterLabelsFile));
        if (gCF.exists()) {
            this.ptClassLabel = new int[numPt];
            // force default label to be 0 or background 
            String[] clusterPtLabelsStr = ModelUtil.readFileIntoArray(graphClusterLabelsFile, numPt, true);
            for (int i = 0; i < numPt; i++) {
                this.ptClassLabel[i] = 0;
            }
            for (int i = 0; i < clusterPtLabelsStr.length; i++) {
                String pointStr = clusterPtLabelsStr[i];
                String[] labelParts = pointStr.split(",");
                if (labelParts.length != 2) {
                    System.out.println("At line number  " + i);
                    System.out.println("Could not parse cluster label file " + graphClusterLabelsFile);
                    retVal = false;
                    break;
                }
                String ptId = labelParts[0];
                int classLabel = Integer.parseInt(labelParts[1]);

                int ptIdx = ptDescMapping.get(ptId);

                if ((ptIdx < 0) || (ptIdx > numPt-1))
                {
                    System.out.println("At line number  " + i);
                    System.out.println("Point index " + ptIdx + " was not within number of points " + numPt + " in "+  graphClusterLabelsFile);
                    retVal = false;                    
                    break;
                }

                this.ptClassLabel[ptIdx] = classLabel;
            }

            // unique class labels
            classlabels = ModelUtil.uniqueInt(ptClassLabel);

            // set the class label index to 0 as it's a signal for rest of code that 
            // class pt label is missing normally -1
            this.classColIdx = 0;

            // now create the labels binary file for future use by the system
            this.saveClassLabelData(fileIn, 1);
        }

        int numiter = -1;
        String[] idxStr = ModelUtil.readFileIntoArray(sortedIdxFile, numPt, true);
        String[] hdsStr = ModelUtil.readFileIntoArray(rawHdsFile, numPt, true);
        // number of iterations = no. of columns in any line of raw hds row
        String[] vals = hdsStr[0].split(" ");

        if (vals.length > 0) {
            numiter = vals.length;
        } else {
            System.out.println("Could not parse file: " + rawHdsFile);
            retVal = false;
        }

        int[][] tempHdsLabels = new int[numPt][numiter];
        int[] tempSortedTreeIdx = new int[numPt];
        int i = 0, j = 0;
        try {
            for (i = 0; i < numPt; i++) {
                vals = hdsStr[i].split(" ");
                for (j = 0; j < numiter; j++) {
                    tempHdsLabels[i][j] = Integer.parseInt(vals[j]);
                }

                // the binary data is 0 indexed for this index while the .hds 
                // is 1 indexed (for historical reasons). since we are regenerating
                // bin 0 index data from 1 indexed data -1 is needed
                tempSortedTreeIdx[i] = Integer.parseInt(idxStr[i]) - 1;
            }
        } catch (NumberFormatException e) {
            System.out.println("Could not parse HDS raw label at row " + i + " column " + j + " in file " + rawHdsFile);
            System.out.println("Or, could not parse row " + i + " in file " + sortedIdxFile);
            retVal = false;
        }

        System.out.println("Regenerating HDS data for future use into binary file " + hdsDataFile);

        DataOutputStream fo = null;
        try {
            fo = new DataOutputStream(new BufferedOutputStream(new FileOutputStream(hdsDataFile), DISC_BUFFER));

            // stores information about whether the bin info saved was graph data as many
            // variables are not computed for graph HDS/HMA drawing
            fo.writeBoolean(graphData);
            fo.writeInt(numPt);
            fo.writeInt(numiter);
            // save hdsLabels, isDense           
            for (j = 0; j < numiter; j++) {
                int actualDenseSize = 0;
                Set<Integer> uniqueClusters = new HashSet<Integer>(100);
                for (i = 0; i < numPt; i++) {
                    int label = tempHdsLabels[i][j];
                    if (label != 0) {
                        actualDenseSize += 1;
                        if (!uniqueClusters.contains(label)) {
                            uniqueClusters.add(label);
                        }
                    }
                    fo.writeInt(label);
                    // is dense is basically tracking which points are dense in the matrix
                    // 0 labels by convention are non-dense
                    if (label == 0) {
                        fo.writeBoolean(false);
                    } else {
                        fo.writeBoolean(true);
                    }
                }
                // save the no. of dense points
                fo.writeInt(actualDenseSize);
                // no. of unique clusters found
                int numClusters = uniqueClusters.size();
                fo.writeInt(numClusters);
            }
            for (i = 0; i < numPt; i++) {
                fo.writeInt(tempSortedTreeIdx[i]);
            }
            fo.close();
        } catch (IOException e) {
            System.err.println("Unable to open this file for writing: " + hdsDataFile);
            return false;
        }
        return retVal;

    }

    //saves HDS related data for loading instead of recomputing next
    // time when users asks clustering with same parameters
    protected void saveHDSData(String fileIn, int debugFlag) {
        int numPt = isDense.length;
        int numiter = isDense[0].length;
        String hdsDataFile = ModelUtil.removeExtension(fileIn) + "_hds.info";
        if (debugFlag > 0) {
            System.out.println("Saving HDS data for future use in file " + hdsDataFile);
        }

        DataOutputStream fo = null;
        try {
            fo = new DataOutputStream(new BufferedOutputStream(new FileOutputStream(hdsDataFile), DISC_BUFFER));

            // we can never save this for graph data which is externally provided in
            fo.writeBoolean(false);
            fo.writeInt(numPt);
            fo.writeInt(numiter);
            // save hdsLabels, isDense, repsList, denseSizeList
            for (int j = 0; j < numiter; j++) {
                for (int i = 0; i < numPt; i++) {
                    fo.writeInt(hdsLabels[i][j]);
                    fo.writeBoolean(isDense[i][j]);
                }
                fo.writeInt(denseSizeList[j]);
                fo.writeInt(numClusters[j]);
                fo.writeDouble(repsList[j]);
            }
            for (int i = 0; i < numPt; i++) {
                fo.writeInt(sortedTreeIdx[i]);
            }
            fo.close();
        } catch (IOException e) {
            System.err.println("Unable to open this file for writing: " + hdsDataFile);
            return;
        }
    }

    //loads both HDS data. This allows us to skip HDS clustering, if the
    // clustering done last time the software was loaded was with identical
    // model parameters
    // WARNING: Make sure THIS CODE IS IN SYNC WITH saveHDSData() function above
    // WHEN MAKING ANY CHANGES.
    protected boolean loadHDSData(String fileIn, int debugFlag, boolean graphData, String [] ptDescription) {
        boolean retVal = true;
        int numPt = -1;
        int numiter = -1;
        String hdsDataFile = ModelUtil.removeExtension(fileIn) + "_hds.info";

        boolean binInfoFileFound = (new File(hdsDataFile)).exists();

        // reproduce binary info file for hds if not found from other files
        // this will only happen for graph datasets when they are loaded first time
        if (!binInfoFileFound) {
            if (graphData) {
                regenerateBinInfoFile(fileIn, true, ptDescription);
            } else {
                return false;
            }
        }

        DataInputStream fi = null;
        try {
            fi = new DataInputStream(new BufferedInputStream(new FileInputStream(hdsDataFile), DISC_BUFFER));

            boolean savedGraphData = fi.readBoolean();
            numPt = fi.readInt();
            numiter = fi.readInt();

            // load hdsLabels, isDense, repsList, denseSizeList
            hdsLabels = new int[numPt][numiter];
            isDense = new boolean[numPt][numiter];
            denseSizeList = new int[numiter];
            numClusters = new int[numiter];

            if (!savedGraphData) {
                repsList = new double[numiter];
            }
            for (int j = 0; j < numiter; j++) {
                for (int i = 0; i < numPt; i++) {
                    hdsLabels[i][j] = fi.readInt();
                    isDense[i][j] = fi.readBoolean();
                }
                denseSizeList[j] = fi.readInt();
                numClusters[j] = fi.readInt();
                if (!savedGraphData) {
                    repsList[j] = fi.readDouble();
                }
            }
            sortedTreeIdx = new int[numPt];
            for (int i = 0; i < numPt; i++) {
                sortedTreeIdx[i] = fi.readInt();
            }
            fi.close();
        } catch (IOException e) {
            retVal = false;
        }
        return retVal;
    }

    /*
   protected void saveAutoHDSData(String fileIn, int debugFlag)
   {
      int numPt= isDense.length;
      int numiter= isDense[0].length;
      String hdsDataFile = ModelUtil.removeExtension(fileIn) + "_autohds.info";
      if (debugFlag > 0)
      {
         System.out.println("Saving Auto-HDS data for future use in file " + hdsDataFile);
      }

      DataOutputStream fo = null;
      try
      {
         fo = new DataOutputStream(new BufferedOutputStream
                                (new FileOutputStream(hdsDataFile), DISC_BUFFER));

         fo.writeInt(numPt);
         fo.writeInt(numiter);
         fo.writeInt(numHMAClusters);
         // save hdsLabels, isDense, repsList, denseSizeList
         for (int j=0; j<numiter; j++)
         {
            for (int i=0; i<numPt; i++)
            {
               fo.writeInt(hmaLabels[i][j]);
            }
         }
         fo.close();
      }
      catch (IOException e)
      {
         System.err.println("Unable to open this file for writing: " + hdsDataFile);
         return;
      }
   }

   //loads both Auto-HDS data. This allows us to skip Auto-HDS clustering, if the
   // clustering done last time the software was loaded was with identical
   // model parameters
   // WARNING: Make sure THIS CODE IS IN SYNC WITH saveAutoHDSData() function above
   // WHEN MAKING ANY CHANGES.
   protected boolean loadAutoHDSData(String fileIn, int debugFlag)
   {
      boolean retVal= true;
      int numPt= -1;
      int numiter= -1;
      String hdsDataFile = ModelUtil.removeExtension(fileIn) + "_autohds.info";

      DataInputStream fi = null;
      try
      {
         fi = new DataInputStream(new BufferedInputStream
                                (new FileInputStream(hdsDataFile), DISC_BUFFER));

         numPt=fi.readInt();
         numiter= fi.readInt();
         numHMAClusters= fi.readInt();
         // load hdsLabels, isDense, repsList, denseSizeList
         hmaLabels= new int[numPt][numiter];

         for (int j=0; j<numiter; j++)
         {
            for (int i=0; i<numPt; i++)
            {
               hmaLabels[i][j]= fi.readInt();
            }
         }
         fi.close();
      }
      catch (IOException e)
      {
         retVal= false;
      }
      return retVal;
   }
     */
    //saves all the clusters generated by Auto-HDS into a file, using
    // the point id of the original set of points. Saves as a CSV file
    public void saveAutoHDSClusters(String fileIn, String[] pointDescriptions, String[] pointURLs) {
        int numPt = isDense.length;

        // now save the labeled HDS data back to an HDS tree output file
        PrintWriter pout;

        String labelFile = ModelUtil.removeExtension(fileIn) + "_lab.csv";

        try {
            pout = new PrintWriter(new FileWriter(labelFile, false));
            // labels for the columns saved

            pout.print("clusterId, stability, ptIdx");
            if (pointDescriptions == null) // point descriptions were not available
            {
                pout.println();
            } else {
                pout.println(",ptDescription");
            }

            for (int i = 0; i < numHMAClusters; i++) {
                int cidx = clusterRankOrder[i]; // process clusters in order of stability
                // get index of points in this cluster
                Integer[] memberIds = hmaBaseMembers.get(cidx);

                for (int j = 0; j < memberIds.length; j++) {
                    pout.print((cidx + 1) + ","); // cluster id
                    pout.print(clusterStability[cidx] + ",");
                    if (pointDescriptions != null) // point descriptions were not available
                    {
                        pout.print((memberIds[j] + 1) + ","); // points indexed by 1 now- Matlab convention
                        String description = pointDescriptions[memberIds[j].intValue()];
                        String url = pointURLs[memberIds[j].intValue()];
                        if (url != null) {
                            description = description.trim() + ":" + url;
                        }
                        pout.println(description);
                    } else {
                        pout.println(memberIds[j] + 1);  // points indexed by 1 now- Matlab convention
                    }
                }
            }
            pout.close();
            System.out.println("Saved all HDS clusters as .csv cluster label file: " + labelFile);
        } catch (IOException e) {
            System.out.println("Could not open Auto-HDS cluster labels output file " + labelFile
                    + " for writing");
        }
    }

    //saves both raw and sorted HDS trees to disk, and also
    protected void saveHDSTree(String fileIn) {
        int numPt = isDense.length;

        // now save the labeled HDS data back to an HDS tree output file
        PrintWriter pout;

        String rawFile = ModelUtil.removeExtension(fileIn) + ".hds";
        String hdsFile = ModelUtil.removeExtension(fileIn) + "_sorted.hds";

        try {
            pout = new PrintWriter(new FileWriter(rawFile, false));
            for (int i = 0; i < numPt; i++) {
                for (int j = 0; j < denseSizeList.length; j++) {
                    pout.print(hdsLabels[i][j] + " ");
                }
                pout.println();
            }
            pout.close();
        } catch (IOException e) {
            System.out.println("Could not open raw HDS tree file " + rawFile
                    + " for writing");
        }

        try {
            pout = new PrintWriter(new FileWriter(hdsFile, false));
            for (int i = 0; i < numPt; i++) {
                int idx = sortedTreeIdx[i];
                for (int j = 0; j < denseSizeList.length; j++) {
                    pout.print(hdsLabels[idx][j] + " ");
                }
                pout.println();
            }
            pout.close();
        } catch (IOException e) {
            System.out.println("Could not open sorted HDS tree file " + hdsFile
                    + " for writing");
        }
    }

    //saves the sorted HMA trees to disk
    protected void saveHMATree(String fileIn) {
        int numPt = isDense.length;

        // now save the labeled HMA data back to an HMA tree output file
        // also creates a corresponding index file for sorted index lookup
        PrintWriter pout, piout;

        String hmaFile = ModelUtil.removeExtension(fileIn) + "_sorted.hma";
        String idxFile = ModelUtil.removeExtension(fileIn) + "_sorted.idx";

        System.out.println("Saving Auto-HDS tree in text file " + hmaFile);
        System.out.println("Saving sorted index mapping in text file " + idxFile);

        try {
            pout = new PrintWriter(new FileWriter(hmaFile, false));
            piout = new PrintWriter(new FileWriter(idxFile, false));
            for (int i = 0; i < numPt; i++) {
                int idx = sortedTreeIdx[i];
                for (int j = 0; j < denseSizeList.length; j++) {
                    pout.print(hmaLabels[idx][j] + " ");
                }
                pout.println();
                piout.println(idx + 1); // change point idx to start with 1, Matlab convention
            }
            pout.close();
            piout.close();
        } catch (IOException e) {
            System.out.println("Could not open HMA tree file " + hmaFile
                    + " for writing");
        }
    }

    // propagates the cluster labels of the points passed in, for the HDS iteration passed in
    // if allFlag is true, ignores ptIdxList and performs the propagation for ALL the dense data points
    // ALL POINT IDX PASSED IN MUST BE VALID DENSE POINTS in iter iteration
    private void propagateLabels(int iter, int[] ptIdxList, int maxPossibleCId, int startCId) {
        int numPt = isDense.length;

        // useful for quickly finding unions of two vectors
        boolean[] labelHash = new boolean[maxPossibleCId + 1];
        int curlab = startCId;

        int numPropPt = ptIdxList.length;
        for (int j = 0; j < numPropPt; j++) {
            int i = ptIdxList[j]; // get idx of next pt to propagate
            curlab = curlab + 1;
            for (int k = 0; k < maxPossibleCId; k++) // initialize hash
            {
                labelHash[k] = false;
            }

            // find unique non-0 labels of dense nbrs of this pt
            int nbrSize = dptsNbrSize[i][iter];
            hdsLabels[i][iter] = curlab;
            for (int k = 0; k < nbrSize; k++) {
                int nbrIdx = dptsNbrs[i][k];
                // the nbr is dense in this iteration
                if (isDense[nbrIdx][iter]) {
                    if (hdsLabels[nbrIdx][iter] > 0) // is labeled AREADY
                    {
                        labelHash[hdsLabels[nbrIdx][iter]] = true; // saves old label of this nbr
                    }
                    // LABELING SCENARIO 1: relabel all dense nbrs to same cluster label
                    hdsLabels[nbrIdx][iter] = curlab;
                }
            }
            // find the unique non-zero labels found
            int labCount = 0;
            int[] tmpLabels = new int[maxPossibleCId + 1];
            for (int k = 1; k <= numPropPt; k++) {
                if (labelHash[k] == true) {
                    tmpLabels[labCount] = k;
                    labCount = labCount + 1;
                }
            }
            // now relabel all pts having these labels to new cluster label
            for (int k = 0; k < labCount; k++) {
                for (int l = 0; l < numPt; l++) {
                    if (isDense[l][iter]) // the point only needs to be labeled if it is dense
                    {
                        if (hdsLabels[l][iter] == tmpLabels[k]) // matches label of one of the nbrs
                        {
                            // LABELING SCENARIO 2: relabel all pts with labels same as that of dense nbrs found
                            hdsLabels[l][iter] = curlab;
                        }
                    }
                }
            }
        }
    }
    // relabels the clusters in a given iteration, to 1 to k
    // and returns the count of the number of clusters fonud

    private int relabelClusters(int iter) {
        int numPt = hdsLabels.length;
        HashMap<Integer, Integer> labelMap = new HashMap<Integer, Integer>(numPt);
        int lab = 0;
        for (int i = 0; i < numPt; i++) {
            if (isDense[i][iter]) {
                Integer ptLab = new Integer(hdsLabels[i][iter]);
                // make sure this cluster label has not been found yet
                if (labelMap.containsKey(ptLab) == false) {
                    lab = lab + 1;
                    labelMap.put(new Integer(hdsLabels[i][iter]), new Integer(lab));
                    hdsLabels[i][iter] = lab;
                } else // already exists, relabel and store
                {
                    hdsLabels[i][iter] = labelMap.get(ptLab).intValue();
                }
            }
        }
        return lab;
    }

};
