package gd;

/*
 * Shell version of Gene Diver - runs Auto-HDS, generates the HDS tree, and
 * can automatically selects clusters, but does not generate any graphics
 * output- good for calling in batch mode.
 */

import java.io.*;
import java.util.*;
import java.lang.String;

public class DiverShell
{
   public static void main (String[] argv)
   {
      // IMPORTANT: PLEASE KEEP THIS UPTO DATE IF ADDING/CHANGING PARAMETERS
      String usageStr= "Usage: DiverShell -[SMF] dataFile=<dataFile distance matrix File>\n"+
         "neps=[3-n] fshave=[0-0.99] [rshave=[0.01 to fshave]]"+
         "[classCol=<class label column name>]\n"+
         "[classColIdx=<column no. of class label column, starting with 0>]\n"+
         "[delimiter=<delimiting character for parsing data file>]\n"+
         "[distMeasure=<Pearson|Euclidean|Cosine>]\n"+
         "Description of the (optional) flags:\n"+
         "M : when data passed is a distance Matrix, outherwise vector data input\n"+
         "    is assumed.\n"+
         "F : only a single cut, i.e. Density shaving corresponding to fshave\n"+
         "    returned, no Auto-HDS hierarchy generated.\n"+
         "S : If specified, skips first line in data, usually containing the column names.\n"+
             "    Currently only applies to the vector data file\n";

      // all the parameters needed by Diver
      String params=null, dataFile=null;
      String delimiter=" ", distMeasure=null;
      // name of the class label column
      String classCol=null, classColIdxStr=null;
      // index of the class label column
      int classColIdx=-1;

      int neps=-1;
      double fshave=-1, rshave=-1;

      // default distance measure is euclidean
      int distMeasureVal= Diver.EUCLIDEAN;

      if (argv.length >0)
      {
         params = argv[0];

         // true when distance matrix passed in
         boolean matrixFlag= false;
         // true if user wants only Density Shaving not Auto HDS
         boolean onlyDS= false;

         // skip first data line
         boolean skipFirstDataLine= false;

         // check if parameter list passed correctly
         if (params.startsWith("-")==true)
         {
            // distance matrix passed or not m, means passed
            if (params.contains("M")== true)
            {
               matrixFlag= true;
            }

            if (params.contains("F")== true)
            {
               onlyDS= true;
            }

            if (params.contains("S")== true)
            {
               skipFirstDataLine= true;
            }
         }

         // now parse the remaining arguments and pick out other
         // parameters passed in
         for (int i=1; i< argv.length; i++)
         {
            if (ModelUtil.matchesNameValueName("dataFile", argv[i]))
            {
               dataFile = ModelUtil.extractStrNameValue("dataFile", argv[i]);
            }
            if (ModelUtil.matchesNameValueName("delimiter", argv[i]))
            {
               delimiter = new String(ModelUtil.extractStrNameValue("delimiter", argv[i]));
            }
            if (ModelUtil.matchesNameValueName("classCol", argv[i]))
            {
               classCol = new String(ModelUtil.extractStrNameValue("classCol", argv[i]));
            }
            if (ModelUtil.matchesNameValueName("classColIdx", argv[i]))
            {
               classColIdxStr = new String(ModelUtil.extractStrNameValue("classColIdx", argv[i]));
               try
               {
                  classColIdx = Integer.parseInt(classColIdxStr);
               }
               catch (NumberFormatException e)
               {
                  return;
               }
            }

            if (ModelUtil.matchesNameValueName("distMeasure", argv[i]))
            {
              distMeasure = new String(ModelUtil.extractStrNameValue("distMeasure", argv[i]));
              if (distMeasure.compareTo("Euclidean")==0)
              {
                 distMeasureVal= Diver.EUCLIDEAN;
              }
              else
              if (distMeasure.compareTo("Pearson")==0)
              {
                 distMeasureVal= Diver.PEARSON;
              }
              else
              if (distMeasure.compareTo("Cosine")==0)
              {
                 distMeasureVal= Diver.COSINE;
              }
              else
              {
                 System.err.println("Invalid distance measure specified: "+ distMeasure);
                 System.err.println("Choices are: EUCLIDEAN, PEARSON, COSINE");
                 return;
              }
            }

            if (ModelUtil.matchesNameValueName("neps", argv[i]))
            {
               try
               {
                  neps= ModelUtil.extractIntegerNameValue("neps", argv[i]);
               }
               catch (NumberFormatException e)
               {
                  return;
               }
            }
            if (ModelUtil.matchesNameValueName("fshave", argv[i]))
            {
               try
               {
                  fshave= ModelUtil.extractDoubleNameValue("fshave", argv[i]);
               }
               catch (NumberFormatException e)
               {
                  return;
               }
            }
            if (ModelUtil.matchesNameValueName("rshave", argv[i]))
            {
               try
               {
                  rshave= ModelUtil.extractDoubleNameValue("rshave", argv[i]);
               }
               catch (NumberFormatException e)
               {
                  return;
               }
            }
         }

         if (dataFile==null)
         {
            System.err.println("Data file not specified, please specify a data file");
            System.err.println(usageStr);
            return;
         }

         if (delimiter==null)
         {
            System.out.println("Data delimiter not specified, assuming space delimited data file.");
            delimiter=" ";
         }

         if (matrixFlag==false) // if data passed in is vector data
         {
            if (distMeasure==null)
            {
               System.out.println("Distance measure not specified, assuming Euclidean.");
               delimiter=" ";
            }
            if (skipFirstDataLine== true)
            {
               System.out.println("Skipping first data line, assuming them to be labels");
               if (classColIdx==-1)
               {
                  if (classCol==null)
                  {
                     System.out.println("Assuming all columns are valid features");
                  }
                  else
                  {
                     try
                     {
                        classColIdx= ModelUtil.findClassColumnIdx(dataFile, classCol, delimiter);
                        if (classColIdx==-1)
                        {
                           System.err.println("Could not find class column index with name "+ classCol);
                        }
                     }
                     catch (IOException e)
                     {
                        System.err.println("Could not open data file "+ dataFile);
                     }
                  }
               }
               else
               {
                  System.out.println("Assuming "+ classColIdx+" column contains class labels");
               }
            }
         }

         if (neps< 3)
         {
            System.err.println("neps not specified, please specify an integer greater than 2");
            System.err.println(usageStr);
            return;
         }

         if (fshave<= 0)
         {
            System.err.println(fshave);
            System.err.println("fshave, fraction of data to shave not specified");
            System.err.println("Please specify a fraction 0<fshave<1");
            System.err.println(usageStr);
            return;
         }

         if (onlyDS== true)
         {
            System.out.println("User requested only DS (Density Shaving) clustering");
            System.out.println("No density hierarchy or Auto-HDS results will be be returned");
         }
         else
         {
            if (rshave<= 0)
            {
               System.err.println("rshave, fraction of data to shave in each iterarion not specified");
               System.err.println("Please specify a fraction 0<rshave<1");
               System.err.println(usageStr);
               return;
            }
         }

         Diver theDiver= new Diver(40000000, distMeasureVal, classColIdx, skipFirstDataLine, false);

         // NOW ACTUAL PROCESSING WORK CAN START
         theDiver.getNNbrs(dataFile, neps, fshave, rshave, onlyDS, matrixFlag, delimiter, 1);
      }
      else
      {
         System.err.println("Invalid parameters, "+usageStr);
      }
   }
};
