package gd;

/**
 * Container class for creating images of HDS and Auto-HDS trees
 */

import java.awt.*;
import javax.swing.*;
import javax.swing.border.*;

public class HDSImage extends JPanel
{
   private Image img=null;
   Border figureBorder= null;
   Border etched= null;

   // these numbers are critical for mapping
   // pixels to hma Row/columns
   // used for non-zoomed plot
   public int numRow=-1;
   public int numCol=-1;
   public int numNonDense=-1;

   // needed for zoomed plot
   public int startIRow=-1, numIRow=-1;
   public int startICol=-1, numICol=-1;

   public int imgWidth=-1;
   public int imgHeight=-1;
   public float fpixWidth=0, fpixHeight=0;
   public static final int XPIXOFFSET=2, YPIXOFFSET=5;

   public boolean isHMAFigure= false;

   public boolean isDrawn()
   {
      boolean retVal= true;
      if (img==null) // image not drawn before
      {
         retVal=false;
      }
      return(retVal);
   }

   public HDSImage (String imageTitle)
   {
      etched= BorderFactory.createEtchedBorder();
      figureBorder= BorderFactory.createTitledBorder(etched, imageTitle, TitledBorder.LEADING, TitledBorder.TOP, this.getFont(), this.getForeground());
      this.setBorder(figureBorder);
   }

   // figures out the color HMA image from the HMA label matrix
   // returns true if successful
   public boolean setHMAImage (int[][] hmaImageData, int[] sortedTreeIdx, int numHMAClusters, String newTitleStr)
   {
      boolean retVal= true;
      isHMAFigure= true;

      if ((hmaImageData!=null) && (sortedTreeIdx!=null))
      {
         // find the number of dense points at the largest (first) level
         int numPt= hmaImageData.length;
         numNonDense=0; //maximum no. of rows of non-dense points, we don't plot non-dense points
         while ((numNonDense< numPt) && (hmaImageData[sortedTreeIdx[numNonDense]][0]==0)) // short-circuted check assumed
         {
            numNonDense++;
         }
         // max no. of dense points is numRow, and we plot only these
         numRow= numPt- numNonDense;

         numCol= hmaImageData[0].length;

         imgWidth= this.getWidth()-2;
         imgHeight= this.getHeight()-5;

         // create the image now for attaching and showing
         img= createImage(imgWidth, imgHeight);

         // temporary panel for creating image
         Graphics bg= img.getGraphics();


         Color background= new Color(0,0,0);

         Font curFont= this.getFont();

         int[] red= new int[numHMAClusters];
         int[] green= new int[numHMAClusters];
         int[] blue= new int[numHMAClusters];

         ModelUtil.getDistinctColors(numPt, numHMAClusters, red, green, blue);

         int colorWidth= Math.round(1000000/(numHMAClusters+1));
         int[] clustCol= new int[numHMAClusters];
         for (int i=0; i<numHMAClusters; i++)
         {
            clustCol[i]= 3000000+ colorWidth*i;
         }

         // compute now width and height of each pixel to draw
         fpixWidth= (float)imgWidth/(float)numCol;
         fpixHeight= (float)imgHeight/(float)numRow;
         int pixWidth= (int)Math.ceil(fpixWidth);
         int pixHeight= (int)Math.ceil(fpixHeight);
         if (pixWidth==0) pixWidth=1;
         if (pixHeight==0) pixHeight=1;

         // first paint whole area with background color
         bg.setColor(background);
         bg.fillRect(XPIXOFFSET,YPIXOFFSET, imgWidth, imgHeight);
         // change border font to new color
         etched= BorderFactory.createEtchedBorder();
         figureBorder= BorderFactory.createTitledBorder(etched, newTitleStr, TitledBorder.LEADING, TitledBorder.TOP, this.getFont(), new Color(200,200,200));
         this.setBorder(figureBorder);

         // now plot HMA clusters in different colors
         for (int i=numNonDense; i<numPt; i++)
         {
            int idx= sortedTreeIdx[i];
            for (int j=0; j<numCol; j++)
            {
               int curLabel= hmaImageData[idx][j];
               if (curLabel>0)
               {
                  bg.setColor(new Color(red[curLabel-1], green[curLabel-1], blue[curLabel-1]));
                  bg.fillRect((int)Math.floor(fpixWidth*(float)j)+XPIXOFFSET, Math.round(fpixHeight*(i-numNonDense))+YPIXOFFSET, pixWidth, pixHeight);
               }
            }
         }
         img.flush();
         bg.dispose();
      }
      else
      {
         retVal= false;
      }
      return retVal;
   }

   // figures out the color HMA image from the HMA label matrix, also labels the peaks/plateaus of labelIndex^th cluster
   // if -1 passed as labelIndex, no cluster labeled
   public boolean setLabeledHMAImage (Diver diverIn, String newTitleStr, int labelIndex)
   {

      int[][] hmaImageData= diverIn.hmaLabels;
      int[] sortedTreeIdx= diverIn.sortedTreeIdx;
      int numHMAClusters= diverIn.numHMAClusters;

      boolean retVal= true;
      isHMAFigure= true;

      if ((hmaImageData!=null) && (sortedTreeIdx!=null))
      {
         // find the number of dense points at the largest (first) level
         int numPt= hmaImageData.length;
         numNonDense=0; //maximum no. of rows of non-dense points, we don't plot non-dense points
         while ((numNonDense< numPt) && (hmaImageData[sortedTreeIdx[numNonDense]][0]==0)) // short-circuted check assumed
         {
            numNonDense++;
         }
         // max no. of dense points is numRow, and we plot only these
         numRow= numPt- numNonDense;

         numCol= hmaImageData[0].length;

         imgWidth= this.getWidth()-2;
         imgHeight= this.getHeight()-5;

         // create the image now for attaching and showing
         img= createImage(imgWidth, imgHeight);

         // temporary panel for creating image
         Graphics bg= img.getGraphics();


         Color background= new Color(0,0,0);

         Font curFont= this.getFont();

         int[] red= new int[numHMAClusters];
         int[] green= new int[numHMAClusters];
         int[] blue= new int[numHMAClusters];

         ModelUtil.getDistinctColors(numPt, numHMAClusters, red, green, blue);

         int colorWidth= Math.round(1000000/(numHMAClusters+1));
         int[] clustCol= new int[numHMAClusters];
         for (int i=0; i<numHMAClusters; i++)
         {
            clustCol[i]= 3000000+ colorWidth*i;
         }

         // compute now width and height of each pixel to draw
         fpixWidth= (float)imgWidth/(float)numCol;
         fpixHeight= (float)imgHeight/(float)numRow;
         int pixWidth= (int)Math.ceil(fpixWidth);
         int pixHeight= (int)Math.ceil(fpixHeight);
         if (pixWidth==0) pixWidth=1;
         if (pixHeight==0) pixHeight=1;

         // first paint whole area with background color
         bg.setColor(background);
         bg.fillRect(XPIXOFFSET,YPIXOFFSET, imgWidth, imgHeight);
         // change border font to new color
         etched= BorderFactory.createEtchedBorder();
         figureBorder= BorderFactory.createTitledBorder(etched, newTitleStr, TitledBorder.LEADING, TitledBorder.TOP, this.getFont(), new Color(200,200,200));
         this.setBorder(figureBorder);

         // now plot HMA clusters in different colors
         for (int i=numNonDense; i<numPt; i++)
         {
            int idx= sortedTreeIdx[i];
            for (int j=0; j<numCol; j++)
            {
               int curLabel= hmaImageData[idx][j];
               if (curLabel>0)
               {
                  bg.setColor(new Color(red[curLabel-1], green[curLabel-1], blue[curLabel-1]));
                  bg.fillRect((int)Math.floor(fpixWidth*(float)j)+XPIXOFFSET, Math.round(fpixHeight*(i-numNonDense))+YPIXOFFSET, pixWidth, pixHeight);
               }
            }
         }

         if (labelIndex!=-1) // a valid cluster
         {
            bg.setColor(Color.DARK_GRAY);
            for (int i=0; i< numHMAClusters; i++)
            {
               Integer[] pointsListIdx= diverIn.hmaBaseMembers.get(i);
               int clustSize= pointsListIdx.length;
               // extract the bounding box of the cluster
               int startRow= diverIn.firstClusterIndex[i]-numNonDense;
               int numRow= clustSize;
               int startCol= diverIn.hmaBaseLevels.get(i);
               int numCol= diverIn.hmaPeakLevels[i]-startCol+1;

               if (i!=labelIndex)
               {
                  int tipX= (int)Math.round((double)(startCol+numCol)*fpixWidth);
                  int midY= (int)Math.round((startRow+((double)numRow/2.0))*fpixHeight);
                  bg.drawRect((int)Math.floor(fpixWidth*(float)startCol)+XPIXOFFSET, (int)Math.floor(fpixHeight*(startRow))+YPIXOFFSET,
                         (int)Math.ceil(numCol*fpixWidth),  (int)Math.ceil(numRow*fpixHeight));
               }
            }
            // now draw the selected cluster at the end to make sure it gets highlighted correctly
            bg.setColor(Color.WHITE);
            int i= labelIndex;
            Integer[] pointsListIdx= diverIn.hmaBaseMembers.get(i);
            int clustSize= pointsListIdx.length;
            // extract the bounding box of the cluster
            int startRow= diverIn.firstClusterIndex[i]-numNonDense;
            int numRow= clustSize;
            int startCol= diverIn.hmaBaseLevels.get(i);
            int numCol= diverIn.hmaPeakLevels[i]-startCol+1;
            int tipX= (int)Math.round((double)(startCol+numCol)*fpixWidth);
            int midY= (int)Math.round((startRow+((double)numRow/2.0))*fpixHeight);
            bg.drawRect((int)Math.floor(fpixWidth*(float)startCol)+XPIXOFFSET, (int)Math.floor(fpixHeight*(startRow))+YPIXOFFSET,
                         (int)Math.ceil(numCol*fpixWidth),  (int)Math.ceil(numRow*fpixHeight));
         }


         img.flush();
         bg.dispose();
      }
      else
      {
         retVal= false;
      }
      return retVal;
   }

   // HMA image that can draw a part of the HMA matrix
   // defined as by a box surrounding the desired cluster passed in as labelIndex
   public boolean setZoomedLabeledHMAImage (Diver diverIn, String newTitleStr, int labelIndex)
   {
      boolean retVal= true;
      isHMAFigure= true;

      int[][] hmaImageData= diverIn.hmaLabels;
      int[] sortedTreeIdx= diverIn.sortedTreeIdx;
      int numHMAClusters= diverIn.numHMAClusters;

      Integer[] pointsListIdx= diverIn.hmaBaseMembers.get(labelIndex);
      int clustSize= pointsListIdx.length;
      // extract the bounding box of the cluster that we want to zoom to
      int startCRow= diverIn.firstClusterIndex[labelIndex]-numNonDense;
      int numCRow= clustSize;
      int startCCol= diverIn.hmaBaseLevels.get(labelIndex);
      int numCCol= diverIn.hmaPeakLevels[labelIndex]-startCCol+1;

      if ((hmaImageData!=null) && (sortedTreeIdx!=null))
      {
         // find the number of dense points at the largest (first) level
         int numPt= hmaImageData.length;
         numNonDense=0; //maximum no. of rows of non-dense points, we don't plot non-dense points
         while ((numNonDense< numPt) && (hmaImageData[sortedTreeIdx[numNonDense]][0]==0)) // short-circuted check assumed
         {
            numNonDense++;
         }
         // Size of full plottable HMA matrix
         numRow= numPt- numNonDense;
         numCol= hmaImageData[0].length;

         imgWidth= this.getWidth()-2;
         imgHeight= this.getHeight()-5;

         // create the image now for attaching and showing
         img= createImage(imgWidth, imgHeight);

         // temporary panel for creating image
         Graphics bg= img.getGraphics();

         Color background= new Color(0,0,0);

         Font curFont= this.getFont();

         int[] red= new int[numHMAClusters];
         int[] green= new int[numHMAClusters];
         int[] blue= new int[numHMAClusters];

         ModelUtil.getDistinctColors(numPt, numHMAClusters, red, green, blue);

         int colorWidth= Math.round(1000000/(numHMAClusters+1));
         int[] clustCol= new int[numHMAClusters];
         for (int i=0; i<numHMAClusters; i++)
         {
            clustCol[i]= 3000000+ colorWidth*i;
         }

         ////////////////////// CUSTOM WIDTH COMPUTATION BASED ON VISIBLE AREA DESIRED

         // original HMA image pixel widths
         fpixWidth= (float)imgWidth/(float)numCol;
         fpixHeight= (float)imgHeight/(float)numRow;

         // now use heuristics figure out the contextual area you want
         // to zoom to, in a given cluster. Basically some surrounding regions be visible
         // and also we are forced to not change the aspect ratio

         startIRow= (int)Math.round(startCRow-numCRow*0.1); // 10% extra area on top
         if (startIRow<0) startIRow=0;
         int endIRow= (int)Math.round(startCRow+numCRow*1.1); // 10% extra at bottom
         if (endIRow>(numRow-1)) endIRow= numRow-1;
         startICol=  (int)Math.round(startCCol-numCCol*0.1); // 10% extra area on left
         if (startICol<0) startICol=0;
         int endICol= (int)Math.round(startCCol+numCCol*1.1); // 10% extra at right
         if (endICol>(numCol-1)) endICol= numCol-1;

         // now figure out the pixel sizes
         int iheight= endIRow-startIRow+1;
         int iwidth= endICol-startICol+1;

         // figure out which side has expanded less compared to the original row-col ratios
         // we can only zoom by that much
         float xexpansion= (float)numCol/(float)iwidth;
         float yexpansion= (float)numRow/(float)iheight;
         float zoomfactor= xexpansion;

         if (yexpansion< xexpansion)
         {
            zoomfactor= yexpansion;
         }

         // compute the number of rows and columns left after the zooming
         numICol= (int)Math.round((float)numCol/zoomfactor);
         numIRow= (int)Math.round((float)numRow/zoomfactor);

         // now based on the center of the zoom (center of cluster)
         // estimate the start row and col
         startIRow= (int)Math.round(startCRow+(float)(numCRow/2.0)-(float)(numIRow/2.0));
         startICol= (int)Math.round(startCCol+(float)(numCCol/2.0)-(float)(numICol/2.0));

         if (startIRow<0) startIRow=0; //shift image down appropriately to fit
         if (startICol<0) startICol=0; //shift image left to fit appropriately

         // shift image left to fit appropriately, shrink if needed
         int rightBound= startICol+numICol;
         if (rightBound> numCol)
         {
            startICol= startICol- (rightBound-numCol);
            if (startICol<0)
            {
               numICol= numICol+startICol;
               startICol=0;
            }
         }
         // shift image up to fit appropriately, shrink if needed
         int downBound= startIRow+numIRow;
         if (downBound> numRow)
         {
            startIRow= startIRow- (downBound-numRow);
            if (startIRow<0)
            {
               numIRow= numIRow+startIRow;
               startIRow=0;
            }
         }

         // now compute the zoomed pixels by multiplying original pixels by the zoom factor
         fpixWidth= fpixWidth*zoomfactor;
         fpixHeight= fpixHeight*zoomfactor;

         int pixWidth= (int)Math.ceil(fpixWidth);
         int pixHeight= (int)Math.ceil(fpixHeight);
         if (pixWidth==0) pixWidth=1;
         if (pixHeight==0) pixHeight=1;

         // first paint whole area with backgronud color
         bg.setColor(background);
         bg.fillRect(XPIXOFFSET,YPIXOFFSET, imgWidth, imgHeight);
         // change border font to new color
         etched= BorderFactory.createEtchedBorder();
         figureBorder= BorderFactory.createTitledBorder(etched, newTitleStr, TitledBorder.LEADING, TitledBorder.TOP, this.getFont(), new Color(200,200,200));
         this.setBorder(figureBorder);

         // now plot HMA clusters in different colors but only the visible area
         for (int i=startIRow+numNonDense; i<(startIRow+numIRow+numNonDense); i++)
         {
            int idx= sortedTreeIdx[i];
            for (int j=startICol; j<(startICol+numICol); j++)
            {
               int curLabel= hmaImageData[idx][j];
               if (curLabel>0)
               {
                  bg.setColor(new Color(red[curLabel-1], green[curLabel-1], blue[curLabel-1]));
                  int xloc=j-startICol;
                  int yloc= i-startIRow-numNonDense;
                  bg.fillRect((int)Math.floor(fpixWidth*(float)xloc)+XPIXOFFSET, Math.round(fpixHeight*(yloc))+YPIXOFFSET, pixWidth, pixHeight);
               }
            }
         }

         // now draw the selected cluster at the end to make sure it gets highlighted correctly
         bg.setColor(Color.WHITE);
         int tipX= (int)Math.round((double)(startCCol+numCCol)*fpixWidth);
         int midY= (int)Math.round((startCRow+((double)numCRow/2.0))*fpixHeight);
         bg.drawRect((int)Math.floor(fpixWidth*(float)(startCCol-startICol))+XPIXOFFSET, (int)Math.floor(fpixHeight*(startCRow-startIRow))+YPIXOFFSET,
                      (int)Math.ceil(numCCol*fpixWidth),  (int)Math.ceil(numCRow*fpixHeight));

         img.flush();
         bg.dispose();
      }
      else
      {
         retVal= false;
      }
      return retVal;
   }


   // figures out the HDS B&W image from the HDS label matrix
   // returns true if successful
   public boolean setHDSImage (int[][] hdsImageData, int[] sortedTreeIdx)
   {
      boolean retVal= true;
      isHMAFigure= false;
      if ((hdsImageData!=null) && (sortedTreeIdx!=null))
      {
         // find the number of dense points at the largest (first) level
         int numPt= hdsImageData.length;
         int numNonDense=0; //maximum no. of rows of non-dense points, we don't plot non-dense points
         
         // after sorting at the first level all the least dense points go on the top
         // we don't need to plot those points that are non-dense first level
         int leastDensePtLabel = hdsImageData[sortedTreeIdx[numNonDense]][0];
         
         while ((numNonDense< numPt) && (leastDensePtLabel==0)) // short-circuted check assumed
         {
            leastDensePtLabel = hdsImageData[sortedTreeIdx[numNonDense]][0];
            numNonDense++;
         }
         // max no. of dense points is numRow, and we plot only these
         int numRow= numPt- numNonDense;

         int numCol= hdsImageData[0].length;

         int imgWidth= this.getWidth()-XPIXOFFSET;
         int imgHeight= this.getHeight()-YPIXOFFSET+2;

         // create the image now for attaching and showing
         img= createImage(imgWidth, imgHeight);

         // temporary panel for creating image
         Graphics bg= img.getGraphics();

         Color black= new Color(0,0,0);
         bg.setColor(black);
         // compute now width and height of each pixel to draw
         float fpixWidth= (float)imgWidth/(float)numCol;
         float fpixHeight= (float)imgHeight/(float)numRow;
         int pixWidth= (int)Math.ceil(fpixWidth);
         int pixHeight= (int)Math.ceil(fpixHeight);
         if (pixWidth==0) pixWidth=1;
         if (pixHeight==0) pixHeight=1;

         // now draw the image, with each non-zero value as a black spot
         for (int i=numNonDense; i<numPt; i++)
         {
            int idx= sortedTreeIdx[i];
            for (int j=0; j<numCol; j++)
            {
               if (hdsImageData[idx][j]>0)
               {
                  bg.fillRect(Math.round(fpixWidth*j)+XPIXOFFSET, Math.round(fpixHeight*(i-numNonDense))+YPIXOFFSET, pixWidth, pixHeight);
               }
            }
         }
         img.flush();
         bg.dispose();
      }
      else
      {
         retVal= false;
      }
      return retVal;
   }

   // Resizable figure
   public boolean setHDSImage (int[][] hdsImageData, int[] sortedTreeIdx, JFrame frameIn)
   {
      boolean retVal= true;

      if ((hdsImageData!=null) && (sortedTreeIdx!=null))
      {
         Toolkit tk= Toolkit.getDefaultToolkit();
         Dimension d= tk.getScreenSize();
         int screenHeight= d.height;
         int screenWidth= d.width;
         int frameWidth= frameIn.getWidth();
         int frameHeight= frameIn.getHeight();
         int frameX= frameIn.getX();
         int frameY= frameIn.getY();

         // compute mamximum width and height of image possible
         int increaseX= Math.round((screenWidth- frameWidth))-30;
         int increaseY= Math.round((screenHeight- frameHeight))-50;

         // validate
         if (increaseX<0) increaseX=0;
         if (increaseY<0) increaseY=0;

         int numRow= hdsImageData.length;
         int numCol= hdsImageData[0].length;

         int imgWidth= this.getWidth()-2+ increaseX;
         int imgHeight= this.getHeight()-2+ increaseY;

         // create the image now for attaching and showing
         img= createImage(imgWidth, imgHeight);

         // temporary panel for creating image
         Graphics bg= img.getGraphics();

         Color black= new Color(0,0,0);
         bg.setColor(black);
         // compute now width and height of each pixel to draw
         float fpixWidth= (float)imgWidth/(float)numCol;
         float fpixHeight= (float)imgHeight/(float)numRow;
         int pixWidth= Math.round(fpixWidth);
         int pixHeight= Math.round(fpixHeight);
         if (pixWidth==0) pixWidth=1;
         if (pixHeight==0) pixHeight=1;

         // now draw the image, with each non-zero value as a black spot
         for (int i=0; i<numRow; i++)
         {
            int idx= sortedTreeIdx[i];
            for (int j=0; j<numCol; j++)
            {
               if (hdsImageData[idx][j]>0)
               {
                  bg.fillRect(Math.round(fpixWidth*j)+2, Math.round(fpixHeight*i)+2, pixWidth, pixHeight);
               }
            }
         }
         img.flush();
         bg.dispose();
      }
      else
      {
         retVal= false;
      }
      return retVal;
   }

   // default image
   public void setImage(Image imgIn)
   {
      img= imgIn;
   }

   public void paintComponent (Graphics g)
   {
      super.paintComponent(g);
      if (img!=null)
      {
         g.drawImage(img,0,0, null);
      }
   }
};
