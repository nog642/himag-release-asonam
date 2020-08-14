package gd;

/*
 * Container class for utility Java functions used in modeling
 * Gunjan Gupta. First version: May 2002
 * Current Version: August 2006
 *
 */

//package model;

import java.io.*;
import java.util.*;
import java.net.*;

// used by random index generator
class IndexStore implements Comparable<IndexStore>
{
   int idx;
   double val;
   public int compareTo(IndexStore objIn)
   {
      return (int)Math.round(Math.signum((val-objIn.val)));
   }
   public IndexStore (int idxIn, double valIn)
   {
      idx= idxIn;
      val= valIn;
   }
};


public class ModelUtil
{
   // checks if a URL is accessible
   public static boolean checkURL(String urlIn)
   {
      boolean retVal= true;

      try
      {
         URL testurl = new URL(urlIn);
         InputStream in = testurl.openConnection().getInputStream();
         in.close();
      }
      catch(IOException e)
      {
         retVal= false;
      }
      return retVal;
   }

   // generate a uniformly random order of N integers
   public static int[] genRandomOrder(int N)
   {
      IndexStore[] val= new IndexStore[N];
      for (int i=0; i<N; i++)
      {
         val[i]= new IndexStore(i, Math.random());
      }
      // now sort it
      Arrays.sort(val);
      // now extract the indexes - they should be in random order now
      int [] retVal= new int[N];
      for (int i=0; i<N; i++)
      {
         retVal[i]= val[i].idx;
      }
      return retVal;
   }

   // generates a uniformly random order of N doubles between 0 and maxVal
   public static double [] genRandomDoubles (int N, double maxVal)
   {
      double [] retVal= new double[N];
      for (int i=0; i<N; i++)
      {
         retVal[i]= Math.random()*maxVal;
      }
      return retVal;
   }

   // returns a random integer between 0<= i < N
   public static int getRandomIdx(int N)
   {
      return (int)  Math.floor(Math.random()*N);
   }


   // simple indexed sort for doubles using hash tables
   // returns the sorted order as index to the original elements
   // in rowIn. Much faster than trying to track indexes inside objects
   // such as using Arrays.sort(IndexedDouble).
   public static int[] idxHashSortDouble(double[] rowIn)
   {
      Double[] rowO= new Double[rowIn.length];
      HashMap<Double,Integer> idxMap= new HashMap<Double,Integer>(rowIn.length);
      int [] retIdx= new int[rowIn.length];

      // create a temporary row of Double objects corresponding to input vector
      for (int i=0; i<rowIn.length; i++)
      {
         rowO[i]= new Double(rowIn[i]);
      }

      // save the hashcodes in a hashtable for lookup after sorting
      for (int i=0; i<rowIn.length; i++)
      {
         idxMap.put(rowO[i], new Integer(i));
      }

      // now sort the Doubles object row
      Arrays.sort(rowO);

      // recover the index order now
      for (int i=0; i<rowIn.length; i++)
      {
         retIdx[i]= idxMap.get(rowO[i]);
      }
      // return sort results as indexes
      return retIdx;
   }

   // a random number generator with a weighted die - the die is passed in as
   // as discreted probability distrbution buckets, the value returned is the selected
   // index following that distrbution. If the values do not sum to one, they are forced to 1
   public static int getRandomByProbDist(double[] bucketsIn)
   {
      int numBuckets= bucketsIn.length;
      int retVal= numBuckets;
      double [] cumBuckets= new double[numBuckets];
      double prevBucket=0;
      for (int i=0; i< numBuckets; i++)
      {
         cumBuckets[i]= bucketsIn[i]+prevBucket;
         prevBucket= cumBuckets[i];
      }
      // compute cumulative sum array and verify the sum is 1
      if (Math.abs(cumBuckets[numBuckets-1]-1)>0.00001)
      {
         System.err.println("Warning: Buckets passed sum to a value "+ cumBuckets[numBuckets-1]+" renormalizing to 1.");
      }
      // generate a random number between 0 and 1 and see which bucket should get it
      double randProb= Math.random();

      for (int i=0; i< numBuckets; i++)
      {
         cumBuckets[i]= cumBuckets[i]/cumBuckets[numBuckets-1];
         if (randProb<=cumBuckets[i])
         {
            retVal=i;
            break;
         }
      }
      // for debugging - DO NOT REMOVE
/*      System.out.println("Random prob:"+ randProb);
      System.out.print("Original Buckets:");
      for (int i=0; i< numBuckets; i++)
      {
         System.out.print(bucketsIn[i]+" ");
      }
      System.out.println();
  */
      return retVal;
   }

   // similar to string tokenizer but works with tokens longer than 1 character
   // for example parseTokenArray(x, "___") looks for occurences of 3 _ to use
   // as a demarcation point
   public static String [] parseTokenArray(String strIn, String tokenStr)
   {

      Vector<String> retList= new Vector<String>();
      int curPos=0, strLen= strIn.length(), tokenLen= tokenStr.length();

      while (curPos<strLen)
      {
         int atIdx= strIn.indexOf(tokenStr, curPos);
         if (atIdx==-1)
         {
            retList.add(strIn.substring(curPos,strLen));
            break;
         }
         else
         {
//            System.out.println(strIn.substring(curPos,curPos+tokenLen));
            retList.add(strIn.substring(curPos,atIdx));
            curPos=atIdx+tokenLen;
         }
      }

      // extract elements from the vector into a string array
      String [] retVal= new String [retList.size()];
      for (int i=0; i< retList.size(); i++)
      {
         retVal[i]= (String)retList.get(i);
      }
      return retVal;
   }

   // generic function for counting number of lines in a file
   public static int getNumLines(String filename)
   {
      FileReader fin;
      LineNumberReader fLin;

      int count=0;
      String buffer= new String("");
      try
      {
         fin= new FileReader(filename);
         fLin= new LineNumberReader (fin);
         while (buffer!=null)
         {
            try
            {
               buffer= fLin.readLine ();
               if (buffer !=null)
               {
                  count++;
               }
            }
            catch (IOException e)
            {
               System.err.println(e.getMessage());
            }
         }
         // now close the file
         try
         {
            fLin.close();
            fin.close();
         }
         catch (IOException e)
         {
            System.err.println ("Could not close file: "+filename);
         }
      }
      catch (IOException e)
      {
         System.err.println ("Could not open file: "+filename);
      }
      return (count);
   }

   // generic function for counting number of columns in a data file
   public static int getNumColumns(String filename, int BUFFER_SIZE_IN, String delimiter)
   {
     LineNumberReader fLin=null;

     int count=0;
     String buffer= new String("");
     try
     {
        fLin= new LineNumberReader (new FileReader(filename), BUFFER_SIZE_IN);
        while (buffer!=null)
        {
           try
           {
              buffer= fLin.readLine ();
              // if found a line and it is not all blanks
              if ((buffer !=null) && (buffer.trim().length() >0))
              {
                 StringTokenizer st= new StringTokenizer(buffer, delimiter);
                 count= st.countTokens();
              }
           }
           catch (IOException e)
           {
              System.err.println(e.getMessage());
           }
        }
        // now close the file
        try
        {
           fLin.close();
        }
        catch (IOException e)
        {
           System.err.println ("Could not close file: "+filename);
        }
     }
     catch (IOException e)
     {
        System.err.println ("Could not open file: "+filename);
     }
     return (count);
   }

   // generic function for counting number of NON-EMPTY lines in a file
   // should use this if you are reading data as you want to skip empty lines
   public static int getNumNonEmptyLines(String filename, int BUFFER_SIZE_IN, boolean debugFlag)
   {
      LineNumberReader fLin=null;

      int count=0;
      String buffer= new String("");
      try
      {
         fLin= new LineNumberReader (new FileReader(filename), BUFFER_SIZE_IN);
         while (buffer!=null)
         {
            try
            {
               buffer= fLin.readLine ();
               // if found a line and it is not all blanks
               if ((buffer !=null) && (buffer.trim().length() >0))
               {
                  count++;
               }
            }
            catch (IOException e)
            {
               System.err.println(e.getMessage());
            }
         }
         // now close the file
         try
         {
            fLin.close();
         }
         catch (IOException e)
         {
            System.err.println ("Could not close file: "+filename);
         }
      }
      catch (IOException e)
      {
         if (debugFlag)
         {
            System.err.println ("Could not open file: "+filename);
         }
         count=-1;
      }
      return (count);
   }

   // generic function for reading lines in a text file into an array
   public static String[] readFileIntoArray(String filename, int numLineIn, boolean debugFlag)
   {
      FileReader fin;
      LineNumberReader fLin;
      String[] fileBuffer= new String [numLineIn];

      int debugWidth= Math.round(numLineIn/10);
      if (debugWidth<500)
      {
        debugWidth=500;
      }
      if (debugWidth>10000)
      {
         debugWidth=10000;
      }

      String buffer= new String("");
      try
      {
         fin= new FileReader(filename);
         fLin= new LineNumberReader (fin);

         int numTrueLines=0;
         while(numTrueLines< numLineIn)
         {
            try
            {
               buffer= fLin.readLine ();
               if (buffer.trim().length()>0) // a non-empty line
               {
                  fileBuffer[numTrueLines]= buffer;
                  numTrueLines++;
               }
            }
            catch (IOException e)
            {
               System.err.println ("Could not read file: "+filename);
            }
            if (debugFlag==true)
            {
               if (numTrueLines % debugWidth == 0)
               {
                  System.err.println("Read "+ numTrueLines+ " out of "+ numLineIn+ " lines...");
               }
            }
         }

         try
         {
            fLin.close();
            fin.close();
         }
         catch (IOException e)
         {
            System.err.println ("Could not close file: "+filename);
         }
      }
      catch (IOException e)
      {
         System.err.println ("Could not open file: "+filename);
      }
      return (fileBuffer);
   }

   // saves the file loaded by readFileIntoArray() back to a file
   public static void saveArrayToFile(String filename, Vector arrayIn)
   {
      FileWriter fout;
      PrintWriter pout;
      // initialize the file and dump the array into it
      try
      {
         fout= new FileWriter (filename, false);
         pout= new PrintWriter (fout);
         int numLineIn= arrayIn.size();
         for (int i=0; i<numLineIn; i++)
         {
            if (arrayIn.get(i) != null)
            {
               pout.println (arrayIn.get(i));
            }
         }
         // now close the file
         try
         {
            fout.close();
            pout.close ();
         }
         catch (IOException e)
         {
            System.err.println ("Could not close file: "+filename);
         }
      }
      catch (IOException e)
      {
         System.err.println ("Could not create file "+filename+" for writing");
      }
   }

   // pads all strings to have the same length - length of longest string
   public static String[] padToMaxSize (String [] strList, char padChar)
   {
      int numPt= strList.length;
      String[] retVal= new String[numPt];

      int maxLen= 0;
      for (int i=0; i<numPt; i++)
      {
         int len= strList[i].length();
         if (len > maxLen)
         {
            maxLen= len;
         }
      }
      // now append padChar to all the strings
      for (int i=0; i<numPt; i++)
      {
         int len= strList[i].length();
         StringBuffer tmp= new StringBuffer(strList[i]);
         if (len< maxLen)
         for (int j=0; j<(maxLen-len); j++)
         {
            tmp.append(padChar);
         }
         retVal[i]= tmp.toString();
      }
      return retVal;
   }

   // convert a double object array to scalar integer array
   public static int [] convertToIntArray (Double [] dArrayIn)
   {
      int [] retVal= new int[dArrayIn.length];
      for (int i=0; i< dArrayIn.length; i++)
      {
         retVal[i]= dArrayIn[i].intValue();
      }
      return retVal;
   }

   // convert a double object array to scalar double array
   public static double [] convertToDoubleArray (Double [] dArrayIn)
   {
      double [] retVal= new double[dArrayIn.length];
      for (int i=0; i< dArrayIn.length; i++)
      {
         retVal[i]= dArrayIn[i].doubleValue();
      }
      return retVal;
   }

   // remove any trailing semicolons etc from a numeric string
   public static String cleanUpNumericString(String strIn)
   {
      StringBuffer retVal= new StringBuffer("");
      for (int j=0; j< strIn.length(); j++)
      {
         char curChar= strIn.charAt(j);
         if (Character.isDigit(curChar))
         {
            retVal.append(curChar);
         }
      }
      return retVal.toString();
   }


   // removes the extension from a file - everything after the . and including
   // the . is removed
   public static String removeExtension (String fileNameIn)
   {
      int dotPos= fileNameIn.lastIndexOf('.');
      if (dotPos == -1)
      {
        return fileNameIn;        
      }
      else
      {
        return fileNameIn.substring(0, dotPos);
      }
   }

   // toggles a boolean value returns true if it was false and false if true
   private static boolean toggleBoolean (boolean valIn)
   {
      boolean retVal= false;
      if (valIn==false)
      {
         retVal= true;
      }
      return retVal;
   }

   // extract the strings and return it as an array of strings
   // expects a format of type {'asdasdf', 'asdfsdf' ...}
   public static Object parseStringArray(String strIn)
   {
      Vector<String> retList= new Vector<String>();
      int curPos=0;
      char curChar= strIn.charAt(curPos);
      boolean insideString= false;
      StringBuffer curStr= new StringBuffer();

      while ((curChar!='}') && (curChar!='\n'))
      {
         curPos= curPos+1;
         curChar= strIn.charAt(curPos);
         if (curChar=='\'')   // found the start of a string element
         {
            insideString= toggleBoolean (insideString);
            if (insideString== false) // completed a string
            {
               retList.add(curStr.toString());
               // clear up the buffer for the next string
               curStr.delete(0, curStr.length());
            }
         }
         else
         if (insideString)
         {
            curStr.append(curChar);
         }
      }

      // extract elements from the vector into a string array
      String [] retVal= new String [retList.size()];
      for (int i=0; i< retList.size(); i++)
      {
         retVal[i]= (String)retList.get(i);
      }
      return retVal;
   }

   // extract the numbers and return it as an array of doubles
   // expects a format of type [ 2 34 45.67 ]
   public static Object parseNumberArray(String strIn)
   {
      // return buffer array
      Double [] retVal= null;
      Vector<Double> retList= new Vector<Double>();

      int curPos=0;
      char curChar= strIn.charAt(curPos);
      boolean insideString= false;
      StringBuffer curStr= new StringBuffer();

      // extract the definition part of the number array
      while ((curChar!=']') && (curChar!='\n'))
      {
         curPos= curPos+1;
         curChar= strIn.charAt(curPos);
         //check to see if its part of a number definition
         if ((curChar=='.') || (Character.isDigit(curChar)) || (Character.isWhitespace(curChar)))
         {
            curStr.append(curChar);
         }
      }

      // parse the numbers
      StringTokenizer st= new StringTokenizer(curStr.toString());
      while (st.hasMoreTokens())
      {
         try
         {
            retList.add(new Double(st.nextToken()));
         }
         catch (NumberFormatException e)
         {
            System.err.println("Error parsing definition: "+ strIn);
            System.err.println("Not a valid number array format");
            retList= null;
         }
      }

      // if found a valid set of numbers in the definition
      if ((retList!= null) && (retList.size() >0))
      {
         retVal= new Double [retList.size()];
         // extract elements from the vector into a double array

         for (int i=0; i< retList.size(); i++)
         {
            retVal[i]= (Double)retList.get(i);
         }
      }
      return retVal;
   }

   public static HashMap<String,Long> getWordCount(LineNumberReader fLin, String wordFile, int minHashSize, boolean waitFlag)
   {
      HashMap<String,Long> wordList= new HashMap<String,Long>(minHashSize);
      String curLine= new String("");
      long lnCount=0;
      do
      {
         try
         {
            curLine= fLin.readLine();
            lnCount= lnCount+1;
            if ((lnCount%5000==0) && (waitFlag==true))
             {
                System.err.println("Processed " + lnCount + " lines ..");
             }

            if (curLine!=null)
            {
               StringTokenizer st= new StringTokenizer(curLine);
               while (st.hasMoreTokens())
               {
                  String curWord= st.nextToken();
                  Object val= wordList.get(curWord);
                  if (val==null)
                  {
                     wordList.put(curWord, new Long(1));
                  }
                  else
                  {
                    wordList.put(curWord,
                                 new Long( ( (Long) val).longValue() + 1));
                  }
               }
            }
         }
         catch (IOException e)
         {
            System.err.println("Could not read word file: "+ wordFile);
         }
      }
      while (curLine!=null);
      if (waitFlag==true)
      {
         System.out.println("Processed " + lnCount + " lines ..");
      }
      return wordList;
   }

   // print a single html table cell, given a string
   public static void printHTMTC(PrintWriter poutIn, String cellVal)
   {
      poutIn.println("<td><center>"+ cellVal+ "</center></td>");
   }

   // converts a list of words into a distinct list of words, removing repetitions
   public static Object [] getDistinctWords(StringTokenizer stIn)
   {
       HashMap<String,Long> wordList= new HashMap<String,Long>(1000);
       while (stIn.hasMoreTokens())
       {
         String curWord= stIn.nextToken();
         Object val= wordList.get(curWord);
         if (val==null)
         {
            wordList.put(curWord, new Long(1));
         }
         else
         {
           wordList.put(curWord,
                        new Long( ( (Long) val).longValue() + 1));
         }
       }
       // now flatten and return the vector
       return (wordList.keySet()).toArray();
   }

   // checks if the name of the name-value pair passed matches desired name
   public static boolean matchesNameValueName(String name, String namevalue)
   {
      boolean retVal= false;
      int idx= namevalue.indexOf("=");
      // now parse out the value
      if (idx!=-1)
      {
         String nameFound= (namevalue.substring(0,idx)).trim();
         if ((name.trim()).compareTo(nameFound)==0) // names match
         {
            retVal= true;
         }
      }
      return retVal;
   }

   // extracts the value of string defined by a name=value pair if
   // the name matches, else returns null
   public static String extractStrNameValue(String name, String namevalue)
   {
      String retVal=null;
      int idx= namevalue.indexOf("=");
      // now parse out the value
      if (idx!=-1)
      {
         String nameFound= (namevalue.substring(0,idx)).trim();
         String value= (namevalue.substring(idx+1, namevalue.length())).trim();
         if ((name.trim()).compareTo(nameFound)==0) // names match
         {
            retVal= value;
         }
      }
      return retVal;
   }

   // extracts the value of an integer defined by a name=value pair if
   // the name matches, and a valid integer is present, else throws an exception
   public static int extractIntegerNameValue(String name, String namevalue)
   {
      int retVal=-1;
      int idx= namevalue.indexOf("=");
      // now parse out the value
      if (idx!=-1)
      {
         String nameFound= (namevalue.substring(0,idx)).trim();
         String value= (namevalue.substring(idx+1, namevalue.length())).trim();
         if (name.compareTo(nameFound)==0) // names match
         {
            try
            {
               retVal = Integer.valueOf(value);
            }
            catch (NumberFormatException e)
            {
               System.err.println("Invaid integer name-value parameter: "+ name+"="+value);
               retVal= -11111;
               throw e;
            }
         }
      }
      return retVal;
   }

   // extracts the value of a double defined by a name=value pair if
   // the name matches, and a valid integer is present, else throws an exception
   public static double extractDoubleNameValue(String name, String namevalue)
   {
      double retVal=-1;
      int idx= namevalue.indexOf("=");
      // now parse out the value
      if (idx!=-1)
      {
         String nameFound= (namevalue.substring(0,idx)).trim();
         String value= (namevalue.substring(idx+1, namevalue.length())).trim();
         if (name.compareTo(nameFound)==0) // names match
         {
            try
            {
               retVal =  Double.parseDouble(value);
            }
            catch (NumberFormatException e)
            {
               System.err.println("Invaid double name-value parameter: "+name+"="+value);
               retVal= -11111;
               throw e;
            }
         }
      }
      return retVal;
   }


   // printing debug statements for tedious processing
   public static int getDebugWidth(int numLineIn, int minWidth, int maxWidth)
   {
     int debugWidth = Math.round(numLineIn / 10);
     if (debugWidth < minWidth)
     {
       debugWidth = minWidth;
     }
     if (debugWidth > maxWidth)
     {
       debugWidth = maxWidth;
     }
     return debugWidth;
   }

   // reads a file containing vector data with each row containing a
   // vector of numbers of length numDim representing numDim dimensions, and numpt
   // is the number of points. Gives error if the data is not numPt x numDim
   // WARNING: STORES RESULT IN PREALLOCATED DATA PASSED IN (for performance reasons)
   // ALSO SKIPS THE COLUMNS THAT ARE ASKED TO BE SKIPPED FROM LOADING
   // WILL ALLOW IN FUTURE TO READ DATA SELECTIVELY
   // IGNORES classLabel column in classLabel vector passed in is null
   public static boolean readVectorDoubleData(String fileIn, int numPt,
                                     int numCol, int[] useColIdx, int[] classLabel, int classLabelIdx,
                                     String delimIn, double [][] data, boolean skipFirstLine,
                                     int discBufferSize, int debugWidth, int debugFlag)
                                     throws IOException
   {
      boolean retVal= true;

      // no. of dimensions to load (skipping ones users asks to skip)
      int numDim= useColIdx.length;

      // store info on what columns are to be read
      boolean[] useColFlag= new boolean[numCol];
      for (int i=0; i<numCol; i++)
      {
         useColFlag[i]=false;
      }
      for (int i=0; i<numDim; i++)
      {
         useColFlag[useColIdx[i]]=true;
      }

      try
      {
         LineNumberReader fLin= new LineNumberReader (new FileReader(fileIn), discBufferSize);
         if (skipFirstLine==true) // skip first line, likely contains feature names
         {
            fLin.readLine();
         }
         StreamTokenizer st= new StreamTokenizer(fLin);
         int delimCode= delimIn.codePointAt(0);
         st.whitespaceChars(delimCode, delimCode);
         st.parseNumbers();
         st.eolIsSignificant(true); // verify end of line
         int rowIdx=0, colIdx=0, usedIdx=0, tokenType=-1;
         do
         {
            tokenType= st.nextToken();
            if (tokenType== st.TT_NUMBER)
            {
              if (colIdx>=numCol) //handle error if the file format is not fix no. of columns each row
              {
                System.err.println("No of columns found at row "+ rowIdx+" not correct!");
                System.err.println("Expected "+numCol+" columns, found at least "+ colIdx);
                retVal= false;
                return retVal;
              }
               if (useColFlag[colIdx]) // only save if a valid column else ignore
               {
                  data[rowIdx][usedIdx] = st.nval;
                  usedIdx= usedIdx+1;
               }
               else
               if ((classLabel!=null) && (colIdx== classLabelIdx))
               {
                  classLabel[rowIdx] = (int)st.nval;
               }
               colIdx = colIdx + 1;
            }
            else
            if (tokenType== st.TT_EOL)
            {
               rowIdx= rowIdx+1;
               if (debugFlag>0)
               {
                  if ((rowIdx+1) % debugWidth == 0)
                  {
                     System.out.println("Read "+ rowIdx+ " out of "+ numPt+ " rows...");
                  }
               }

               if (colIdx!= numCol)
               {
                 System.err.println("No of columns found at row "+ rowIdx+" not correct!");
                 System.err.println("Expected "+numCol+" columns, found "+ colIdx);
                 retVal= false;
                 return retVal;
               }
               colIdx=0;
               usedIdx=0;
               if (rowIdx> numPt)
               {
                  System.err.println("Too many lines of data found.");
                  System.err.println("Expected only "+ numPt+ " data lines.");
                  retVal= false;
                  return retVal;
               }
            }
         } while (tokenType != st.TT_EOF);

         fLin.close();
      }
      catch (IOException e)
      {
         retVal= false;
         throw (e);
      }
      return retVal;
   }

   public static int findClassColumnIdx(String fileIn, String columnName, String delimIn) throws IOException
   {
      int retVal=-1;
      try
      {
         LineNumberReader fLin = new LineNumberReader(new FileReader(
            fileIn));
         String colLabels = fLin.readLine();
         StringTokenizer st = new StringTokenizer(colLabels, delimIn);
         int i=0;
         while (st.hasMoreTokens())
         {
            String curColStr= st.nextToken();
            if (curColStr.compareTo(columnName)==0)
            retVal= i;
            i++;
         }
         fLin.close();
      }
      catch (IOException e)
      {
         throw (e);
      }
      return retVal;
   }

   // finds the values of the unique integers in vectIn. requires the
   // an approximate estimate of the number of unique entries to be found
   // Returns unique labels and their sizes in labOut and sizeOut respectively
   // Similar in function to the hist() function in Matlab
   public static void histogram (int[] vectIn, int numUnique, int[] labOut, int[] sizeOut)
   {
      HashMap<Integer, Integer> h= new HashMap<Integer, Integer>(numUnique);
      for (int i=0; i< vectIn.length; i++)
      {
         Integer curLab= new Integer(vectIn[i]);
         Integer count= h.get(curLab);
         if (count==null) // first occurence
         {
            h.put(curLab,new Integer(1));
         }
         else // increment count
         {
            h.put(curLab,new Integer((count.intValue()+1)));
         }
      }

      int numLabFound= h.size();

      // now look up values and return them and their count
      Set<Integer> keys= h.keySet();
      Iterator<Integer> iter= keys.iterator();
      for (int j=0; j< numLabFound; j++)
      {
         Integer lab= iter.next();
         labOut[j]= lab.intValue();
         sizeOut[j]= h.get(lab);
      }
   }

   // returns the unique set of integers in the input
   // similar to matlab unique function
   public static int[] uniqueInt (int[] vectIn)
   {
      HashSet<Integer> h= new HashSet<Integer>(vectIn.length);
      for (int i=0; i< vectIn.length; i++)
      {
         Integer val= new Integer(vectIn[i]);
         if (!h.contains(val))
         {
            h.add(val);
         }
      }
      Iterator<Integer> iter= h.iterator();
      int numLabFound= h.size();
      int[] retVal= new int[numLabFound];
      for (int j=0; j< numLabFound; j++)
      {
         Integer lab= iter.next();
         retVal[j]= lab.intValue();
      }
      return retVal;
   }


   // finds the values of the unique integers in vectIn. requires the
   // exact number of unique entries to be found be known. Use ModelUtil.uniqueInt()
   // for preprocessing to get that value.
   // Similar in function to the hist() function in Matlab.
   // Returns unique labels and their indexes in labOut and listOut respectively

   public static void histogram (int[] vectIn, int numUnique, int[] labOut, Vector<Integer[]> listOut)
   {
      int initialSize= Math.round(vectIn.length/numUnique)+1;
      HashMap<Integer, ArrayList<Integer>> h= new HashMap<Integer, ArrayList<Integer>>(numUnique);
      for (int i=0; i< vectIn.length; i++)
      {
         Integer curLab= new Integer(vectIn[i]);
         ArrayList<Integer> labList= h.get(curLab);
         if (labList==null) // first occurence of items of this label
         {
            // add the current index as first element
            labList= new ArrayList<Integer>(initialSize);
            labList.add(new Integer(i));
            h.put(curLab, labList);
         }
         else
         {
            // add current index to the list of indexes for this label
            labList.add(new Integer(i));
            h.put(curLab, labList);
         }
      }

      int numLabFound= h.size();
      // now look up labels and return them and the corresponding index list
      Set<Integer> keys= h.keySet();
      Iterator<Integer> iter= keys.iterator();
      for (int j=0; j< numLabFound; j++)
      {
         Integer lab= iter.next();
         labOut[j]= lab.intValue();
         ArrayList<Integer> list= h.get(lab);
         Integer[] out= new Integer[list.size()];
         list.toArray(out);
         listOut.add(out);
      }
   }

   // returns well-separated RGB colors
   public static void getDistinctColors(int numPt, int numCol, int[] red, int[] green, int[] blue)
   {
       // scale the cluster colors into the number of colors needed
       int[][] colorList= new int[3][numPt];
       double power= (double)1;
       power= power/(double)3;
       double numsteps = Math.pow((double)numPt,power);
       double stepsize= ((double)255)/numsteps;
//       System.out.println("stepsize="+stepsize);
       int i=0;
       double currval=0, curgval=0, curbval=0;
       do
       {
          colorList[0][i]= (int)Math.floor(currval)+1;
          colorList[1][i]= (int)Math.floor(curgval)+1;
          colorList[2][i]= (int)Math.floor(curbval)+1;
          curbval= curbval+stepsize;
          if (curbval>255)
          {
             curbval=0;
             curgval= curgval+stepsize;
             if (curgval>255)
             {
               curgval=0;
               currval= currval+stepsize;
             }
          }
          i++;
       } while (i<numPt);

       double colSpace= (double)numPt/(double)(numCol+1);
       // now return the spaced colors
       int pos=0;
       for (i=0; i<numCol; i++)
       {
          pos= (int)Math.round((double)(i+1)*colSpace);
          red[i]= colorList[0][pos];
          green[i]= colorList[1][pos];
          blue[i]= colorList[2][pos];
//          System.out.println(red[i]+" "+ green[i]+" "+ blue[i]);
       }
   }


   public static String htmlPost(String urlStr, String postContent)
   {
      String retResponse=null;
      DataOutputStream    printout;
      DataInputStream     input;
      URLConnection urlConn=null;
      URL posturl= null;
      try
      {
         posturl= new URL(urlStr);
         urlConn= posturl.openConnection();
         urlConn.setDoInput(true);
         urlConn.setDoOutput(true);
         urlConn.setUseCaches(false);

         // Send POST output.
         DataOutputStream po = new DataOutputStream (urlConn.getOutputStream());
         po.writeBytes (postContent);
         po.flush ();
         po.close ();

         //now get ready to write output

         // Get response data.
         DataInputStream in = new DataInputStream (urlConn.getInputStream ());
         StringBuffer str= new StringBuffer("");
         int c;
         do
         {
            c = in.read();
            if(c != -1)
            {
               str.append((char)c);
                //System.out.println("Char="+(char)c+" Int="+c);
            }
         } while(c != -1);
         in.close();
         retResponse= str.toString();
      }
      catch(IOException e)
      {
         System.err.println(e);
      }
      return retResponse;
   }

};


