# Annotator Overview

The annotator requires Bokeh, Pandas, and Numpy to be installed. Bokeh can be installed using a standard python package manager (i.e. pip, conda, etc).

### Dependencies
* Bokeh
* Pandas
* Numpy

```
#!bash

conda install bokeh
conda install pandas
conda install numpy
```

## Running From the Command Line

Next, the annotator must be started from the command line using the `bokeh serve --show` command. Two minutes of demo data is provided. To run the example:

Run using:

        bokeh serve --show ScriptName.py --args ppgFile.txt qosFile.txt ekgFile.txt [ppgQosAnnotation.txt] [ekgAnnotation.txt]

Example:

        bokeh serve --show ppgAnnotator.py --args data/sample_plethraw.txt data/sample_qosraw.txt data/sample_ekg.txt

## Structure

Script outline:
1.  Load data into arguments
2.  Create pandas dataframes from loaded files
3.  Create figure/viewers for data
4.  Create the lines/datasources that will populate the figure
5.  Create settings for displays
6.  Create widgets for interactions
7.  Create callback functions for widgets (and create function for redisplaying annotations from previous files)
8.  Connect callback functions to widgets
9.  Initialize annotator
10. Add plot and widgets to the document


## Data Format
Pandas has pretty robust methods for parsing dates. Therefore, as long as data is provided in comma separated format (time,pleth/qos), no further formatting should be needed.

In other words, the following two inputs should work fine:



```
timestamp,pleth
2020-01-01 12:00:00.000,1400
2020-01-01 12:00:00.008,1382
2020-01-01 12:00:00.016,1365
```

```
"timestamp","pleth"
"2020-01-01T12:00:00.000-0500",1400
"2020-01-01T12:00:00.008-0500",1382
"2020-01-01T12:00:00.016-0500",1365
```
