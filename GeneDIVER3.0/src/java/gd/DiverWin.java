package gd;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;

import javax.swing.*;
import javax.swing.event.ChangeListener;
import javax.swing.event.ListSelectionListener;
import javax.swing.event.ListSelectionEvent;

import javax.swing.event.ChangeEvent;
import java.io.IOException;
import javax.swing.text.MaskFormatter;
import javax.swing.JFormattedTextField;
import javax.swing.text.NumberFormatter;
import java.text.NumberFormat;
import java.awt.*;
import java.awt.event.*;

class DiverGUI implements ActionListener,ChangeListener,MouseListener,ListSelectionListener
{
  public static final String DIVER_VERSION= "Gene DIVER 2.0";

  // cluster label popper
  JPopupMenu mainHMApopup= null;

  // DIVER program object
  Diver theDiver= null;

  public static final int FILENAMETEXTSIZE=15;
  public static final String CONFIGFILEEXTENSION=".cfg";
  public static final int SPLASHTIME=2000;
  public static final String SPLASHIMAGENAME="graysplash.gif";

  // Parameters input to Auto-HDS clustering
  // are staged here

  String dataDir=".";

  // CUSTOM CONFIGURATION INFO SAVER and LOADER
  ModelSchema modelConfig= null;

  protected boolean fileSelected= false;

  String delimiter=",";

  String dataFile=null, dataDescriptionFile=null;

  // load and store points descriptions for the GUI usage, if available
  String [] pointsDescriptions= null;
  
  // load and store points web URLs if found any, for the GUI usage
  String [] pointsURLs = null;
  
  // true when distance matrix passed in
  boolean matrixFlag= false;

  // true if user wants only Density Shaving not Auto HDS
  boolean onlyDS= false;

  // forces auto-hds results to become invalid when set to true
  // set when HDS executed
  boolean autohdsInvalid= true;

  // skip first data line
  boolean skipFirstDataLine= true;
  
  // skip input data file reading and clustering only processes existing hds 
  // clustering
  boolean skipDataFileClustering = false;

  // default distance measure is euclidean
  int distMeasureVal= Diver.EUCLIDEAN;

  // name of the class label column
  String classCol=null, classColIdxStr=null;
  // index of the class label column
  int classColIdx=-1;

  int neps=-1, runtSize=-1;
  double fshave=-1, rshave=-1;


  int numPt=-2;
  int numDescriptions=-1;
  // GUI objects associated with Diver /////

  // main container
  JFrame frame=null;

  JTabbedPane tabbedPane = null;

  JPanel dataPanel=null, clustPanel=null, systemPanel=null, browsePanel=null, aboutPanel=null;
  HDSImage figurePanel= null, zoomFigurePanel=null;

  // layout managers for the the two tabs
  GridBagLayout datalayout= new GridBagLayout();
  GridBagLayout clustlayout= new GridBagLayout();
  GridBagLayout browselayout= new GridBagLayout();
  GridBagLayout systemlayout= new GridBagLayout();
  GridBagLayout aboutlayout= new GridBagLayout();

  GridBagConstraints c= new GridBagConstraints();

  JRadioButton classColName=null, classColIndex=null, classColNone=null;
  JRadioButton dataFormatDistMat=null, dataFormatVectorSpace=null, dataFormatGraph=null;
  JRadioButton sqEuclideanRadio=null, pearsonRadio=null, cosineRadio=null, infDistRadio=null;
  JRadioButton commaDelimiterRadio=null, spaceDelimiterRadio=null, tabDelimiterRadio=null, otherDelimiterRadio=null;
  JTextField inputFilePathDisp=null, labelFilePathDisp=null, autoFilePathDisp=null, configFilePathDisp=null;
  JTextField classColumnDisp=null, delimiterDisp=null, nepsDisp=null, fshaveDisp=null, rshaveDisp=null;
  JTextField discBufferDisp=null, runtSizeDisp=null;

  JButton fileLoadButton=null, hdsButton=null, autohdsButton=null;
  int browseResultsStatus=0; // 0 not ready, 1 ready but not drawn, 2 ready and drawn
  JButton exitButton=null;

  JButton leftButton=null, rightButton=null, plusButton=null, minusButton=null;
  ImageIcon lefticon=null, righticon=null, plusicon=null, minusicon=null;

  JCheckBox skipLineCheckBox=null, browseInternetCheckBox=null, autoZoomCheckBox=null;
  JTextPane dataSummaryDisp= null, currentListedCluster=null, networkPane=null;

  // display the list of HDS clusters in browse window, and the list of points in each cluster
  JList clusterList=null, pointsList= null;
  JScrollPane clusterListPane=null, pointsListPane=null;

  public DiverGUI()
  {
  }

  public JTextField addTextField(String textStr, String tooltip, int numCols, GridBagLayout layoutIn, JPanel panelIn)
  {
     JTextField text= new JTextField(textStr,numCols);
     text.setFont(new Font("Arial", Font.PLAIN, 20));
     if (tooltip.length()>0)
     {
       text.setToolTipText(tooltip);
     }
     // add a listener to process text input on this text field
     text.addActionListener(this);
     layoutIn.setConstraints(text, c);
     panelIn.add(text);
     return text;
  }

  public JFormattedTextField addFormattedTextField(String textStr, String formatStr, String tooltip, GridBagLayout layoutIn, JPanel panelIn)
  {
     MaskFormatter f= null;
     JFormattedTextField text= null;
     try
     {
        f= new MaskFormatter(formatStr);
        text = new JFormattedTextField(f);
        if (tooltip.length()>0)
        {
          text.setToolTipText(tooltip);
        }
        text.setText(textStr);
        text.setColumns(formatStr.length()-1);
        text.setFont(new Font("Arial", Font.PLAIN, 20));
        // add a listener to process text input on this text field
        text.addActionListener(this);
        layoutIn.setConstraints(text, c);
        panelIn.add(text);
     }
     catch (java.text.ParseException e)
     {
        System.err.println("Error creating text field"+ textStr);
        System.err.println("Formatter text "+ formatStr+" is invalid");
     }
     return text;
  }

  public JFormattedTextField addFormattedNumberField(String textStr, NumberFormat fIn, String tooltip, GridBagLayout layoutIn, JPanel panelIn)
  {
     NumberFormatter nf= null;
     JFormattedTextField text= null;
//     try
  //   {
        nf= new NumberFormatter(fIn);
        text = new JFormattedTextField(nf);
        text.setText(textStr);
        if (tooltip.length()>0)
        {
          text.setToolTipText(tooltip);
        }
        text.setColumns(fIn.getMaximumFractionDigits()+fIn.getMaximumIntegerDigits()+1);
        text.setFont(new Font("Arial", Font.PLAIN, 20));
        // add a listener to process text input on this text field
        text.addActionListener(this);
        layoutIn.setConstraints(text, c);
        panelIn.add(text);
//     }
/*     catch (java.text.ParseException e)
     {
        System.err.println("Error creating number field"+ textStr);
     }*/
     return text;
  }

  public JTextArea addText(String textStr, int numRows, GridBagLayout layoutIn, JPanel panelIn)
  {
    JTextArea text= new JTextArea(textStr,numRows,textStr.length());
    text.setEditable(false);
    text.setFont(new Font("Arial", Font.PLAIN, 20));
    layoutIn.setConstraints(text, c);
    panelIn.add(text);
    return text;
  }

  public JList addList(int numVisible, boolean forceSingleSelection,  GridBagLayout layoutIn, JPanel panelIn)
  {
    JList list= new JList();
    if (forceSingleSelection) // not allow users to select multiple itmes in the list
    {
       list.setSelectionMode(ListSelectionModel.SINGLE_SELECTION);
    }
    list.setVisibleRowCount(numVisible);
    list.setFont(new Font("Arial", Font.PLAIN, 20));
    layoutIn.setConstraints(list, c);
    panelIn.add(list);
    return list;
  }

  public JList makeList(int numVisible, String tooltip, boolean forceSingleSelection)
  {
    JList list= new JList();
    if (forceSingleSelection) // not allow users to select multiple itmes in the list
    {
       list.setSelectionMode(ListSelectionModel.SINGLE_SELECTION);
    }

    if (tooltip.length()>0)
    {
       list.setToolTipText(tooltip);
    }

    list.setVisibleRowCount(numVisible);
    list.setFont(new Font("Arial", Font.PLAIN, 15));
    return list;
  }

  public JScrollPane addScrollList(JList listIn, GridBagLayout layoutIn, JPanel panelIn)
  {
    JScrollPane paneOut= new JScrollPane(listIn);
    // add a listener to process text input on this text field
    listIn.addListSelectionListener(this);
    layoutIn.setConstraints(paneOut, c);
    panelIn.add(paneOut);
    paneOut.setHorizontalScrollBarPolicy(JScrollPane.HORIZONTAL_SCROLLBAR_ALWAYS);
    paneOut.setVerticalScrollBarPolicy(JScrollPane.VERTICAL_SCROLLBAR_ALWAYS);
    return paneOut;
  }

  public JTextPane addHtml(String htmlStr, int numRows, GridBagLayout layoutIn, JPanel panelIn)
  {
    JTextPane text= new JTextPane();
    text.setContentType("text/html; charset=EUC-JP");
    text.setEditable(false);
    text.setText(htmlStr);
    layoutIn.setConstraints(text, c);
    panelIn.add(text);
    return text;
  }

  public JButton addButton(String name, int mnemonic, String tooltip, GridBagLayout layoutIn, JPanel panelIn)
  {
    JButton button= new JButton();
    button.setText(name);
    if (tooltip.length()>0)
    {
      button.setToolTipText(tooltip);
    }
    // buttons hotkey
    if (mnemonic!=-1)
    {
       button.setMnemonic(mnemonic);
    }
    // add a listener to process this button's click
    button.addActionListener(this);
    layoutIn.setConstraints(button, c);
    panelIn.add(button);
    return button;
  }

  public JButton addIconButton(ImageIcon icon, String tooltip, GridBagLayout layoutIn, JPanel panelIn)
  {
    JButton button= new JButton();
    button.setIcon(icon);
    if (tooltip.length()>0)
    {
      button.setToolTipText(tooltip);
    }

    // add a listener to process this button's click
    button.addActionListener(this);
    layoutIn.setConstraints(button, c);
    panelIn.add(button);
    return button;
  }

  public JRadioButton addRadioButton(String name, boolean status, ButtonGroup g, GridBagLayout layoutIn, JPanel panelIn)
  {
     JRadioButton button= new JRadioButton(name, status);
     g.add(button);
     button.addActionListener(this);
     layoutIn.setConstraints(button, c);
     panelIn.add(button);
     return button;
  }

  public JCheckBox addCheckBox(String name, String tooltip, boolean status, GridBagLayout layoutIn, JPanel panelIn)
  {
     JCheckBox box= new JCheckBox(name, status);
     if (tooltip.length()>0)
     {
        box.setToolTipText(tooltip);
     }
     box.addActionListener(this);
     layoutIn.setConstraints(box, c);
     panelIn.add(box);
     return box;
  }

  // helper function for initializing the grid constraints
  public void setGridConstraints(int gridx, int gridy, int gridwidth, int gridheight, int fillVal)
  {
     c.gridx= gridx;
     c.gridy= gridy;
     c.gridwidth= gridwidth;
     c.gridheight= gridheight;
     c.fill= fillVal;
     c.weightx=0;
     c.weighty=0;
     c.anchor= GridBagConstraints.WEST;
  }

  public void init()
  {
     //Create and set up the window.
     frame = new JFrame(DIVER_VERSION);


     Image icon = Toolkit.getDefaultToolkit().getImage("./images/simpleicon.gif");

     frame.setIconImage(icon);

     Splash w= new Splash("./images/"+SPLASHIMAGENAME,frame,SPLASHTIME);

     frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
     frame.setFont(new Font("SansSerif", Font.PLAIN, 15));

     // initialize the tabbed pane
     dataPanel= new JPanel(datalayout, true);
     clustPanel= new JPanel(clustlayout, true);
     browsePanel= new JPanel(browselayout, true);
     systemPanel= new JPanel(systemlayout, true);
     aboutPanel= new JPanel(aboutlayout, true);

     tabbedPane= new JTabbedPane();
     tabbedPane.addTab("Data", dataPanel);
     tabbedPane.setMnemonicAt(0, KeyEvent.VK_D);
     tabbedPane.setToolTipTextAt(0,"Specify data for clustering");

     tabbedPane.addTab("Cluster", clustPanel);
     tabbedPane.setMnemonicAt(1, KeyEvent.VK_C);
     tabbedPane.setToolTipTextAt(1,"Generate Auto-HDS clustering");

     tabbedPane.addTab("Browse Clustering", browsePanel);
     tabbedPane.setMnemonicAt(2, KeyEvent.VK_B);
     tabbedPane.setToolTipTextAt(2,"Browse Auto-HDS clustering results");

     tabbedPane.addTab("System", systemPanel);
     tabbedPane.setMnemonicAt(3, KeyEvent.VK_S);
     tabbedPane.setToolTipTextAt(3,"System settings");

     tabbedPane.addTab("About", aboutPanel);
     tabbedPane.setMnemonicAt(4, KeyEvent.VK_A);
     tabbedPane.setToolTipTextAt(4,"About Gene DIVER");

     tabbedPane.addChangeListener(this);

     frame.getContentPane().add(tabbedPane, BorderLayout.CENTER);
     c.insets = new Insets(10, 10, 10, 10);

     int ROWID=0;
     //////////////////////////////////////////////////// DATA TAB ///////////////////////////
     setGridConstraints(0,ROWID,2,1,GridBagConstraints.NONE);
     addHtml("<font size=5 color=ff0000>Input Data File:</font>", 1, datalayout, dataPanel);

     setGridConstraints(2,ROWID,4,1,GridBagConstraints.HORIZONTAL);
     inputFilePathDisp= addTextField("", "", DiverGUI.FILENAMETEXTSIZE, datalayout, dataPanel);
     inputFilePathDisp.setEditable(false);

     setGridConstraints(6,ROWID,1,1,GridBagConstraints.NONE);
     fileLoadButton= addButton("Browse",KeyEvent.VK_B, "Browse data file", datalayout, dataPanel);

     ///////////////////////////////////////////////////////
     ROWID= ROWID+1;

     setGridConstraints(0,ROWID,2,1,GridBagConstraints.NONE);
     addHtml("<font size=5 color=ff0000>Auto File:</font>", 1, datalayout, dataPanel);

     setGridConstraints(2,ROWID,5,1,GridBagConstraints.HORIZONTAL);
     autoFilePathDisp= addTextField("", "Auto-HDS clustering hierarchy output file", DiverGUI.FILENAMETEXTSIZE, datalayout, dataPanel);
     autoFilePathDisp.setEditable(false);

     ///////////////////////////////////////////////////////
     ROWID= ROWID+1;

     setGridConstraints(0,ROWID,2,1,GridBagConstraints.NONE);
     addHtml("<font size=5 color=ff0000>Model Config File:</font>", 1, datalayout, dataPanel);

     setGridConstraints(2,ROWID,5,1,GridBagConstraints.HORIZONTAL);
     configFilePathDisp= addTextField("", "Last configuration for clustering the data file specified stored here.", DiverGUI.FILENAMETEXTSIZE, datalayout, dataPanel);
     configFilePathDisp.setEditable(false);

     ///////////////////////////////////////////////////////
     ROWID= ROWID+1;
     setGridConstraints(0,ROWID,2,1,GridBagConstraints.NONE);
     addHtml("<font size=5 color=ff0000>Label File:</font>", 1, datalayout, dataPanel);

     setGridConstraints(2,ROWID,5,1,GridBagConstraints.HORIZONTAL);
     labelFilePathDisp= addTextField("", "Auto-HDS final cluster labels output file", DiverGUI.FILENAMETEXTSIZE, datalayout, dataPanel);
     labelFilePathDisp.setEditable(false);

     ///////////////////////////////////////////////////////
     ROWID= ROWID+1;
     ButtonGroup dataFormatRadio= new ButtonGroup();

     setGridConstraints(0,ROWID,2,1,GridBagConstraints.NONE);
     addHtml("<font size=5 color=ff0000>Data Format:</font>", 1, datalayout, dataPanel);

     setGridConstraints(2,ROWID,1,1,GridBagConstraints.NONE);
     skipLineCheckBox= addCheckBox("Skip first data line", "Check this if your data file has column labels in the first row", true, datalayout, dataPanel);

     setGridConstraints(4,ROWID,1,1,GridBagConstraints.NONE);
     dataFormatVectorSpace= addRadioButton("Vector Space", true, dataFormatRadio, datalayout, dataPanel);

     setGridConstraints(5,ROWID,1,1,GridBagConstraints.NONE);
     dataFormatDistMat= addRadioButton("Distance Matrix", false, dataFormatRadio, datalayout, dataPanel);
    
     setGridConstraints(6,ROWID,1,1,GridBagConstraints.NONE);
     dataFormatGraph= addRadioButton("Graph", false, dataFormatRadio, datalayout, dataPanel);

     
     ///////////////////////////////////////////////////////
     ROWID= ROWID+1;
     ButtonGroup delimiterRadioGroup= new ButtonGroup();

     setGridConstraints(0,ROWID,2,1,GridBagConstraints.NONE);
     addHtml("<font size=5 color=ff0000>Delimiter:</font>", 1, datalayout, dataPanel);

     setGridConstraints(2,ROWID,1,1,GridBagConstraints.NONE);
     commaDelimiterRadio= addRadioButton("Comma", true, delimiterRadioGroup, datalayout, dataPanel);

     setGridConstraints(3,ROWID,1,1,GridBagConstraints.NONE);
     spaceDelimiterRadio= addRadioButton("Space", true, delimiterRadioGroup, datalayout, dataPanel);

     setGridConstraints(4,ROWID,1,1,GridBagConstraints.NONE);
     tabDelimiterRadio= addRadioButton("Tab", true, delimiterRadioGroup, datalayout, dataPanel);

     setGridConstraints(5,ROWID,1,1,GridBagConstraints.HORIZONTAL);
     otherDelimiterRadio= addRadioButton("Other", true, delimiterRadioGroup, datalayout, dataPanel);

     setGridConstraints(6,ROWID,1,1,GridBagConstraints.HORIZONTAL);
     delimiterDisp= addFormattedTextField(",", "*", "delimiting character separating fields in input data file", datalayout, dataPanel);
     delimiterDisp.setEditable(true);

     ///////////////////////////////////////////////////////
     ROWID= ROWID+1;
     setGridConstraints(0,ROWID,2,1,GridBagConstraints.NONE);
     addHtml("<font size=5 color=ff0000>Distance Measure:</font>", 1, datalayout, dataPanel);

     ButtonGroup distanceRadio= new ButtonGroup();
     setGridConstraints(2,ROWID,1,1,GridBagConstraints.NONE);
     sqEuclideanRadio= addRadioButton("Sq. Euclidean", true, distanceRadio, datalayout, dataPanel);

     setGridConstraints(3,ROWID,1,1,GridBagConstraints.NONE);
     pearsonRadio= addRadioButton("(1-Pearson Correlation)", false, distanceRadio, datalayout, dataPanel);

     setGridConstraints(4,ROWID,1,1,GridBagConstraints.NONE);
     cosineRadio= addRadioButton("(1-Cosine Similarity)", false, distanceRadio, datalayout, dataPanel);

     setGridConstraints(5,ROWID,1,1,GridBagConstraints.NONE);
     infDistRadio= addRadioButton("Inferred", false, distanceRadio, datalayout, dataPanel);

     ///////////////////////////////////////////////////////
     ROWID= ROWID+1;
     setGridConstraints(0,ROWID,2,1,GridBagConstraints.NONE);
     addHtml("<font size=5 color=ff0000>Class Label Column:</font>", 1, datalayout, dataPanel);

     setGridConstraints(2,ROWID,1,1,GridBagConstraints.HORIZONTAL);
     classColumnDisp= addTextField("", "Name or index(starting from 0) of the column representing class labels in input data file", 10, datalayout, dataPanel);
     classColumnDisp.setEditable(true);

     ButtonGroup classColRadio= new ButtonGroup();
     setGridConstraints(3,ROWID,1,1,GridBagConstraints.NONE);
     classColNone= addRadioButton("Not Available", true, classColRadio, datalayout, dataPanel);

     setGridConstraints(4,ROWID,1,1,GridBagConstraints.NONE);
     classColName= addRadioButton("Name specified", false, classColRadio, datalayout, dataPanel);

     setGridConstraints(5,ROWID,1,1,GridBagConstraints.NONE);
     classColIndex= addRadioButton("Index specified", false, classColRadio, datalayout, dataPanel);

     //////////////////////////////////////////////////// CLUSTER TAB ///////////////////////////
     ROWID= 0;
     int TEXTWIDTH=10;

     setGridConstraints(0,ROWID,1,1,GridBagConstraints.NONE);
     addHtml("<font size=5 color='ff0000'>Data Summary:</font>", 1, clustlayout, clustPanel);

     // this is where we put the figure, holder panel for now
     figurePanel= new HDSImage("HDS Cluster Tree");
     setGridConstraints(TEXTWIDTH,ROWID,5,15,GridBagConstraints.BOTH);
     c.weightx=0.5; // THIS ALLOWS THE FIGURE PART TO TAKE UP ALL THE SLACK EXTRA SPACE
     clustlayout.setConstraints(figurePanel, c);
     figurePanel.addMouseListener(this);
     figurePanel.setToolTipText("Left-click on a cluster to see more info");
     clustPanel.add(figurePanel);

     ////////////////////////////////////////////////////////////////////////////////////////////
     ROWID= ROWID+1;
     setGridConstraints(0,ROWID,TEXTWIDTH,10,GridBagConstraints.BOTH);
     dataSummaryDisp= addHtml(getHtmlDataSummary(), 10, clustlayout, clustPanel);

     ////////////////////////////////////////////////////////////////////////////////////////////
     ROWID= ROWID+10;
     setGridConstraints(0,ROWID,1,1,GridBagConstraints.NONE);
     addHtml("<font size=5 color='ff0000'>n_eps(>1):</font>", 1, clustlayout, clustPanel);

     setGridConstraints(1,ROWID,1,1,GridBagConstraints.NONE);
     NumberFormat f1= NumberFormat.getInstance();
     f1.setMaximumFractionDigits(0);
     f1.setMaximumIntegerDigits(4);
     nepsDisp= addFormattedNumberField("20", f1, "minimum no. of pts in nbrhood for density estimation", clustlayout, clustPanel);

     setGridConstraints(TEXTWIDTH-1,ROWID,1,1,GridBagConstraints.NONE);
     hdsButton= addButton("Cluster(HDS)", KeyEvent.VK_H, "Cluster using Hierarchical Density Shaving", clustlayout, clustPanel);

     ////////////////////////////////////////////////////////////////////////////////////////////
     ROWID= ROWID+1;
     setGridConstraints(0,ROWID,1,1,GridBagConstraints.NONE);
     addHtml("<font size=5 color='ff0000'>fshave(0.00-0.99):</font>", 1, clustlayout, clustPanel);

     setGridConstraints(1,ROWID,1,1,GridBagConstraints.NONE);
     NumberFormat f= NumberFormat.getInstance();
     f.setMaximumFractionDigits(2);
     f.setMaximumIntegerDigits(0);
     fshaveDisp= addFormattedNumberField("0.3", f, "Fraction of points to shave off in the first HDS iteration", clustlayout, clustPanel);

     setGridConstraints(TEXTWIDTH-1,ROWID,1,1,GridBagConstraints.NONE);
     autohdsButton= addButton("Auto-HDS", KeyEvent.VK_A, "Automatically select clusters from HDS hierarchy", clustlayout, clustPanel);
     autohdsButton.setEnabled(false);

     ////////////////////////////////////////////////////////////////////////////////////////////
     ROWID= ROWID+1;
     setGridConstraints(0,ROWID,1,1,GridBagConstraints.NONE);
     addHtml("<font size=5 color='ff0000'>rshave(0.01-0.99):</font>", 1, clustlayout, clustPanel);

     setGridConstraints(1,ROWID,1,1,GridBagConstraints.NONE);
     rshaveDisp= addFormattedNumberField("0.05", f, "Fraction of remaining points to shave off in each iteration after the first iteration", clustlayout, clustPanel);

     ////////////////////////////////////////////////////////////////////////////////////////////
     ROWID= ROWID+1;
     setGridConstraints(0,ROWID,1,1,GridBagConstraints.NONE);
     addHtml("<font size=5 color='ff0000'>npart(0 to neps-1):</font>", 1, clustlayout, clustPanel);

     setGridConstraints(1,ROWID,1,1,GridBagConstraints.NONE);
     runtSizeDisp= addFormattedNumberField("1", f1, "Smallest cluster size desired for Auto-HDS, also known as runt size.", clustlayout, clustPanel);

     setGridConstraints(TEXTWIDTH-1,ROWID,1,1,GridBagConstraints.NONE);
     exitButton= addButton("eXit", KeyEvent.VK_X, "Done with clustering, exit Gene Diver", clustlayout, clustPanel);

     //////////////////////////////////////////////////// BROWSE CLUSTERING TAB ///////////////////////////
     ROWID= 0;
     int ROWIDTH=9;
     int COLWIDTH=6;
     int FULLWIDTH=20;

     /////////////////////////////////////////
     // now add the four buttons
     lefticon= new ImageIcon("./images/left.gif");
     righticon= new ImageIcon("./images/right.gif");
     minusicon= new ImageIcon("./images/minus.gif");
     plusicon= new ImageIcon("./images/plus.gif");
     c.weightx=0;
     c.weighty=0;
     c.anchor=c.SOUTHWEST;
     c.fill=c.NONE;
     setGridConstraints(0,ROWID,1,1,GridBagConstraints.BOTH);
     leftButton= addIconButton(lefticon, "a feature coming soon: pan left", browselayout, browsePanel);

     setGridConstraints(1,ROWID,1,1,GridBagConstraints.BOTH);
     rightButton= addIconButton(righticon, "a feature coming soon: pan right", browselayout, browsePanel);

     setGridConstraints(2,ROWID,1,1,GridBagConstraints.BOTH);
     minusButton= addIconButton(minusicon, "a feature coming soon: zoom out", browselayout, browsePanel);

     setGridConstraints(3,ROWID,1,1,GridBagConstraints.BOTH);
     plusButton= addIconButton(plusicon, "a feature coming soon: zoom in", browselayout, browsePanel);

     // disable the zoom buttons for now- not implemented yet
     leftButton.setEnabled(false);
     rightButton.setEnabled(false);
     minusButton.setEnabled(false);
     plusButton.setEnabled(false);

     setGridConstraints(4,ROWID,1,2,GridBagConstraints.BOTH);
     browseInternetCheckBox= addCheckBox("Browse Point web URLs", "Check this if you want to open URLS associated with data points.", false, browselayout, browsePanel);

     setGridConstraints(5,ROWID,1,2,GridBagConstraints.BOTH);
     autoZoomCheckBox= addCheckBox("Auto Zoom", "Check this if you want to zoom to selected cluster automatically", false, browselayout, browsePanel);

     ROWID=ROWID+1;
     // this is where we put the figure, holder panel for now
     zoomFigurePanel= new HDSImage("Cluster Tree Browser");
     zoomFigurePanel.setSize(200,200);
     setGridConstraints(0,ROWID,COLWIDTH,FULLWIDTH-1,GridBagConstraints.BOTH);
     c.weightx=0.5; // THIS ALLOWS THE FIGURE PART TO TAKE UP ALL THE SLACK EXTRA SPACE
     c.weighty=0.5;
     browselayout.setConstraints(zoomFigurePanel, c);
     zoomFigurePanel.addMouseListener(this);
     zoomFigurePanel.setToolTipText("Select a cluster from the list to zoom to.");
     browsePanel.add(zoomFigurePanel);

     ////////////////////////////////////////////////////////////////////////////////////////////
     ROWID= ROWID+ROWIDTH;

     setGridConstraints(COLWIDTH,ROWID, 4,1,GridBagConstraints.NONE);
     addHtml("<font size=5 color='ff0000'>Top Clust(Stab.1%Rt):</font>", 1, browselayout, browsePanel);

     setGridConstraints(COLWIDTH+4,ROWID, 4,1,GridBagConstraints.NONE);
     currentListedCluster= addHtml("<font size=5 color='ff0000'>Points in Cluster:</font>", 1, browselayout, browsePanel);


     ROWID= ROWID+1;
     setGridConstraints(COLWIDTH,ROWID,4,FULLWIDTH-ROWID,GridBagConstraints.BOTH);

     ROWID= ROWID+1;
     clusterList= makeList(5, "Right click to open FunSpec", true);
     clusterListPane= addScrollList(clusterList, browselayout, browsePanel);
     String[] dummyData= {"          ","","","","",""};
     clusterList.setListData(dummyData);
     clusterList.addMouseListener(this);

     c.weightx=0.5;
     setGridConstraints(COLWIDTH+4,ROWID,4,FULLWIDTH-ROWID,GridBagConstraints.BOTH);
     pointsList= makeList(5, "Select a point to browse", true);
     pointsList.setListData(dummyData);
     pointsListPane= addScrollList(pointsList, browselayout, browsePanel);
     pointsList.addMouseListener(this);

     //////////////////////////////////////////////////// SYSTEM TAB ///////////////////////////
     ROWID=0;
     setGridConstraints(0,ROWID,1,1,GridBagConstraints.NONE);
     addHtml("<font size=5 color='ff0000'>DISC BUFFER (Megabytes):</font>", 1, systemlayout, systemPanel);

     setGridConstraints(1,ROWID,1,1,GridBagConstraints.NONE);
     f= NumberFormat.getInstance();
     f.setMaximumFractionDigits(0);
     f.setMaximumIntegerDigits(2);
     discBufferDisp= addFormattedNumberField((""+Math.round(Diver.DEFAULT_DISC_BUFFER/1000000)), f, "Set larger size for reading/writing data to disk efficiently.", systemlayout, systemPanel);


     //////////////////////////////////////////////////// ABOUT TAB ///////////////////////////
     ROWID=0;
     File workingDir= (new File ("."));
     String workingDirStr= workingDir.getAbsolutePath();
     workingDirStr= workingDirStr.substring(0,workingDirStr.length()-1);
     String splashurl= "file:///"+workingDirStr+"/images/"+SPLASHIMAGENAME;

     setGridConstraints(0,ROWID,1,1,GridBagConstraints.BOTH);
     addHtml("<img src=\""+splashurl+"\" height=400 width=400>", 1, aboutlayout, aboutPanel);

     setGridConstraints(1,ROWID,1,1,GridBagConstraints.BOTH);
     // take up all the extra slack space
     c.weightx=0.5;
     c.weighty=0.5;

     addHtml("Copyright(c) by Gunjan Gupta, gunjan@iname.com"
     +"<br>Based partly on research supported by NSF grants IIS-0325116 and IIS-0307792 & with funding from Lightsphere AI Inc. "
     +"<br>Other contributors: Kris McGary, Insuk Lee , Alexander Liu and Joydeep Ghosh, Andrew Galloway, Neil Gupta, Alex Mallen"
     +"<br><br>This software is available for free for commercial and non-commercial purposes as long "
     +"<br>as this copyright notice appears in any application, and due credit is given where appropriate. "
     +"<br>The software is provided as is, without any expectation of warranty or support. Please send "
     +"<br>an email to business@lightsphereai.com for reporting bugs or suggestions for new features.</font>"
     , 1, aboutlayout, aboutPanel);

     //Display the window.
     frame.pack();
     goodCenterFrameToScreen(frame);

     frame.setVisible(true);
     frame.setResizable(false);
  }

  // centers frame to user screen
  public void centerFrameToScreen(JFrame frameIn)
  {
     Toolkit tk= Toolkit.getDefaultToolkit();
     Dimension d= tk.getScreenSize();
     int screenHeight= d.height;
     int screenWidth= d.width;
     int frameWidth= frameIn.getWidth();
     int frameHeight= frameIn.getHeight();
     int frameX= frameIn.getX();
     int frameY= frameIn.getY();
     int newFrameX= Math.round((screenWidth- frameWidth)/2);
     int newFrameY= Math.round((screenHeight- frameHeight)/2);
     frameIn.setLocation(newFrameX, newFrameY);
  }

  // puts frame at a "good" position on user screen
  // 1/3rd spacing shifted from top and centered left to right
  public void goodCenterFrameToScreen(JFrame frameIn)
  {
     Toolkit tk= Toolkit.getDefaultToolkit();
     Dimension d= tk.getScreenSize();
     int screenHeight= d.height;
     int screenWidth= d.width;
     int frameWidth= frameIn.getWidth();
     int frameHeight= frameIn.getHeight();
     int frameX= frameIn.getX();
     int frameY= frameIn.getY();
     int newFrameX= Math.round((screenWidth- frameWidth)/2);
     int newFrameY= Math.round((screenHeight- frameHeight)/3);
     frameIn.setLocation(newFrameX, newFrameY);
  }

  public String getHtmlDataSummary()
  {
     StringBuffer dataSummary= new StringBuffer("<font size=4>");
     if (dataFile== null)
     {
        dataSummary.append("<b>Input data file:</b> Not Specified<br>");
        dataSummary.append("<b>Auto HDS clustering tree file</b>: Not Specified<br>");
        dataSummary.append("<b>Auto HDS cluster labels file</b>: Not Specified<br>");
     }
     else
     {
        dataSummary.append("<b>Input data file:</b> "+ dataFile+"<br>");
        dataSummary.append("<b>Auto HDS clustering tree file:</b> "+ autoFilePathDisp.getText()+"<br>");
        dataSummary.append("<b>Auto HDS cluster labels file:</b> "+ labelFilePathDisp.getText()+"<br>");
        if (dataDescriptionFile!=null)
        {
           dataSummary.append("<b>Data description file:</b> "+ dataDescriptionFile);
           dataSummary.append("<br>");
        }
        else
        {
           dataSummary.append("<b>Data description file:</b> Not Found<br>");
        }
     }
     if (matrixFlag)
     {
        dataSummary.append("<b>Input data is a Distance Matrix</b><br>");
     }
     else if (dataFormatGraph.isSelected())
     {
        dataSummary.append("<b>Input data is of pre-clustered Auto-HDS Graph form</b><br>");
     }
     else
     {
        dataSummary.append("<b>Input data is in Vector Space form</b><br>");
        String dispDist= "Sq. Euclidean";
        if (distMeasureVal== Diver.PEARSON)
        {
           dispDist= "(1-Pearson Correlation)";
        }
        if (distMeasureVal== Diver.COSINE)
        {
           dispDist= "(1-Cosine Similarity)";
        }
        dataSummary.append("<b>Distance Measure is:</b>"+ dispDist+"<br>");

        if (delimiter.compareTo(" ")==0)
        {
           dataSummary.append("<b>Delimiter text for parsing data file is the Space character.</b><br>");
        }
        else
        if (delimiter.compareTo(",")==0)
        {
           dataSummary.append("<b>Delimiter text for parsing data file is the \",\" character.</b><br>");
        }
        else
        if (delimiter.compareTo("\t")==0)
        {
           dataSummary.append("<b>Delimiter text for parsing data file is the Tab character.</b><br>");
        }
        else
        {
           dataSummary.append("<b>Delimiter text for parsing data file is the \""+delimiter+"\" character.</b><br>");
        }

        if (skipFirstDataLine)
        {
           dataSummary.append("<b>Will skip reading first data line.</b><br>");

           if (classColNone.isSelected()==false) // something was selected then it should be valid
           {
              if (classCol!=null)
              {
                 dataSummary.append("<b>Class column name:</b> "+classCol+"<br>");
              }
              if (classColIdx>-1)
              {
                 dataSummary.append("<b>Class column index:</b> "+classColIdx+"<br>");
              }
           }
           else
           {
              dataSummary.append("<b>All columns will be used as features.</b><br>");
           }
        }
        else
        {
           classCol=null;
           if (classColNone.isSelected()==false) // something was selected then it should be valid
           {
              if (classColIdx>-1)
              {
                 dataSummary.append("<b>Class column index:</b> "+classColIdx+"<br>");
              }
           }
           else
           {
              dataSummary.append("<b>All columns will be used as features.</b><br>");
           }
        }
     }

     dataSummary.append("</font>");
     return dataSummary.toString();
  }


  // extracts the currently selected parameters from the GUI
  public boolean buildCurrentParams()
  {
    if (dataFile==null)
    {
       JOptionPane.showMessageDialog(null, "Input data file not specified for clustering.", "Error", JOptionPane.ERROR_MESSAGE);
       tabbedPane.setSelectedIndex(0);
       return false;
    }

    String sortedIdxFile= ModelUtil.removeExtension(dataFile)+"_sorted.idx";
    String hdsFile= ModelUtil.removeExtension(dataFile)+".hds";
        
    matrixFlag=false;

    if (dataFormatGraph.isSelected())
    {
        skipDataFileClustering = true;
    }
    else if (dataFormatDistMat.isSelected())
    {
        matrixFlag=true;      
    }
    
    skipFirstDataLine=skipLineCheckBox.isSelected();

    // try to load the data description and count if the number of descriptions are correct
    if (dataDescriptionFile!=null)
    {
      if ((numPt<0) && (!skipDataFileClustering)) // not read before
      {
        numPt= ModelUtil.getNumNonEmptyLines(dataFile, Diver.DEFAULT_DISC_BUFFER, false);
        if (skipFirstDataLine== true)
        {
          numPt= numPt-1;
        }
      }
      if (numDescriptions<0) //check if not read before
      {
        numDescriptions= ModelUtil.getNumNonEmptyLines(dataDescriptionFile, Diver.DEFAULT_DISC_BUFFER, false);
      }
      if ((numDescriptions!= numPt) && (!this.skipDataFileClustering))
      {
        dataDescriptionFile=null; 
        // data description file not found can't browse points on internet
        if (this.browseInternetCheckBox.isSelected())
        {
          this.browseInternetCheckBox.doClick();
        }          
          JOptionPane.showMessageDialog(null, "Valid .dsc points description file not found.", "Information", JOptionPane.INFORMATION_MESSAGE);
      }
      else
      {
        if (pointsDescriptions==null) // not loaded before
        {
          if (numDescriptions > 0)
          {
            
            // set the number of data points using data description file if empty data file is passed for graph clustering 
            if (this.skipDataFileClustering)
            {
              System.out.println("Loading " + numDescriptions +" point descriptions for graph data.");
              numPt = numDescriptions;
              
              // also check to make sure sorted.idx and .hds files required for graph data are present
              int hdsFileLineCount = ModelUtil.getNumNonEmptyLines(hdsFile, Diver.DEFAULT_DISC_BUFFER, false);
              int sortedIdxFileLineCount = ModelUtil.getNumNonEmptyLines(sortedIdxFile, Diver.DEFAULT_DISC_BUFFER, false);
              if (hdsFileLineCount <= 0)
              {
                JOptionPane.showMessageDialog(null, "Required hds file for graph clustering " + hdsFile + " not found!"
                                              , "Error", JOptionPane.ERROR_MESSAGE);
                tabbedPane.setSelectedIndex(0);
                return false;              
              }
              if (sortedIdxFileLineCount <= 0)
              {
                JOptionPane.showMessageDialog(null, "Required sorted idx file for graph clustering " + sortedIdxFile + " not found!"
                                             , "Error", JOptionPane.ERROR_MESSAGE);
                tabbedPane.setSelectedIndex(0);
                return false;              
              }              
            }
            
            // now try loading the descriptions
            String [] pointsDescriptionsAndURLs = ModelUtil.readFileIntoArray(dataDescriptionFile, numPt, true);

            this.pointsDescriptions = new String[pointsDescriptionsAndURLs.length];
            this.pointsURLs = new String[pointsDescriptionsAndURLs.length];
            for (int i =0; i< pointsDescriptionsAndURLs.length; i++)
            {
              String pointDescriptionAndURL = pointsDescriptionsAndURLs[i];
              int splitPoint = pointDescriptionAndURL.indexOf(":");
              if (splitPoint != -1)
              {
                this.pointsDescriptions[i] = pointDescriptionAndURL.substring(0, splitPoint);
                this.pointsURLs[i] = pointDescriptionAndURL.substring(splitPoint+1);
              }
              else
              {
                this.pointsDescriptions[i] = pointDescriptionAndURL;
                this.pointsURLs[i] = null;
              }
            }
        
            // make all of them the same length
            pointsDescriptions= ModelUtil.padToMaxSize (pointsDescriptions, ' ');                      

          }
          else
          {
            JOptionPane.showMessageDialog(null, "Required description file for graph clustering " + dataDescriptionFile + " not found!"
                                        , "Error", JOptionPane.ERROR_MESSAGE);
            tabbedPane.setSelectedIndex(0);
            return false;              
          }          
        }
      }
    }

    if (classColName.isSelected())
    {
       classCol= classColumnDisp.getText();
       try
       {
          classColIdx= ModelUtil.findClassColumnIdx(dataFile, classCol, ",");
          if (classColIdx==-1) // did not find it
          {
             JOptionPane.showMessageDialog(null, "Class label column \""+ classCol+"\" not found in data file."
                                        , "Error", JOptionPane.ERROR_MESSAGE);
             tabbedPane.setSelectedIndex(0);
             return false;
          }

       }
       catch (IOException e)
       {
          JOptionPane.showMessageDialog(null, ("Could not read data file: "+ dataFile)
                                        , "Error", JOptionPane.ERROR_MESSAGE);
          tabbedPane.setSelectedIndex(0);
          return false;
       }
    }
    if (classColIndex.isSelected())
    {
       classColIdxStr= classColumnDisp.getText();
       try
       {
          classColIdx= Integer.parseInt(classColIdxStr);
       }
       catch (NumberFormatException e)
       {
          JOptionPane.showMessageDialog(null, "Invalid Class column index specified.", "Error", JOptionPane.ERROR_MESSAGE);
          tabbedPane.setSelectedIndex(0);
          return false;
       }
    }

    if (matrixFlag== false)
    {
       distMeasureVal= Diver.EUCLIDEAN;
       if (pearsonRadio.isSelected())
       {
          distMeasureVal= Diver.PEARSON;
       }
       if (cosineRadio.isSelected())
       {
          distMeasureVal= Diver.COSINE;
       }
    }

    if (commaDelimiterRadio.isSelected())
    {
       delimiter=",";
    }
    if (tabDelimiterRadio.isSelected())
    {
       delimiter="\t";
    }
    if (spaceDelimiterRadio.isSelected())
    {
       delimiter=" ";
    }
    if (otherDelimiterRadio.isSelected())
    {
       delimiter=delimiterDisp.getText();
    }
     // extract other required fields
     try
     {
        neps= NumberFormat.getInstance().parse(nepsDisp.getText()).intValue();
        if (neps<2)
        {
           JOptionPane.showMessageDialog(null, "neps of "+ neps+ " is too small, is 2 OK?", "Error: neps", JOptionPane.ERROR_MESSAGE);
           nepsDisp.setText("2");
        }
        if (neps>100)
        {
           JOptionPane.showMessageDialog(null, "neps of "+ neps+ " may be too large.", "Warning: neps", JOptionPane.WARNING_MESSAGE);
        }
        // if data file was read make sure neps is reasonable for graph we can't check this here
        if ((numPt> 2) && (neps>numPt))
        {
           JOptionPane.showMessageDialog(null, "neps cannot be more than no. of data points, changing to "+ numPt, "Error: neps", JOptionPane.WARNING_MESSAGE);
           nepsDisp.setText(Integer.toString(numPt));
        }

        fshave= NumberFormat.getInstance().parse(fshaveDisp.getText()).doubleValue();
        if (fshave<0)
        {
           JOptionPane.showMessageDialog(null, "fshave should be >=0", "Error: fshave", JOptionPane.ERROR_MESSAGE);
           fshaveDisp.setText("0.00");
        }
        if (fshave>0.99)
        {
           JOptionPane.showMessageDialog(null, "fshave should be <=0.99", "Error: fshave", JOptionPane.ERROR_MESSAGE);
           fshaveDisp.setText("0.99");
        }
        rshave= NumberFormat.getInstance().parse(rshaveDisp.getText()).doubleValue();
        if (rshave<0.01)
        {
           JOptionPane.showMessageDialog(null, "rshave should be >=0.01", "Error: rshave", JOptionPane.ERROR_MESSAGE);
           rshaveDisp.setText("0.01");
        }
        if (rshave>0.2)
        {
           JOptionPane.showMessageDialog(null, "rshave should be <0.2", "Error: rshave", JOptionPane.ERROR_MESSAGE);
           rshaveDisp.setText("0.2");
        }

        runtSize= NumberFormat.getInstance().parse(runtSizeDisp.getText()).intValue();
        if (runtSize<1)
        {
           JOptionPane.showMessageDialog(null, "runtSize of "+ runtSize+ " is too small, is 1 OK?", "Error: Runt Size", JOptionPane.ERROR_MESSAGE);
           runtSizeDisp.setText("1");
        }
/*        if (runtSize>10)
        {
           JOptionPane.showMessageDialog(null, "runtSize of "+ runtSize+ " may be too large.", "Warning: Runt Size", JOptionPane.WARNING_MESSAGE);
        }*/
     }
     catch (java.text.ParseException e) // no need to throw since already controlled
     {
        return false;
     }
     return true;
  }

  // save current Diver clustering parameters associated with the data file
  public boolean saveCurrentParams()
  {
     boolean retVal= false;
     modelConfig= new ModelSchema();
     // list of parameters that uniquely define clustering configuration
     // for a data file. Add to this any new such parameter
     modelConfig.setProperty("matrixFlag", Boolean.toString(matrixFlag));
     
     // this is only true if graph clustering is ON
     modelConfig.setProperty("skipDataFileClustering", Boolean.toString(skipDataFileClustering));
     modelConfig.setProperty("skipFirstDataLine", Boolean.toString(skipFirstDataLine));
     if (delimiter.compareTo(" ")==0)
     {
        modelConfig.setProperty("delimiter", "SPACE");
     }
     else
     if (delimiter.compareTo("\t")==0)
     {
        modelConfig.setProperty("delimiter", "TAB");
     }
     else
     {
        modelConfig.setProperty("delimiter", delimiter);
     }

     modelConfig.setProperty("distanceMeasure", Integer.toString(distMeasureVal));
     modelConfig.setProperty("classlabel", classColumnDisp.getText());
     modelConfig.setProperty("classColIdx", Integer.toString(classColIdx));
     modelConfig.setProperty("classColName", Boolean.toString(classColName.isSelected()));
     modelConfig.setProperty("neps", Integer.toString(neps));
     modelConfig.setProperty("fshave", Double.toString(fshave));
     modelConfig.setProperty("rshave", Double.toString(rshave));
     modelConfig.setProperty("runtSize", Integer.toString(runtSize));

     try
     {
       FileOutputStream fo= new FileOutputStream(new File(configFilePathDisp.getText()));
       modelConfig.store(fo, "Last Configuration for clustering data file "+ dataFile);
       fo.close();
       retVal= true;
    }
    catch (IOException ie)
    {
      modelConfig=null;
    }
    return retVal;
  }

  // load previous Diver clustering parameters associated with the data file
  public boolean loadPreviousParams()
  {
     boolean retVal= false;
     modelConfig= new ModelSchema();
     try
     {
        
        File configFile = new File(configFilePathDisp.getText());
        if (configFile.exists())
        {
            FileInputStream fi= new FileInputStream(configFile);            
            modelConfig.load(fi);
            fi.close();

            retVal= true;  
        }
     }
     catch (IOException ie)
     {
         System.out.println("Model config file loading failed "+ configFilePathDisp.getText() + ", new config will be saved later...");
     }
     return retVal;
  }


  // sets current parameters on the GUI etc. to those loaded from older run's config
  // updates the GUI accordingly. WARNING: Does not update the variables = call buildParams() to do that
  // RETURNS true ONLY if the loaded parameters match the current user selection, i.e. no change since
  // last HDS run is detected.

  public boolean setGUIToLoadedParams()
  {
     boolean retVal= true;
     // set the GUI according to the values loaded
     if (modelConfig !=null)
     {

         
        boolean testVal= Boolean.valueOf(modelConfig.getProperty("skipDataFileClustering"));
        // this selects the appropriate button and triggers appropriate events/updates on the GUI
        if ((testVal== true) && (skipDataFileClustering==false))
        {
           retVal= false;
           this.dataFormatGraph.doClick();
           skipDataFileClustering = true;
        }
        
        testVal= Boolean.valueOf(modelConfig.getProperty("matrixFlag"));
        // this selects the appropriate button and triggers appropriate events/updates on the GUI
        if ((testVal== true) && (matrixFlag==false))
        {
           retVal= false;
           dataFormatDistMat.doClick();
        }
        if ((testVal== false) && (matrixFlag==true))
        {
           retVal= false;
           dataFormatVectorSpace.doClick();
        }

        testVal= Boolean.valueOf(modelConfig.getProperty("skipFirstDataLine"));
        if ((testVal==true) && (skipFirstDataLine== false))
        {
           retVal= false;
           skipLineCheckBox.doClick();
        }
        if ((testVal==false) && (skipFirstDataLine== true))
        {
           retVal= false;

           if (dataFormatVectorSpace.isSelected()) // only need to process if vector space
           {
              skipLineCheckBox.doClick();
           }
           else
           {
              skipLineCheckBox.setSelected(false);
           }
        }

        String testStr= modelConfig.getProperty("delimiter");
        if (testStr.compareTo("SPACE")==0)
        {
           testStr=" ";
        }
        if (testStr.compareTo("TAB")==0)
        {
           testStr="\t";
        }
        if (testStr.compareTo(delimiter)!=0) // if changed
        {
           retVal= false;
           delimiter= testStr;
        }

        int testInt=-1;
        if (matrixFlag==false)
        {
           testInt= Integer.parseInt(modelConfig.getProperty("distanceMeasure"));
           if (testInt != distMeasureVal) // needs update
           {
              retVal= false;
              switch (testInt)
              {
                 case Diver.PEARSON  : pearsonRadio.doClick(); break;
                 case Diver.COSINE   : cosineRadio.doClick(); break;
                 default             : sqEuclideanRadio.doClick(); break;
              }
           }
        }
        else
        {
           distMeasureVal= Diver.EUCLIDEAN;  // default assumed
        }

        testInt= Integer.parseInt(modelConfig.getProperty("classColIdx"));
        if (testInt!= classColIdx)
        {
           retVal= false;
           if (testInt>-1)
           {
              if (Boolean.valueOf(modelConfig.getProperty("classColName")))
              {
                 classColName.setSelected(true);
                 classColumnDisp.setText(modelConfig.getProperty("classlabel"));
              }
              else
              {
                 classColIndex.setSelected(true);
                 classColumnDisp.setText(modelConfig.getProperty("classColIdx"));
              }
           }
        }

        testInt= Integer.parseInt(modelConfig.getProperty("neps"));
        if (neps!= testInt)
        {
           retVal= false;
           neps= testInt;
           nepsDisp.setText(modelConfig.getProperty("neps"));
        }

        double testD= Double.parseDouble(modelConfig.getProperty("fshave"));
        if (fshave!= testD)
        {
           retVal= false;
           fshave= testD;
           fshaveDisp.setText(modelConfig.getProperty("fshave"));
        }

        testD= Double.parseDouble(modelConfig.getProperty("rshave"));
        if (rshave!= testD)
        {
           retVal= false;
           rshave= testD;
           rshaveDisp.setText(modelConfig.getProperty("rshave"));
        }

        testInt= Integer.parseInt(modelConfig.getProperty("runtSize"));
        if (runtSize!= testInt)
        {
           retVal= false;
           runtSize= testInt;
           runtSizeDisp.setText(modelConfig.getProperty("runtSize"));
        }
     }
     else // no previous runs exist since no config file could be found
     {
        retVal= false;
     }

     return retVal;
  }


  // checks the status of browse HDS results drawing
  // Returns 0 if not up to date. 1 if just loaded and drawing needed
  // 2 if completely up to date
  public int isBrowseHDSUpToDate()
  {

     int retVal= isAutoHDSUpToDate();
     if (zoomFigurePanel.isDrawn()==false)
     {
        if (retVal==2)
        {
           retVal=1;
        }
     }
     if (browseResultsStatus==1) // ready but not drawn yet
     {
        if (retVal==2)
        {
           retVal=1;
        }
     }
     return retVal;
  }

  // Checks if HDS uptodate AND runtsize has not changed
  // then AutoHDS is up to dates. Returns 0 if not up to date. 1 if just loaded and drawing needed
  // 2 if completely up to date
  public int isAutoHDSUpToDate()
  {
     int retVal= 2;

     if (autohdsInvalid) // forces autohds to be invalid and be updated
     {
        return 0;
     }

     int hdsStatus= isHDSUpToDate();

     if (hdsStatus>0)
     {
        int testInt= Integer.parseInt(modelConfig.getProperty("runtSize"));
        if (runtSize== testInt)
        {
           // make sure if hmaLabel array is computed already
           if (theDiver.hmaLabels==null)
           {
              boolean loadStatus= theDiver.computeAutoHDS(runtSize, dataFile, rshave);
              // output labeled clusters, saves all clusters, ordered by stability
              theDiver.saveAutoHDSClusters(dataFile, pointsDescriptions, pointsURLs);
              if (loadStatus==true)
              {
                 drawHDSResults();  // found the AUTOHDS results uptodate but need to draw after loading
                 retVal=1;
              }
              else
              {
                 retVal= 0;
              }
           }
        }
        else
        {
           retVal= 0;
        }
     }
     else
     {
        retVal= 0;
     }
     return retVal;
  }

  public int isHDSUpToDate()
  {
     // load last clustered parameter values
     boolean status = loadPreviousParams();

      // force the parameters to be updated based on the current GUI values
     buildCurrentParams();
     
     // save a copy of current params since we just build based on current UI setting
     // this also merges current settings with saved settings in memory model config
     if (!status)
        saveCurrentParams();
     
     // now compare the two///////////////////////////

     dataSummaryDisp.setText(getHtmlDataSummary());

     int retVal= 2;

     // set the GUI according to the values loaded
     if (modelConfig !=null)
     {
        boolean skipDataClustering = Boolean.valueOf(modelConfig.getProperty("skipDataFileClustering"));
     
        if (!skipDataClustering)
        {
            boolean testVal= Boolean.valueOf(modelConfig.getProperty("matrixFlag"));
            // this selects the appropriate button and triggers appropriate events/updates on the GUI
            if ((testVal== true) && (matrixFlag==false))
            {
               retVal= 0;
            }
            if ((testVal== false) && (matrixFlag==true))
            {
               retVal= 0;
            }

            testVal= Boolean.valueOf(modelConfig.getProperty("skipFirstDataLine"));
            if ((testVal==true) && (skipFirstDataLine== false))
            {
               retVal= 0;
            }
            if ((testVal==false) && (skipFirstDataLine== true))
            {
               retVal= 0;
            }

            String testStr= modelConfig.getProperty("delimiter");
            if (testStr.compareTo("SPACE")==0)
            {
               testStr=" ";
            }
            if (testStr.compareTo("TAB")==0)
            {
               testStr="\t";
            }
            if (testStr.compareTo(delimiter)!=0) // if changed
            {
               retVal= 0;
            }

            int testInt=-1;
            if (matrixFlag==false)
            {
               testInt= Integer.parseInt(modelConfig.getProperty("distanceMeasure"));
               if (testInt != distMeasureVal) // needs update
               {
                  retVal= 0;
               }
            }

            testInt= Integer.parseInt(modelConfig.getProperty("classColIdx"));
            if (testInt!= classColIdx)
            {
               retVal= 0;
            }

            testInt= Integer.parseInt(modelConfig.getProperty("neps"));
            if (neps!= testInt)
            {
               retVal= 0;
            }
            double testD= Double.parseDouble(modelConfig.getProperty("fshave"));
            if (fshave!= testD)
            {
               retVal= 0;
            }
            testD= Double.parseDouble(modelConfig.getProperty("rshave"));
            if (rshave!= testD)
            {
               retVal= 0;
            }       
        }
        else
        {
            // pretend data already clustered before for graph clustering as 
            // that is a requirement so set it to reload that existing clustering
            retVal=2;
        }
        
        // still seems completely uptodate, make sure loaded in memory
        if (retVal== 2)
        {
            if (theDiver==null) // but HDS is not in memory but on DISK, try loading it
            {
               retVal=1; // not completely uptodate but attempting load of old results
               theDiver= new Diver(getDiscBufferSelected(), distMeasureVal, classColIdx, skipFirstDataLine, skipDataFileClustering);
               boolean hdsloadstatus= theDiver.loadHDSData(dataFile, 1, skipDataClustering, this.pointsDescriptions);
               if (hdsloadstatus== false) // could not load HDS, clustering not available
               {
                  theDiver= null;
                  retVal=0;
               }
               else
               {
                  // now draw the results onto the default visual window in COLOR!
                  drawHDSResults();
               }
            }
        }
     }
     else // no previous runs exist since no config file could be found
     {
        retVal= 0;
     }
     return retVal;
  }

  // triggered when the tabbed pane changes
  public void stateChanged (ChangeEvent e)
  {
     // update the cluster tab content
     if (tabbedPane.getSelectedIndex()==1) // selected the CLUSTER TAB
     {
        buildCurrentParams();
        dataSummaryDisp.setText(getHtmlDataSummary());
        frame.pack();
     }

     if (tabbedPane.getSelectedIndex()==2) //selected the Browse Clustering TAB
     {
        if (browseResultsStatus== 0)
        {
           JOptionPane.showMessageDialog(null, "Auto-HDS not ready to browse yet.", "Error", JOptionPane.ERROR_MESSAGE);
           tabbedPane.setSelectedIndex(1);
        }
        else
        {
           int status= isBrowseHDSUpToDate();
           if (status==1)
           {
              drawBrowserHDSResults();
           }
        }
     }
  }

  // disc buffer validation
  private int getDiscBufferSelected()
  {
     int retVal= Diver.DEFAULT_DISC_BUFFER;
     try
     {
        // count in megabytes
        retVal= Integer.parseInt(discBufferDisp.getText())*1000000;
     }
     catch (NumberFormatException ne)
     {
        JOptionPane.showMessageDialog(null, "DISC BUFFER \""+
                  discBufferDisp.getText()+"\" invalid, switching to default."
                             , "Warning", JOptionPane.ERROR_MESSAGE);
        discBufferDisp.setText(Integer.toString(Diver.DEFAULT_DISC_BUFFER));
     }
     return retVal;
  }

  ////////////////////////////////////////// MEAT OF ALL THE GUI ACTIONS HERE //////////////////////////

  public void actionPerformed (ActionEvent e)
  {
     String cmd= e.getActionCommand();
     Object source= e.getSource();

     if (source== exitButton)
     {
        System.exit(0);
     }

     if (source== autohdsButton)
     {
        int status= isHDSUpToDate(); // checks if last run of HDS was in sync with current parameters
        if (status== 0)
        {
           autohdsButton.setEnabled(false);
           JOptionPane.showMessageDialog(null, "Parameters have changed. HDS clustering will now be updated first",
                                         "Auto HDS", JOptionPane.INFORMATION_MESSAGE);
           hdsButton.doClick(300);
        }

        // check if Auto-HDS is up to date
        int autohdsstatus= isAutoHDSUpToDate();
        if (autohdsstatus== 0)
        {
           browseResultsStatus= 0;
           // put code for running autohds below
           // that floodfills and displays the clustering results
           boolean autocompstatus= theDiver.computeAutoHDS(runtSize, dataFile, rshave);
           theDiver.saveHMATree(dataFile); // for user, text format save
           // output labeled clusters, saves all clusters, ordered by stability
           theDiver.saveAutoHDSClusters(dataFile, pointsDescriptions, pointsURLs);

           if (autocompstatus==true)
           {
              drawHDSResults();

              JOptionPane.showMessageDialog(null, "Auto-HDS is ready, "+
              theDiver.numHMAClusters+" clusters in hierarchy, ready to browse", "Auto-HDS is ready", JOptionPane.INFORMATION_MESSAGE);

              // save the current parameters used for clustering
              saveCurrentParams();
           }
           else
           {
              JOptionPane.showMessageDialog(null,
              "Could not compute Auto-HDS. Internal error: contact author gunjan@iname.com", "Error:Auto-HDS", JOptionPane.INFORMATION_MESSAGE);
           }
        }
        else
        if (autohdsstatus==1)
        {
           JOptionPane.showMessageDialog(null, "Auto-HDS is up to date: loaded from last run, "+
           theDiver.numHMAClusters+" clusters in hierarchy, ready to browse", "Auto-HDS is ready", JOptionPane.INFORMATION_MESSAGE);
        }
        else // no need to run clustering again- it is up to date
        {
           JOptionPane.showMessageDialog(null, "Auto-HDS is up to date. No need to run,"+
           theDiver.numHMAClusters+" clusters in hierarchy, ready to browse" , "Auto-HDS is ready", JOptionPane.INFORMATION_MESSAGE);
        }
     }

     if (source== hdsButton)
     {
        int status= isHDSUpToDate(); // checks if last run of HDS was in sync with current parameters

        // if they are different in some way
        if (status==0)  // something has changed- we need to run HDS again
        {
           autohdsButton.setEnabled(false);
           browseResultsStatus= 0;
           // run HDS now using current parameters selected by user, throw away the outdated construction
           // in the process
           theDiver= new Diver(getDiscBufferSelected(), distMeasureVal, classColIdx, skipFirstDataLine, skipDataFileClustering);

           // NOW ACTUAL PROCESSING WORK CAN START
           boolean hdsStatus= theDiver.getNNbrs(dataFile, neps, fshave, rshave, onlyDS, matrixFlag, delimiter, 1);
           autohdsInvalid= true;
           if (hdsStatus== false) // HDS failed
           {
              theDiver= null;
           }
           else
           {
              // now draw the results onto the default visual window as B&W, since colors not available yet
              drawHDSResults();

              // now we can enable the button for Auto-HDS
              autohdsButton.setEnabled(true);
              // save the current parameters used for clustering
              saveCurrentParams();
           }
        }
        else // no need to run clustering again - it is up to date
        {
           if (status==2)
           {
              JOptionPane.showMessageDialog(null, "HDS clustering is up to date. No need to do it again", "HDS is ready", JOptionPane.INFORMATION_MESSAGE);
              autohdsButton.setEnabled(true);
           }
           if (status==1) // loaded old results, mention that to the user
           {
              JOptionPane.showMessageDialog(null, "HDS clustering results up to date: loaded from the last run.", "HDS is ready", JOptionPane.INFORMATION_MESSAGE);
              autohdsButton.setEnabled(true);
           }
        }
     }

     if (source== fileLoadButton)
     {
        JFileChooser chooser = new JFileChooser();
        chooser.setCurrentDirectory(new File(dataDir));
        if (dataFile==null)
        {
           chooser.setSelectedFile(new File(dataDir));
        }
        else
        {
           chooser.setSelectedFile(new File(dataFile));
        }
        int returnVal = chooser.showOpenDialog(frame);
        if(returnVal == JFileChooser.APPROVE_OPTION)
        {
           fileSelected= true; // now we know we have a data file to go on
           File fselected= chooser.getSelectedFile();
           dataDir= fselected.getParentFile().getPath();
           String newDataFile= fselected.getAbsolutePath();
           if (dataFile!=null)
           {
              // data file specified before and was not the same as the new one
              if (dataFile.compareTo(newDataFile)!=0)
              {
                 // now update the data file
                 dataFile= newDataFile;
                 inputFilePathDisp.setText(dataFile);
                 // we  want to clear previous results every time a new file is loadedp
                 clearDrawnResults();

                 // remove variables that were computed from previous run
                 resetOldLocalVars();

                 // also remove old Diver
                 theDiver= null;

                 // clear previous clustering state
                 autohdsButton.setEnabled(false);
                 browseResultsStatus= 0;
              }
           }
           else
           {
              // now update the data file
              dataFile= newDataFile;
              inputFilePathDisp.setText(dataFile);
           }

           // display output file names
           autoFilePathDisp.setText(ModelUtil.removeExtension(dataFile)+Diver.SORTEDHDSFILEEXTENSION);
           labelFilePathDisp.setText(ModelUtil.removeExtension(dataFile)+Diver.LABELFILEEXTENSION);

           // where we will store the clustering configuration
           configFilePathDisp.setText(ModelUtil.removeExtension(dataFile)+CONFIGFILEEXTENSION);

           // check if data description file is present, if it is, load that info
           dataDescriptionFile= ModelUtil.removeExtension(dataFile)+".dsc";

           // check if clustering parameters from last run are available, if yes
           // load them and set the current params specs by user to them.
           boolean foundParams= loadPreviousParams();
           String message = null;
           String messageBanner = null;
           int messageType = JOptionPane.INFORMATION_MESSAGE;
           
           if (foundParams== false)
           {
              message = "No previous clustering config available for this data file. Please select correct parameters before clustering";
              messageBanner = "User input needed";
              messageType = JOptionPane.WARNING_MESSAGE;
              
              // clear previous clustering state
              autohdsButton.setEnabled(false);
              browseResultsStatus= 0;
           }
           else
           {
              setGUIToLoadedParams();
              message = "Loaded previous clustering parameters for this data file.";
              messageBanner = "Configuration Found";
           }
           
            // if the data file is zero size and
            if (ModelUtil.getNumLines(dataFile) == 0)
            {
               message = "Assuming graph data as spatial input data file is empty! " + message;
               if (!this.dataFormatGraph.isSelected())
               {
                   this.dataFormatGraph.doClick();
               }
               // also unselect some of the other options that won't be possible with empty data file
               classColName.setSelected(false);
               classColIndex.setSelected(false);
               classColNone.setSelected(true);
            }                
            
            JOptionPane.showMessageDialog(null, message, messageBanner, messageType);            
        }        
     }

     if (source== autoZoomCheckBox)
     {
        // update display whenever this state change happens
        drawZoomedBrowserHDS();
     }

     if (source== skipLineCheckBox)
     {
        if (skipLineCheckBox.isSelected())
        {
           //enable class column name selection
           classColName.setEnabled(true);
        }
        else
        {
           //enable class column name selection
           if (classColName.isSelected())
           {
              classColNone.setSelected(true);
              classColumnDisp.setText("");
           }
           classColName.setEnabled(false);
        }
     }

     if (source== dataFormatDistMat)
     {
        sqEuclideanRadio.setEnabled(false);
        pearsonRadio.setEnabled(false);
        cosineRadio.setEnabled(false);
        infDistRadio.setSelected(true);
        skipLineCheckBox.setEnabled(false);
        skipLineCheckBox.setSelected(false);
        classColName.setEnabled(false);
        classColIndex.setEnabled(false);
        classColumnDisp.setEnabled(false);
        classColumnDisp.setText("");
        classColNone.setSelected(true);
        spaceDelimiterRadio.setSelected(true);
     }

     if (source== dataFormatVectorSpace)
     {
        sqEuclideanRadio.setEnabled(true);
        pearsonRadio.setEnabled(true);
        cosineRadio.setEnabled(true);
        sqEuclideanRadio.setSelected(true);
        skipLineCheckBox.setEnabled(true);
        skipLineCheckBox.setSelected(true);
        classColName.setEnabled(true);
        classColIndex.setEnabled(true);
        classColumnDisp.setEnabled(true);
        commaDelimiterRadio.setSelected(true);
     }
     
     if (source== dataFormatGraph)
     {
        sqEuclideanRadio.setEnabled(false);
        pearsonRadio.setEnabled(false);
        cosineRadio.setEnabled(false);
        infDistRadio.setSelected(false);
        skipLineCheckBox.setEnabled(false);
        skipLineCheckBox.setSelected(false);
        classColName.setEnabled(false);
        classColIndex.setEnabled(false);
        classColumnDisp.setEnabled(false);
        classColumnDisp.setText("");
        classColNone.setSelected(false);
        spaceDelimiterRadio.setSelected(false);         
     }
  }

  // draws HDS results if they are available
  public boolean drawHDSResults()
  {
     boolean retVal= false;

     if (theDiver!=null)
     {
        if (theDiver.hmaLabels!= null)
        {
           frame.setResizable(true);

           // image used in the main panel
           retVal= figurePanel.setHMAImage (theDiver.hmaLabels, theDiver.sortedTreeIdx,theDiver.numHMAClusters, "HDS Clusters");
           figurePanel.update(figurePanel.getGraphics());

           frame.pack();
           frame.setResizable(false);

           autohdsButton.setEnabled(true);
           autohdsInvalid= false;
           // browse results ready but not drawn
           browseResultsStatus= 1;
        }
        else
        if (theDiver.hdsLabels!= null)
        {
           frame.setResizable(true);
           retVal= figurePanel.setHDSImage(theDiver.hdsLabels, theDiver.sortedTreeIdx);
           figurePanel.update(figurePanel.getGraphics());
           frame.pack();
           frame.setResizable(false);
           // cannot browse as AutoHDS not ready yet
           browseResultsStatus= 0;
        }
     }
     return retVal;
  }

  // draws HDS results if they are available
  public boolean drawBrowserHDSResults()
  {
     boolean retVal= false;

     if (theDiver!=null)
     {
        if (theDiver.hmaLabels!= null)
        {
           frame.setResizable(true);

           // now update the rest of the items in the Browse Clusters pane
           String[] clusterListData= new String[theDiver.numHMAClusters];
           for (int i=0; i<theDiver.numHMAClusters; i++)
           {
              // list the most stable clusters first
              int rankedIdx= theDiver.clusterRankOrder[i];
              clusterListData[i]= Integer.toString(rankedIdx+1)+ "("+
                  Math.round(theDiver.clusterStability[rankedIdx])+")";
           }
           clusterList.setListData(clusterListData);
           clusterList.setSelectedIndex(0);

           // image used in the browser panel
           retVal= zoomFigurePanel.setLabeledHMAImage (theDiver, "Browsable HDS Clusters", -1);
           zoomFigurePanel.update(zoomFigurePanel.getGraphics());

           frame.pack();
           frame.setResizable(true);
           browseResultsStatus=2; // ready to browse now
           retVal=true;
        }
     }
     return retVal;
  }

  // updates the zoomed drawing of HDS results
  public boolean drawZoomedBrowserHDS()
  {
     boolean retVal= false;

     if (theDiver!=null)
     {
        if (theDiver.hmaLabels!= null)
        {
           // things have shifted need to redraw, pass -1 if no index found selected
           int clusterIdx= clusterList.getSelectedIndex();
           if (clusterIdx!=-1)
           {
              clusterIdx= theDiver.clusterRankOrder[clusterIdx];
           }

           // image used in the browser panel
           if (autoZoomCheckBox.isSelected())
           {
              zoomFigurePanel.setZoomedLabeledHMAImage (theDiver, "Browsable HDS Clusters", clusterIdx);
           }
           else
           {
              retVal= zoomFigurePanel.setLabeledHMAImage (theDiver, "Browsable HDS Clusters", clusterIdx);
           }
//           zoomFigurePanel.update(zoomFigurePanel.getGraphics());
        }
     }
     return retVal;
  }


  public void mouseClicked(MouseEvent e)
 {
 }
 public void mouseEntered(MouseEvent e)
 {
 }
 public void mouseExited(MouseEvent e)
 {
 }
 public void mousePressed(MouseEvent e)
 {
    int button= e.getButton();
    Object source = e.getSource();
    
    if ((button == e.BUTTON1) && (source == pointsList))
    {
        int viewPidx = pointsList.getSelectedIndex();
        int viewCidx = clusterList.getSelectedIndex();        
        int cIdx= theDiver.clusterRankOrder[viewCidx];

        Integer[] pointsListIdx= theDiver.hmaBaseMembers.get(cIdx);       
        
        if (viewPidx > 0)
        {
            int pIdx = pointsListIdx[viewPidx-1];
         
            this.pointsListPane.removeMouseListener(this);
        
            if ((this.browseInternetCheckBox.isSelected()) && (this.pointsURLs[pIdx] != null))
            {            
                this.openPointURL(pointsURLs[pIdx]);
            }
        }
    }
    
    if ((button== e.BUTTON3) && (source == clusterList))
    {
       int cidx= clusterList.getSelectedIndex();
       clusterListPane.setToolTipText("Select cluster to browse");
       clusterListPane.removeMouseListener(this);
    }
    if ((button== e.BUTTON1) &&(figurePanel.isHMAFigure) &&
        ((source==figurePanel) || (source==zoomFigurePanel) ))
    {
       // first check to see which figure is being displayed-  figurePanel or zoomFigurePanel
       HDSImage curFigurePanel= figurePanel;

       // current active pane is the browsable one
       if(tabbedPane.getSelectedIndex()==2)
       {
          curFigurePanel= zoomFigurePanel;
       }

       int x= e.getX();
       int y= e.getY();
//       System.out.println("x= "+x);
//       System.out.println("y= "+y);

       int startRow=0, startCol=0;
       int numRow= curFigurePanel.numRow;
       int numCol= curFigurePanel.numCol;

       // if browsing tabbed and zoomed, then we need to use different offset coordinates
       if ((autoZoomCheckBox.isSelected()) &&(tabbedPane.getSelectedIndex()==2))
       {
          startRow= curFigurePanel.startIRow;
          startCol= curFigurePanel.startICol;
          numRow= curFigurePanel.numIRow;
          numCol= curFigurePanel.numICol;
       }

       // now compute the actual hma row and col clicked by user
       int hmaCol= (int)Math.round((x- curFigurePanel.XPIXOFFSET-curFigurePanel.fpixWidth/2.0)/curFigurePanel.fpixWidth+ startCol);
       int hmaRow= (int)Math.round((y- curFigurePanel.YPIXOFFSET-curFigurePanel.fpixHeight/2.0)/
                        curFigurePanel.fpixHeight)+curFigurePanel.numNonDense+startRow;
       // if a valid row col clicked, then browse it
       if ((hmaCol>=startCol) && (hmaCol<(startCol+numCol)) && (hmaRow>=startRow)
               && (hmaRow<(curFigurePanel.numNonDense+startRow+numRow)))
       {
          int ptIdx= theDiver.sortedTreeIdx[hmaRow]; // original point index
          int hmaClusterId= theDiver.hmaLabels[ptIdx][hmaCol];
          String dispStr="";
          if (hmaClusterId>0)
          {
             dispStr= "HDS Cluster id: "+hmaClusterId;
             mainHMApopup= new JPopupMenu();
             mainHMApopup.add(dispStr);
             dispStr= "Base cluster size: "+ theDiver.hmaClusterSize[hmaClusterId-1];
             mainHMApopup.add(dispStr);
             dispStr= "Base level: "+ theDiver.hmaBaseLevels.get(hmaClusterId-1);
             dispStr= "Class distribution";
             mainHMApopup.add(dispStr);
             mainHMApopup.addSeparator();
             if (theDiver.classColIdx==-1)
             {
                dispStr= "No labeled data";
                mainHMApopup.add(dispStr);
             }
             else
             {
                for (int i = 0; i < theDiver.classlabels.length; i++)
                {
                   if (theDiver.classlabels[i] != 0)
                   {
                      mainHMApopup.add("" + theDiver.classlabels[i] + ":" +
                         theDiver.hmaBaseLabels[hmaClusterId - 1][i]);
                   }
                }
                mainHMApopup.addSeparator();
                for (int i = 0; i < theDiver.classlabels.length; i++)
                {
                   if (theDiver.classlabels[i] == 0)
                   {
                      mainHMApopup.add("Background points: " +
                         theDiver.hmaBaseLabels[hmaClusterId - 1][i]);
                   }
                }
             }

             // now add the button for browsing clusters in Fun Spec
             //mainHMApopup.addSeparator();
             mainHMApopup.show(curFigurePanel,x,y);
          }
       }
    }
 }
 public void mouseReleased(MouseEvent e)
 {
    if (mainHMApopup!=null)
    {
       mainHMApopup.remove(figurePanel);
    }
 }

  // clears anything previously drawn
  public void clearDrawnResults()
  {
     // dummy drawn image that is blank
     int [] clIdx= new int[10];
     for (int i=0; i<10; i++)
     {
       clIdx[i]= i;
     }
     figurePanel.setHDSImage(new int[10][3], clIdx);
     zoomFigurePanel.setHDSImage(new int[10][3], clIdx);

     // delete data from the browse lists
     String[] emptyList= new String[1];
     emptyList[0]= new String("");
     pointsList.setListData(emptyList);
     clusterList.setListData(emptyList);
  }

  public void valueChanged (ListSelectionEvent e)
  {
     JList list= (JList)e.getSource();
     if ((list== clusterList) && (clusterList.getSelectedIndex()!=-1))
     {
        // now process this selection, recover original cluster id
        int listidx= clusterList.getSelectedIndex();

        int idx= theDiver.clusterRankOrder[listidx];

        Integer[] pointsListIdx= theDiver.hmaBaseMembers.get(idx);
        int clustSize= pointsListIdx.length;

        // now display the points in this cluster in the pointsList, including their summary
        // as the first row
        String[] displayList= new String[clustSize+1];

        browseInternetCheckBox.setEnabled(true);

        displayList[0]="Cluster "+(idx+1)+" of size "+clustSize;

        if (dataDescriptionFile!=null)
        {
           // look up the points description that have been loaded
           for (int i=0; i<clustSize; i++)
           {
              displayList[i+1]= pointsDescriptions[pointsListIdx[i]];
           }
        }
        else
        {
           // no data description file is available
           // just show points idx
           for (int i=0; i<clustSize; i++)
           {
              displayList[i+1]= new String("Point "+pointsListIdx[i].toString());
           }
        }
        // now fill up the points list
        pointsList.setListData(displayList);
        // select the first point in the points list
        pointsList.setSelectedIndex(1);

        int numRow= clustSize;
        int startCol= theDiver.hmaBaseLevels.get(idx);
        int numCol= theDiver.hmaPeakLevels[idx]-startCol+1;

        int startRow= theDiver.firstClusterIndex[idx]; // first position in sorted hma matrix that this cluster appears
        // now update the HMA figure to zoom into the selected cluster area
        drawZoomedBrowserHDS(); // things have shifted need to redraw
     }
     if (list== pointsList) // selected a point, time to show the network
     {
        // now process this selection, recover original point index
        int listidx= pointsList.getSelectedIndex();
        // todo: add url loading capabiltiy later there old biogrid stuff removed
        drawZoomedBrowserHDS();
     }
  }

   public void openPointURL(String url)
   {
      // String url = "https://thebiogrid.org/search.php?search="+geneName +"&organism=all";
      Runtime runtime = Runtime.getRuntime();      
      try 
      {
         runtime.exec("google-chrome "+ url);
      } 
      catch (IOException e) 
      {
         System.out.println("Error opening browser to url: "+ url);
      }
   }

  // clears those previously loaded and set variables that could interfer with
  // interepretation if new file gets loaded for clustering
  protected void resetOldLocalVars()
  {
     // load and store points descriptions for the GUI usage, if available
     pointsDescriptions= null;

     // if funspec checkbox is enabled
//     funspecGeneNames= false;

     numPt=-2;
     numDescriptions=-1;
     pointsDescriptions= null;
     classCol=null;
     classColIdxStr=null;
  }
};


class DiverWin
{
  public static void main(String args[])
  {
     DiverGUI theGUI = new DiverGUI();
     theGUI.init();
  }
};
