# Getting started with the annotator #

The annotator requires Bokeh, Pandas, and Numpy to be installed. Bokeh can be installed using a standard python package manager (i.e. pip, conda, etc). 

```
#!bash

conda install bokeh
conda install pandas
conda install numpy
```

## Running From the Command Line ##

Next, the annotator must be started from the command line using the `bokeh serve --show` command. Two minutes of demo data is provided. To run the example:

```
#!bash

bokeh serve --show ppgAnnotator.py --args data/sample_plethraw.txt data/sample_qosraw.txt
```


## Note ##
The annotator requires that you pass a PPG File and Qos File (note: must provide path to file, so you may want to `cd` to certain directory level). An optional file of previously annotated notes may be passed as well. A command should look similar to the following:

```
#!bash

bokeh serve --show ppgAnnotator.py --args ppgFile.txt qosFile.txt [previouslyAnnotatedFile.txt]
```

### Data Format ###
Pandas has pretty robust methods for parsing dates. Therefore, as long as data is provided in comma separated format (time,pleth/qos), no further formatting should be needed.

```
timestamp,pleth
2020-01-01 12:00:00.000,1400
2020-01-01 12:00:00.008,1382
2020-01-01 12:00:00.016,1365
```
```
timestamp,pleth
"2020-01-01T12:00:00.000-0500",1400
"2020-01-01T12:00:00.008-0500",1382
"2020-01-01T12:00:00.016-0500",1365
```

### Dependencies ###
* Bokeh
* Pandas
* Numpy