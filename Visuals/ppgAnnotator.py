"""
For Python 2.7.x

Third iteration of offline visual dataviewer and annotator. Written in Bokeh 0.12.4.
As per the documentation and gallery examples, script makes use of global variables. Will try to make easier to read in
future revisions, but initial attempts at class based OOP version was slower than current implementation.

Run using:
    bokeh serve --show ScriptName.py --args sqlFile.db [-s pleth/qosAnnotation.txt] [-e ekgAnnotation.txt]

@author: aoyalowo

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
"""
from __future__ import division

import argparse
import datetime
import warnings
# import memory_profiler
import logging

import numpy as np
import pandas as pd
from bokeh.io import curdoc
from bokeh.models import Range1d, DatetimeTickFormatter, Circle, ColumnDataSource, Label
from bokeh.models.layouts import Column, HBox, VBox
from bokeh.models.tools import HoverTool, BoxSelectTool, TapTool, WheelZoomTool, ResizeTool, BoxAnnotation
from bokeh.models.widgets import Slider, TextInput, Button, RadioButtonGroup, DataTable, TableColumn
from bokeh.plotting import figure

import annotatorSettings
import csv
import os.path

logger = logging.getLogger()
logger.disabled = True

# FIXME: Clean up load data (functions perhaps?)
def parse_args():
    """ Create command line interface for entering command line arguments.

    Returns
    -------
    parsedArgs: Parser object
        Object for holding parsed command line arguments

    """

    import time

    now = time.strftime("%Y-%m-%dT%H-%M-%S")

    parser = argparse.ArgumentParser()
    parser.add_argument('sqlFile')
    # parser.add_argument('qosFile')
    # parser.add_argument('ekgFile')

    parser.add_argument('-s','--spo2QosAnnotatedFile', default="{}_ppgFile.txt".format(now), nargs='?')
    parser.add_argument('-e','--ekgAnnotatedFile', default="{}_ekgFile.txt".format(now), nargs='?')
    parsedArgs = parser.parse_args()

    return parsedArgs

args = parse_args()
logger.info(args)

# Check to see if annotated files exist.
if os.path.isfile(args.spo2QosAnnotatedFile):
    warnings.warn("File {} already exists and will be written to. Please check to make sure you are annotating the correct file.".format(args.spo2QosAnnotatedFile))

    spo2QosAnnotatedFile = args.spo2QosAnnotatedFile

else:

    with open(args.spo2QosAnnotatedFile,'w') as outfile:
        outfile.write('{},{},{},{}'.format('startTime','endTime','ppgNote','qosNote'))
        outfile.write('\n')

        spo2QosAnnotatedFile = outfile.name

if os.path.isfile(args.ekgAnnotatedFile):

    warnings.warn("File {} already exists and will be written to. Please check to make sure you are annotating the correct file.".format(args.ekgAnnotatedFile))

    ekgAnnotatedFile = args.ekgAnnotatedFile

else:
    with open(args.ekgAnnotatedFile,'w') as outfile:
        outfile.write('{},{},{}'.format('startTime','endTime','ekgNote'))
        outfile.write('\n')

        ekgAnnotatedFile = outfile.name

################################################
#### 2. Create dataframes from loaded data. ####
################################################

import sqlite3

conn = sqlite3.connect(args.sqlFile)
conn.row_factory = sqlite3.Row
c = conn.cursor()
v = conn.cursor()


# alarms = c.execute('SELECT * FROM alarms')


# Note: Timestamps are read in and kept as object dtype
# ppgDataFrame = pd.read_csv(args.ppgFile, header=0, names=['time', 'pleth'], low_memory=False)
# qosDataFrame = pd.read_csv(args.qosFile, header=0, names=['time', 'qos'], low_memory=False)
# ekgDataFrame = pd.read_csv(args.ekgFile, header=0, names=['time', 'ekg'], low_memory=False)

# FIXME: Clean up plots
###########################
#### 3. CREATE VIEWERS ####
###########################

vitalViewer = figure(
    title="SpO2",
    plot_width= annotatorSettings.viewerWidth,
    plot_height=annotatorSettings.spo2ViewerHeight,
    toolbar_location=None,
    # toolbar_sticky=False,
    x_axis_type='datetime',
    y_range=annotatorSettings.spo2YRange,

)

# Control how string values axis should be displayed at a certain zoom/scale.
# http://bokeh.pydata.org/en/latest/docs/reference/models/formatters.html
vitalViewer.xaxis.formatter = DatetimeTickFormatter(
    years=["%D %T"],
    months=["%D %T"],
    days=["%D %T"],
    hours=["%D %T"],
    hourmin=["%D %T"],
    minutes=["%D %T"],
    minsec=["%D %T"],
    seconds=["%D %T"],
    milliseconds=["%D %T.%3N"],
)

vitalViewer2 = figure(
    title="Heart Rate",
    plot_width= annotatorSettings.viewerWidth,
    plot_height=annotatorSettings.hrViewerHeigth,
    toolbar_location=None,
    # toolbar_sticky=False,
    x_axis_type='datetime',
    y_range=annotatorSettings.hrYRange,

)

# Control how string values axis should be displayed at a certain zoom/scale.
# http://bokeh.pydata.org/en/latest/docs/reference/models/formatters.html
vitalViewer2.xaxis.formatter = DatetimeTickFormatter(
    years=["%D %T"],
    months=["%D %T"],
    days=["%D %T"],
    hours=["%D %T"],
    hourmin=["%D %T"],
    minutes=["%D %T"],
    minsec=["%D %T"],
    seconds=["%D %T"],
    milliseconds=["%D %T.%3N"],
)


ekgViewer = figure(
    # title=args.ekgFile,
    plot_width= annotatorSettings.viewerWidth,
    plot_height=annotatorSettings.ekgViewerHeight,
    toolbar_location='below',
    toolbar_sticky=False,
    x_axis_type='datetime',
    y_range=annotatorSettings.ekgYRange,

)

# Control how string values axis should be displayed at a certain zoom/scale.
# http://bokeh.pydata.org/en/latest/docs/reference/models/formatters.html
ekgViewer.xaxis.formatter = DatetimeTickFormatter(
    years=["%D %T"],
    months=["%D %T"],
    days=["%D %T"],
    hours=["%D %T"],
    hourmin=["%D %T"],
    minutes=["%D %T"],
    minsec=["%D %T"],
    seconds=["%D %T"],
    milliseconds=["%D %T.%3N"],
)

ppgViewer = figure(
    # title=args.ppgFile,
    plot_width=annotatorSettings.viewerWidth,
    plot_height=annotatorSettings.ppgViewerHeight,
    toolbar_location='below',
    toolbar_sticky=False,
    x_axis_type='datetime',
    y_range=annotatorSettings.ppgYRange,
)
ppgViewer.extra_y_ranges = {"qosRange": Range1d(start=-1.1, end=1.1)}
ppgViewer.xaxis.formatter = DatetimeTickFormatter(
    years=["%D %T"],
    months=["%D %T"],
    days=["%D %T"],
    hours=["%D %T"],
    hourmin=["%D %T"],
    minutes=["%D %T"],
    minsec=["%D %T"],
    seconds=["%D %T"],
    milliseconds=["%D %T.%3N"],
)

# Create tools to add to ppgViewer.
wheel_zoom = WheelZoomTool()
tap_tool = TapTool()
resizeTool = ResizeTool()
box_select = BoxSelectTool(dimensions="width")
hover = HoverTool(
    point_policy='snap_to_data',
    line_policy='nearest',
    tooltips=[
        ("index", "$index"),
        ("Value", "@y"),
        ("Time", '@time'),
    ],
)

# Create tools to add to ekgViewer.
wheel_zoom_ekg = WheelZoomTool()
tap_tool_ekg = TapTool()
resizeTool_ekg = ResizeTool()
box_select_ekg = BoxSelectTool(dimensions="width")
hover_ekg = HoverTool(
    point_policy='snap_to_data',
    line_policy='nearest',
    tooltips=[
        ("index", "$index"),
        ("Value", "@y"),
        ("Time", '@time'),
    ],
)

ekgViewer.add_tools(hover_ekg, box_select_ekg, tap_tool_ekg,resizeTool_ekg)
ekgViewer.toolbar.active_drag = box_select_ekg
ekgViewer.toolbar.active_scroll = wheel_zoom_ekg
ekgViewer.toolbar.active_tap = tap_tool_ekg


hoverSpO2 = HoverTool(
    point_policy='snap_to_data',
    line_policy='nearest',
    tooltips=[
        ("index", "$index"),
        ("Value", "@y"),
        ("Time", '@time'),
    ],
)

hoverHR = HoverTool(
    point_policy='snap_to_data',
    line_policy='nearest',
    tooltips=[
        ("index", "$index"),
        ("Value", "@y"),
        ("Time", '@time'),
    ],
)

ppgViewer.add_tools(hover, box_select, tap_tool, resizeTool)
ppgViewer.toolbar.active_drag = box_select
ppgViewer.toolbar.active_scroll = wheel_zoom
ppgViewer.toolbar.active_tap = tap_tool

vitalViewer.add_tools(hoverSpO2)
vitalViewer2.add_tools(hoverHR)

######################################################
#### 4. CREATE LINES AND DATASOURCES FOR PLOTTING ####
######################################################

vitalLine = vitalViewer.line(x=[], y=[], color=annotatorSettings.ppgLineColor, alpha=0.5)
vitalLine2 = vitalViewer2.line(x=[], y=[], color=annotatorSettings.ppgLineColor, alpha=0.5)
ekgLine = ekgViewer.line(x=[], y=[], color=annotatorSettings.ekgLineColor, alpha=0.5)
ppgLine = ppgViewer.line(x=[], y=[], color=annotatorSettings.ppgLineColor, alpha=0.5)
qosMarkers = ppgViewer.circle(x=[], y=[], color=annotatorSettings.qosMarkerColor, y_range_name='qosRange', line_width=0)

ekgDataSource = ekgLine.data_source
ppgDataSource = ppgLine.data_source
qosDataSource = qosMarkers.data_source
vitalDataSource = vitalLine.data_source
vitalDataSource2 = vitalLine2.data_source



qosMarkers.selection_glyph = Circle(fill_color=annotatorSettings.qosMarkerColor, visible=True)
qosMarkers.nonselection_glyph = Circle(fill_color=annotatorSettings.qosMarkerColor, visible=True)

##################################
#### 5. SETTINGS FOR DISPLAYS ####
##################################

fs = annotatorSettings.ppgFrequency
windowInSecs = annotatorSettings.windowInSecs

yScalesToSelect = [annotatorSettings.ppgYRange,[-10000,10000],[-30000,30000]]

currentPage = annotatorSettings.initializePage
i = conn.cursor()
totalPages = i.execute("SELECT COUNT('index') FROM alarms").fetchone()[0]


ekgColorSelector = annotatorSettings.ekgColorSelector
ppgColorSelector = annotatorSettings.ppgColorSelector
qosColorSelector = annotatorSettings.qosColorSelector

# FIXME: Clean up widgets
################################################################################
#### 6. ADD WIDGETS FOR INTERACTIONS (callbacks assigned at end of script). ####
################################################################################

fwdButton = Button(label="Next")
bckButton = Button(label="Previous")
jumpSlider = Slider(title='Jump to page', start=0, end=totalPages, step=1)
yScaleSlider = Slider(title='Y-scale', start=1, end=len(yScalesToSelect), step=1)
timeSlider = Slider(title='Window in secs', start=annotatorSettings.timeSliderStart, end=annotatorSettings.timeSliderEnd, value=annotatorSettings.timeSliderInitialValue, step=annotatorSettings.timeSliderStep)
pageIndicator = TextInput(value='{0!s}/{1!s}'.format(currentPage+1, totalPages), title='Current Page')
annotationTextInput = TextInput(title='Enter annotation below:')
ekgButtonGroup = RadioButtonGroup(labels=annotatorSettings.ekgCodes, active=0, width=annotatorSettings.viewerWidth)
ppgButtonGroup = RadioButtonGroup(labels=annotatorSettings.ppgCodes, active=0, width=annotatorSettings.viewerWidth)
qosButtonGroup = RadioButtonGroup(labels=annotatorSettings.qosCodes, active=0, width=annotatorSettings.viewerWidth)

# FIXME: Clean up callbacks
###############################
#### 7. CALLBACK FUNCTIONS ####
###############################

# @profile
def change_page():
    """ Request new data to be served to the plot.
    """

    # Call globals just as a reminder to denote what is local and what is global. Globals only being accesed, not reassigned.
    global ppgDataFrame, qosDataFrame, ekgDataFrame, ppgDataSource, qosDataSource, ekgDataSource, currentPage, vitalDataSource, vitalDataSource2

    alarms = c.execute('SELECT * FROM alarms WHERE "index" = ?',(currentPage,))
    result = alarms.fetchone()
    time = result[1]
    keys = str(result.keys())
    keyValues = str(list(result))
    logger.info(time)

    ekgViewer.title.text = "EKG " + keyValues
    ppgViewer.title.text = "Pleth " + keyValues

    t = v.execute("SELECT * FROM vitals WHERE (timestamp > DATETIME(?, ?) AND timestamp < DATETIME(?, ?))",(time,'-{} seconds'.format(windowInSecs//2),time,'+{} seconds'.format(windowInSecs//2))).fetchall()
    correspondingVitalTimes = np.array([item['timestamp'] for item in t])
    vitalValues = np.array([item['values(SpO2)'] for item in t], dtype=np.float)
    vitalValues2 = np.array([item['values(Heart Rate)'] for item in t], dtype=np.float)
    idx = np.argwhere(~np.isnan(vitalValues))
    idx2 = np.argwhere(~np.isnan(vitalValues2))
    logger.info(vitalValues)


    # Grab a certain number of PPG datapoints based on window size, page, and fs.
    t = v.execute("SELECT * FROM pleth WHERE (timestamp > DATETIME(?, ?) AND timestamp < DATETIME(?, ?))",(time,'-{} seconds'.format(windowInSecs//2),time,'+{} seconds'.format(windowInSecs//2))).fetchall()
    ppgTimesAsStr = np.array([item['timestamp'] for item in t])
    ppgValues = np.array([item['first(Pleth)'] for item in t])
    logger.info(ppgValues)


    # Grab the qos times corresponding to the grabbed PPG times (via conditional indexing).
    t = v.execute("SELECT * FROM qos WHERE (timestamp > DATETIME(?, ?) AND timestamp < DATETIME(?, ?))",(time,'-{} seconds'.format(windowInSecs//2),time,'+{} seconds'.format(windowInSecs//2))).fetchall()
    correspondingQosTimes = np.array([item['timestamp'] for item in t])
    qosValues = np.array([item['values(qos)'] for item in t])
    logger.info(qosValues)

    # # Grab the ekg times corresponding to the grabbed PPG times (via conditional indexing).
    t = v.execute("SELECT * FROM ekg WHERE (timestamp > DATETIME(?, ?) AND timestamp < DATETIME(?, ?))",(time,'-{} seconds'.format(windowInSecs//2),time,'+{} seconds'.format(windowInSecs//2))).fetchall()
    correspondingEkgTimes = np.array([item['timestamp'] for item in t])
    ekgValues = np.array([item['first(ecg)'] for item in t])
    logger.info(ekgValues)

    # BEST PRACTICE --- update .data in one step with a new dict (according to Bokeh site/docs).
    # Create new dictionaries which will hold new "step" of data.
    newPpgData = dict()
    newQosData = dict()
    newEkgData = dict()
    newVitalData = dict()
    newVitalData2 = dict()


    # Convert times to datetime objects (for bokeh axis) and assign values to new dicts.
    newPpgData['x'] = pd.to_datetime(ppgTimesAsStr)
    newPpgData['y'] = ppgValues
    newPpgData['time'] = ppgTimesAsStr

    newEkgData['x'] = pd.to_datetime(correspondingEkgTimes)
    newEkgData['y'] = ekgValues
    newEkgData['time'] = correspondingEkgTimes

    newQosData['x'] = pd.to_datetime(correspondingQosTimes)
    newQosData['y'] = qosValues
    newQosData['time'] = correspondingQosTimes

    newVitalData['x'] = pd.to_datetime(correspondingVitalTimes[idx].ravel())
    newVitalData['y'] = vitalValues[idx]
    newVitalData['time'] = correspondingVitalTimes[idx]

    newVitalData2['x'] = pd.to_datetime(correspondingVitalTimes[idx2].ravel())
    newVitalData2['y'] = vitalValues2[idx2]
    newVitalData2['time'] = correspondingVitalTimes[idx2]


    # Update the datasources with the new data.
    ekgDataSource.data = newEkgData
    ppgDataSource.data = newPpgData
    qosDataSource.data = newQosData
    vitalDataSource.data = newVitalData
    vitalDataSource2.data = newVitalData2


    # Change the value of the page indicator.
    pageIndicator.value = '{0!s}/{1!s}'.format(currentPage+1, totalPages)

    # logger.info(currentPage, '/', totalPages)


def jump_forward():
    """ Callback for forward button. Increment the current page and recursively call change_page() function.
    """

    global currentPage

    # Prevent annotator from jumping past final page.
    if currentPage < totalPages:
        currentPage += 1
        change_page()

    else:
        pass


def jump_backward():
    """ Callback for forward button. Decrement the current page and recursively call change_page() function.
    """

    global currentPage

    if currentPage > 0:
        currentPage -= 1
        change_page()

    else:
        pass


def slide_to_page(attrname, old, new):
    """Set the current page to the value indicated by the slider on movement.

    Parameters -- required by bokeh
    ----------
    attrname:str
        'value'

    old:int
        Previous value of the slider widget

    new:int
        New (i.e. just changed to) value of the slider widget

    Returns
    -------

    """

    global currentPage, jumpSlider

    if jumpSlider.value > currentPage:

        # -1 for python vs slider indexing
        currentPage = jumpSlider.value - 1
        jump_forward()

    elif jumpSlider.value < currentPage:
        currentPage = jumpSlider.value + 1
        jump_backward()

    else:
        logger.info('error')


def resize_y_scale(attrname, old, new):
    """Change the scale of the y-axis.

    Parameters -- required by Bokeh
    ----------
    attrname:str
        'value'

    old:int
        Previous value of the slider widget

    new:int
        New (i.e. just changed to) value of the slider widget

    Returns
    -------

    """

    global yScalesToSelect, ppgViewer

    newScale = yScalesToSelect[new - 1]
    ppgViewer.y_range.start = newScale[0]
    ppgViewer.y_range.end = newScale[1]


def change_time_window(attrname, old, new):
    """Change the scale of the y-axis.

    Parameters -- required by Bokeh
    ----------
    attrname:str
        'value'

    old:int
        Previous value of the slider widget

    new:int
        New (i.e. just changed to) value of the slider widget

    Returns
    -------
    """

    global windowInSecs, totalPages, jumpSlider

    windowInSecs = new
    # totalPages = int(ppgDataFrame['time'].size / (windowInSecs * fs)) - 1
    jumpSlider.end = totalPages
    change_page()


def ppgViewerSelectionCallback(attr, old, new):
    """Create an annotation based on the geometry of the box select tool.

    Parameters
    ----------
    attr:str
        'geometries'

    old:list
        e.g. [{'vx0': 464, 'vy0': 23.7869873046875, 'y0': 0, 'y1': 4503.400000000001, 'type': 'rect', 'x0': 1481149362095.9377, 'vx1': 552, 'x1': 1481149364565.3564, 'vy1': 341.03603515625}]

    new:list
        e.g. [{'vx0': 464, 'vy0': 23.7869873046875, 'y0': 0, 'y1': 4503.400000000001, 'type': 'rect', 'x0': 1481149362095.9377, 'vx1': 552, 'x1': 1481149364565.3564, 'vy1': 341.03603515625}]


    Returns
    -------

    """

    # Provide globals to help reader know what is local and global
    global ppgViewer, ppgDataFrame, args, ppgColorSelector, qosColorSelector, ppgButtonGroup, qosButtonGroup


    # Edge case. Make sure minimum x value for annotation is 0.
    if new[0]['x0'] < 0:
        x0 = 0
    else:
        x0 = abs(int(new[0]['x0']))

    x1 = abs(int(new[0]['x1']))

    # Create box annotation. Color of annotation depends on which button in a group is selected (active).
    ppgComments = BoxAnnotation(fill_color=ppgColorSelector[ppgButtonGroup.active])
    ppgViewer.add_layout(ppgComments)

    ppgComments.left = x0
    ppgComments.right = x1

    # Create box annotation. Color of annotation depends on which button in a group is selected (active).
    qosComments = BoxAnnotation(fill_color=qosColorSelector[qosButtonGroup.active], fill_alpha=1)
    ppgViewer.add_layout(qosComments)

    qosComments.top = annotatorSettings.ppgYRange[1]
    qosComments.bottom = annotatorSettings.ppgYRange[1] - 100
    qosComments.left = x0
    qosComments.right = x1

    save_annotation_dimensions(x0,x1,args.spo2QosAnnotatedFile)


def ekgViewerSelectionCallback(attr, old, new):
    """Create an annotation based on the geometry of the box select tool.

    Parameters
    ----------
    attr:str
        'geometries'

    old:list
        e.g. [{'vx0': 464, 'vy0': 23.7869873046875, 'y0': 0, 'y1': 4503.400000000001, 'type': 'rect', 'x0': 1481149362095.9377, 'vx1': 552, 'x1': 1481149364565.3564, 'vy1': 341.03603515625}]

    new:list
        e.g. [{'vx0': 464, 'vy0': 23.7869873046875, 'y0': 0, 'y1': 4503.400000000001, 'type': 'rect', 'x0': 1481149362095.9377, 'vx1': 552, 'x1': 1481149364565.3564, 'vy1': 341.03603515625}]


    Returns
    -------

    """

    # Provide globals to help reader know what is local and global
    global ekgViewer, args, ekgColorSelector, ekgButtonGroup

    # Edge case. Make sure minimum x value for annotation is 0.
    if new[0]['x0'] < 0:
        x0 = 0
    else:
        x0 = abs(int(new[0]['x0']))

    x1 = abs(int(new[0]['x1']))

    # Create box annotation. Color of annotation depends on which button in a group is selected (active).
    ekgComments = BoxAnnotation(fill_color=ekgColorSelector[ekgButtonGroup.active])
    ekgComments.left = x0
    ekgComments.right = x1
    ekgViewer.add_layout(ekgComments)

    save_annotation_dimensions(x0,x1,args.ekgAnnotatedFile)


def save_annotation_dimensions(left, right, file):

    if file == args.spo2QosAnnotatedFile:

        ppgCode = dict(enumerate(annotatorSettings.ppgCodes))
        qosCode = dict(enumerate(annotatorSettings.qosCodes))

        # Save coordinates and values of notes and save to file.
        with open(file,'a+') as outfile:

            outfile.write('{},{},{},{}'.format(datetime.datetime.fromtimestamp(left/1000).isoformat()[:-3],
                                               datetime.datetime.fromtimestamp(right/1000).isoformat()[:-3],
                                               ppgCode[ppgButtonGroup.active],
                                               qosCode[qosButtonGroup.active],
                                               )
                          )
            outfile.write('\n')


    elif file == args.ekgAnnotatedFile:

        ekgCode = dict(enumerate(annotatorSettings.ekgCodes))

        # Save coordinates and values of notes and save to file.
        with open(file,'a+') as outfile:

            outfile.write('{},{},{}'.format(datetime.datetime.fromtimestamp(left/1000).isoformat()[:-3],
                                               datetime.datetime.fromtimestamp(right/1000).isoformat()[:-3],
                                            ekgCode[ekgButtonGroup.active],
                                            ))
            outfile.write('\n')


    else:
        warnings.warn('nothing implemented')

def annotate_selection(attrname, old, new):

    if new == '':
        pass
    else:

        annotationTextInput.value = ''

#########################
#### OTHER FUNCTIONS ####
#########################

def load_existing_ppgQos_annotations(startTime, endTime, ppgNote, qosNote):
    """Loads existing annotations from file.

    Parameters -- from file column headers
    ----------
    startTime:str
        Timestamp marking beginning of annotation, preferably in ISO format.

    endTime:str
        Timestamp marking end of annotation, preferably in ISO format.

    ppgNote:str
        Annotation code for PPG (e.g. "PPG Interpretable")

    qosNote:str
        Annotation code for QoS (e.g. "QoS Correct")

    Returns
    -------

    """

    global ppgColorSelector, ppgViewer

    ppgIdx = annotatorSettings.ppgCodes.index(ppgNote)
    qosIdx = annotatorSettings.qosCodes.index(qosNote)

    # Use ppgNote and qosNote to determine color of loaded annotation to add to plot.
    ppgComments = BoxAnnotation(fill_color=ppgColorSelector[ppgIdx])
    ppgViewer.add_layout(ppgComments)

    # FIXME: Timestamp issue likely in the future.
    # I honestly do not know why these values work...but there is a current issue with Bokeh datetime.
    # I subtracted the timestamp provided by x1 and the known epoch UTC timestamp of 1/1/2020 to get 18000000000000.
    # I divided by various magnitudes of 10 until timestamp on bokeh was correct.
    ppgComments.left = (pd.to_datetime(str(startTime)).value+18000000000000)/1000000
    ppgComments.right = (pd.to_datetime(str(endTime)).value+18000000000000)/1000000

    qosComments = BoxAnnotation(fill_color=qosColorSelector[qosIdx],fill_alpha=1)
    ppgViewer.add_layout(qosComments)
    qosComments.top = annotatorSettings.ppgYRange[1]
    qosComments.bottom = annotatorSettings.ppgYRange[1] - 100

    qosComments.left = (pd.to_datetime(str(startTime)).value+18000000000000)/1000000
    qosComments.right = (pd.to_datetime(str(endTime)).value+18000000000000)/1000000

def load_existing_ekgAnnotations(startTime, endTime, ekgNote):
    """Loads existing annotations from file.

    Parameters -- from column file headers
    ----------
    startTime:str
        Timestamp marking beginning of annotation, preferably in ISO format.

    endTime:str
        Timestamp marking end of annotation, preferably in ISO format.

    ekgNote:str
        Annotation code for EKG (e.g. "EKG Interpretable")

    Returns
    -------

    """

    global ekgColorSelector

    ekgIdx = annotatorSettings.ekgCodes.index(ekgNote)

    ekgComments = BoxAnnotation(fill_color=ekgColorSelector[ekgIdx])
    ekgViewer.add_layout(ekgComments)

    # FIXME: Timestamp issue likely in the future.
    # I honestly do not know why these values work...but there is a current issue with Bokeh datetime.
    # I subtracted the timestamp provided by x1 and the known epoch UTC timestamp of 1/1/2020 to get 18000000000000.
    # I divided by various magnitudes of 10 until timestamp on bokeh was correct.
    ekgComments.left = (pd.to_datetime(str(startTime)).value+18000000000000)/1000000
    ekgComments.right = (pd.to_datetime(str(endTime)).value+18000000000000)/1000000


with open(spo2QosAnnotatedFile,'r') as readfile:
    reader = csv.reader(readfile)
    next(reader)
    for row in reader:
        load_existing_ppgQos_annotations(row[0], row[1], row[2], row[3])

with open(ekgAnnotatedFile,'r') as readfile:
    reader = csv.reader(readfile)
    next(reader)
    for row in reader:
        load_existing_ekgAnnotations(row[0], row[1], row[2])


#########################################
#### 8. CONNECT FUNCTIONS TO WIDGETS ####
#########################################

ppgViewer.tool_events.on_change("geometries", ppgViewerSelectionCallback)
ekgViewer.tool_events.on_change("geometries", ekgViewerSelectionCallback)
fwdButton.on_click(jump_forward)
bckButton.on_click(jump_backward)
jumpSlider.on_change('value', slide_to_page)
yScaleSlider.on_change('value', resize_y_scale)
timeSlider.on_change('value', change_time_window)
annotationTextInput.on_change('value', annotate_selection)

#######################
#### 9. INITIALIZE ####
#######################

jump_forward()

###################################################
#### 10. Add plot and widgets to the document. ####
###################################################

curdoc().add_root(Column(
    vitalViewer,
    vitalViewer2,
    ppgViewer,
    ekgViewer,
    ekgButtonGroup,
    ppgButtonGroup,
    qosButtonGroup,
    HBox(pageIndicator, bckButton, fwdButton),
    # VBox(HBox(ekgButtonGroup, ppgButtonGroup, qosButtonGroup), HBox(pageIndicator, bckButton, fwdButton)),
    HBox(yScaleSlider, timeSlider, jumpSlider),

)

)
