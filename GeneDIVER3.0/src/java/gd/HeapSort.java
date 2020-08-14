package gd;

/*
 * A fast, heapsort algorithm, especially in the context of
  * 1. being able to recover index for the sorted list, and 2. being able to sort only
 * top neps items at the fastest speed possible.
 *
 * Supports super-fast top neps element sorting of doubles, and also returns
 * the indexes- something critical for most machine learning applications
 * Author :Gunjan Gupta
 * August 3, 2006
 *
 */

// modified to be explicity efficientsorting a set of double numbers
// using an integer index associated with for the actual sort, rather
// than swapping the doubles themselves

class HeapSort
{
    // plain sorting - sorts all items in increasing order, no index returned
    // no partial sorting possible
    public static void sort(double a[])
    {
        int N = a.length;
        for (int k = N/2; k > 0; k--)
        {
            HeapSort.downHeap(a, k, N);
        }
        do
        {
            double T = a[0];
            a[0] = a[N - 1];
            a[N - 1] = T;
            N = N - 1;
            HeapSort.downHeap(a, 1, N);
        } while (N > 1);
    }

    public static void downHeap(double a[], int k, int N)
    {
        double T = a[k - 1];
        while (k <= N/2)
        {
            int j = k + k;
            if ((j < N) && (a[j - 1] < a[j]))
            {
                j++;
            }
            if (T >= a[j - 1])
            {
                break;
            }
            else
            {
                a[k - 1] = a[j - 1];
                k = j;
            }
        }
        a[k - 1] = T;
    }

    // sorting with index saving
    // RETURNS SMALLEST neps ITEMS AT THE END in the inverted order
    // i.e. last element is smallest, second-last is second smallest and so on...
    public static void idxSort(double a[], int idx[])
    {
        int N = a.length;
        for (int k = N/2; k > 0; k--)
        {
            HeapSort.downHeapIdx(a, idx, k, N);
        }
        do
        {
            int Tidx = idx[0];
            idx[0] = idx[N - 1];
            idx[N - 1] = Tidx;
            N = N - 1;
            HeapSort.downHeapIdx(a, idx, 1, N);
        } while (N > 1);
    }

    // used for indexed sorting, same as downheap except only the integer
    // indexes are manipulated /sorted
    public static void downHeapIdx(double a[], int idx[], int k, int N)
    {
        int Tidx = idx[k - 1];
        while (k <= N/2)
        {
            int j = k + k;
            if ((j < N) && (a[idx[j - 1]] > a[idx[j]]))
            {
                j++;
            }
            if (a[Tidx] <= a[idx[j - 1]])
            {
                break;
            }
            else
            {
                idx[k - 1] = idx[j - 1];
                k = j;
            }
        }
        idx[k - 1] = Tidx;
    }

    // partial sorting with index saving
    // RETURNS SMALLEST neps ITEMS AT THE END in the inverted order
    // i.e. last element is smallest, second-last is second smallest and so on...
    // WHILE THE REST MAINTAINS THE HEAP STATUS

    public static void partIdxSort(double a[], int idx[], int neps)
    {
        int N = a.length;
        int stopN= 1;
        if (neps<N)
        {
           stopN= N-neps;
        }

        for (int k = N/2; k > 0; k--)
        {
            HeapSort.downHeapIdx(a, idx, k, N);
        }
        do
        {
            int Tidx = idx[0];
            idx[0] = idx[N - 1];
            idx[N - 1] = Tidx;
            N = N - 1;
            HeapSort.downHeapIdx(a, idx, 1, N);
        } while (N > stopN);
    }

    // extract top neps from the inverted ordering returned by partidxsort
    // WARNING: Make sure you only ask for as many as were originally sorted
    // We are not making this Object Oriented for performance reasons!!!
    public static int [] extractTopNeps (int[] partidx, int neps)
    {
       int [] retIdx= new int[neps];
       int len= partidx.length;
       for (int i=0; i<neps; i++)
       {
          retIdx[i]= partidx[len-i-1];
       }
       return retIdx;
    }

    // continues sorting of a heap from which lastneps items were extracted earlier
    public static void continuePartIdxSort(double a[], int idx[], int lastneps, int curneps)
    {
        // make sure sorting needed
        if (curneps<= lastneps)
           return;

        int lastStopN=1;
        int lastN= a.length;

        if (lastneps< lastN)
        {
           lastStopN= lastN-lastneps;
        }
        // last time N stopped processing when it
        // reached value of lastStopN, so we need to start from there
        int N= lastStopN;

        int stopN= 1;
        if (curneps<N)
        {
           stopN= lastN-curneps;
        }

        do
        {
            int Tidx = idx[0];
            idx[0] = idx[N - 1];
            idx[N - 1] = Tidx;
            N = N - 1;
            HeapSort.downHeapIdx(a, idx, 1, N);
        } while (N > stopN);
    }

    // continues sorting of a heap from which lastneps items were extracted earlier
    // until the value exceeds the reps limit. returns the total no. of elements that
    // are in a sorted state at the end of the process.
    public static int extendPartIdxSort(double a[], int idx[], int lastneps, double reps)
    {
        int len= a.length;

        // make sure sorting needed, not needed
        // if the last sorted element exceeds reps in value
        if (a[idx[len-lastneps]]>= reps)
           return lastneps;

        int lastStopN=1;

        int N= 1;

        if (lastneps< len)
        {
           // last time N stopped processing when it
           // reached value of lastStopN, so we need to start from there
           N= len-lastneps;
        }

        do
        {
            int Tidx = idx[0];
            idx[0] = idx[N - 1];
            idx[N - 1] = Tidx;
            N = N - 1;
            HeapSort.downHeapIdx(a, idx, 1, N);
        } while ((N > 1) && (a[idx[N]]<=reps));

        // no. of elements now sorted
        return len-N;
    }

    // prints the first few sorted entries to the console
    // useful for debugging
    public static void printFirstFew (double a[], int idx[], int neps)
    {
       int arraySize= a.length;
       for (int j = arraySize-1; j > arraySize-neps; j--)
       {
          System.out.println("[" + idx[j] + "]=" + a[idx[j]]);
       }
    }

    // helper function for getting a fast index array already initialized
    public static int[] getIndexArray(int arraySize)
    {
       int[] retVal= new int[arraySize];
       for (int j=0; j<arraySize; j++)
       {
          retVal[j]= j;
       }
       return retVal;
    }
}


