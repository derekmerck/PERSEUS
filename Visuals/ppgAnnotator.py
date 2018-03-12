"""
For Python 2.7.x

Sixth(?) iteration of offline visual dataviewer and annotator. Written in Bokeh 0.12.6.
As per the documentation and gallery examples, script makes use of global variables. Will try to make easier to read in
future revisions, but initial attempts at class based OOP version was slower than current implementation.

Run using:
    bokeh serve --show ScriptName.py --args rawJsonFile.json alarmsFile.csv [-s pleth/qosAnnotation.txt] [-e ekgAnnotation.txt]

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
import time
import warnings
# import memory_profiler
import logging

import numpy as np
import pandas as pd
from bokeh.io import curdoc
from bokeh.models import Range1d, DatetimeTickFormatter, Circle, ColumnDataSource, Label, Span
from bokeh.models.layouts import Column, HBox, VBox, Row
from bokeh.models.tools import HoverTool, BoxSelectTool, TapTool, WheelZoomTool, ResizeTool, BoxAnnotation
from bokeh.models.widgets import Slider, TextInput, Button, RadioButtonGroup, DataTable, TableColumn
from bokeh.plotting import figure

import annotatorSettings
import csv
import os.path

logger = logging.getLogger()
# logger.disabled = True

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
    parser.add_argument('rawJsonFile')
    parser.add_argument('alarmsFile')

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

alarms_df = pd.read_csv(args.alarmsFile,parse_dates=[0])
alarms_df.set_index("_time", inplace=True)
alarms_df.tz_localize("UTC",copy=False).tz_convert('Etc/GMT+4',copy=False)
alarms = alarms_df.index.to_pydatetime()

number_of_alarms = alarms.size
current_alarm_number = 0
# alarm = alarms[0]

# Note: Timestamps are read in and kept as object dtype
physio_df = pd.read_json(args.rawJsonFile, lines=True)
physio_df.set_index("timestamp",inplace=True)
physio_df.tz_localize('Etc/GMT+4',copy=False)

pleth = physio_df['Pleth'].dropna()
ecg = physio_df['ECG'].dropna()
hr = physio_df['Heart Rate'].apply(pd.to_numeric,errors='coerce').dropna()
spo2 = physio_df['SpO2'].apply(pd.to_numeric,errors='coerce').dropna()
qos = physio_df['qos'].apply(pd.to_numeric,errors='coerce').dropna()
qos = qos[~qos.index.duplicated(keep='first')]
nibp = physio_df['Non-invasive Blood Pressure']

cleaned_physio_df = pd.concat([pleth.reset_index(),ecg.reset_index(),hr.reset_index(),spo2.reset_index(),qos.reset_index(),nibp.reset_index()])
cleaned_physio_df.set_index('timestamp',inplace=True)
cleaned_physio_df.sort_index(inplace=True)
# cleaned_physio_df.index = cleaned_physio_df.index.to_pydatetime()
# print(cleaned_physio_df.head())

# cleaned_physio_df = physio_df.groupby(physio_df.index).first().combine_first(physio_df.groupby(physio_df.index).last())
# cleaned_physio_df[['Heart Rate','Respiration Rate','SpO2','qos']] = cleaned_physio_df[['Heart Rate','Respiration Rate','SpO2','qos']].apply(pd.to_numeric,errors='coerce')

# cols = [0,7]
# cleaned_physio_df.drop(cleaned_physio_df.columns[cols],axis=1,inplace=True)

# print(cleaned_physio_df.head())

qos_df_offset = cleaned_physio_df[["qos"]].set_index(cleaned_physio_df.index - pd.Timedelta('5 seconds'))



isolated_dfs = []
isolated_qos_dfs = []
for alarm in alarms:
    # print(alarm)

    star = pd.Timestamp(alarm-pd.Timedelta("{} seconds".format(annotatorSettings.timeAroundAlarm)))
    sto = pd.Timestamp(alarm+pd.Timedelta("{} seconds".format(annotatorSettings.timeAroundAlarm)))

    # print(star)
    # print(sto)
    df = cleaned_physio_df[star:sto]
    qdf = qos_df_offset[star:sto]
    ndf = pd.DataFrame()
    ndf[["diastolic_bp","mean_bp","systolic_bp"]] = df["Non-invasive Blood Pressure"].dropna().apply(pd.Series).apply(pd.to_numeric,errors='coerce')
    df = pd.concat([df.reset_index(),ndf.reset_index()])
    df.set_index('timestamp',inplace=True)
    df.sort_index(inplace=True)
    isolated_dfs.append(df)
    isolated_qos_dfs.append(qdf)

del physio_df, cleaned_physio_df, qos_df_offset
del hr, spo2, qos, nibp, pleth, ecg


# FIXME: Clean up plots
###########################
#### 3. CREATE VIEWERS ####
###########################


def create_viewer(title,y_range,toolbar_location=None,toolbar_sticky=False,tools="",
                    plot_width=annotatorSettings.viewerWidth,
                    plot_height=annotatorSettings.defaultViewerHeights,x_axis_type='datetime',
                    add_tools=True):

    viewer = figure(
        title=title,
        tools=tools,
        plot_width=plot_width,
        plot_height=plot_height,
        toolbar_location=toolbar_location,
        # toolbar_sticky=False,
        x_axis_type=x_axis_type,
        y_range=y_range,

    )

    viewer.xaxis.formatter = DatetimeTickFormatter(
        years=["%F %T"],
        months=["%F %T"],
        days=["%F %T"],
        hours=["%F %T"],
        hourmin=["%F %T"],
        minutes=["%F %T"],
        minsec=["%F %T"],
        seconds=["%F %T"],
        milliseconds=["%F %T.%3N"],
    )

    # Create tools to add to ekgViewer.
    wheel_zoom = WheelZoomTool()
    tap_tool = TapTool()
    resizeTool = ResizeTool()
    box_select = BoxSelectTool(dimensions="width")
    hover = HoverTool(
        point_policy='snap_to_data',
        line_policy='nearest',
        tooltips=[
        ("index", "$index"),
        ("Time", "@x{%F %T.%3N %Z}"),
        ("Value", "@y"),
        # ("Time", '@time'),
        ],
        formatters={"x": "datetime"},

    )

    if add_tools:
        viewer.add_tools(hover, box_select, tap_tool,resizeTool)
        viewer.toolbar.active_drag = box_select
        viewer.toolbar.active_scroll = wheel_zoom
        viewer.toolbar.active_tap = tap_tool

    return viewer


bpViewer = create_viewer("Non-invasive Blood Pressure",annotatorSettings.YRange3,plot_height=annotatorSettings.nibpViewerHeight)
hrViewer = create_viewer("Heart Rate",annotatorSettings.hrYRange,plot_height=annotatorSettings.hrViewerHeight)
spo2Viewer = create_viewer("SpO2",annotatorSettings.spo2YRange,plot_height=annotatorSettings.spo2ViewerHeight)

ekgViewer = create_viewer("ECG",annotatorSettings.ekgYRange)

ppgViewer = create_viewer("Pleth",annotatorSettings.ppgYRange)
ppgViewer.extra_y_ranges = {"qosRange": Range1d(start=-1.1, end=1.1)}

ppgViewer2 = create_viewer("Pleth: -5 Second Offset",annotatorSettings.ppgYRange)
ppgViewer2.extra_y_ranges = {"qosRange": Range1d(start=-1.1, end=1.1)}


######################################################
#### 4. CREATE LINES AND DATASOURCES FOR PLOTTING ####
######################################################

hrLine = hrViewer.line(x=[], y=[], color=annotatorSettings.hrLineColor)
spo2Line = spo2Viewer.line(x=[], y=[], color=annotatorSettings.spo2LineColor)
nibpSysLine = bpViewer.line(x=[], y=[], color=annotatorSettings.nibpSysLineColor)
nibpMeanLine = bpViewer.line(x=[], y=[], color=annotatorSettings.nibpMeanLineColor)
nibpDiaLine = bpViewer.line(x=[], y=[], color=annotatorSettings.nibpDiaLineColor)

ekgLine = ekgViewer.line(x=[], y=[], color=annotatorSettings.ekgLineColor, alpha=0.9)
ppgLine = ppgViewer.line(x=[], y=[], color=annotatorSettings.ppgLineColor, alpha=0.9)
ppgLine2 = ppgViewer2.line(x=[], y=[], color=annotatorSettings.ppgLineColor, alpha=0.9)
qosMarkers = ppgViewer.circle(x=[], y=[], color=annotatorSettings.qosMarkerColor, y_range_name='qosRange', line_width=0)
qosMarkers2 = ppgViewer2.circle(x=[], y=[], color=annotatorSettings.qosMarkerColor, y_range_name='qosRange', line_width=0)

ekgDataSource = ekgLine.data_source
ppgDataSource = ppgLine.data_source
ppgDataSource2 = ppgLine2.data_source
qosDataSource = qosMarkers.data_source
qosDataSource2 = qosMarkers2.data_source
hrDataSource = hrLine.data_source
nibpSysDataSource = nibpSysLine.data_source
nibpMeanDataSource = nibpMeanLine.data_source
nibpDiaDataSource = nibpDiaLine.data_source
spo2DataSource = spo2Line.data_source

##################################
#### 5. SETTINGS FOR DISPLAYS ####
##################################

fs = annotatorSettings.ppgFrequency
windowInSecs = annotatorSettings.windowInSecs

yScalesToSelect = [annotatorSettings.ppgYRange,[-10000,10000],[-30000,30000]]

currentPage = annotatorSettings.initializePage
totalPages = 10

ekgColorSelector = annotatorSettings.ekgColorSelector
ppgColorSelector = annotatorSettings.ppgColorSelector
qosColorSelector = annotatorSettings.qosColorSelector

# FIXME: Clean up widgets
################################################################################
#### 6. ADD WIDGETS FOR INTERACTIONS (callbacks assigned at end of script). ####
################################################################################

fwdButton = Button(label="Next")
bckButton = Button(label="Previous")
fwdAlarmButton = Button(label="Next Alarm")
bckAlarmButton = Button(label="Previous Alarm")

jumpSlider = Slider(title='Jump to page', start=0, end=totalPages, step=1)
yScaleSlider = Slider(title='Y-scale', start=1, end=len(yScalesToSelect), step=1)
timeSlider = Slider(title='Window in secs', start=annotatorSettings.timeSliderStart, end=annotatorSettings.timeSliderEnd, value=annotatorSettings.timeSliderInitialValue, step=annotatorSettings.timeSliderStep)
pageIndicator = TextInput(value='{0!s}/{1!s}'.format(currentPage+1, totalPages), title='Current Page')
alarmIndicator = TextInput(value='{0!s}/{1!s}'.format(current_alarm_number+1, number_of_alarms), title='Current Alarm')
annotationTextInput = TextInput(title='Enter annotation below:')
ekgButtonGroup = RadioButtonGroup(labels=annotatorSettings.ekgCodes, active=0, width=annotatorSettings.viewerWidth)
ppgButtonGroup = RadioButtonGroup(labels=annotatorSettings.ppgCodes, active=0, width=annotatorSettings.viewerWidth)
qosButtonGroup = RadioButtonGroup(labels=annotatorSettings.qosCodes, active=0, width=annotatorSettings.viewerWidth)

# FIXME: Clean up callbacks
###############################
#### 7. CALLBACK FUNCTIONS ####
###############################


def expand_pleth_times(timestamp):
    x = pd.date_range(timestamp, periods=32,freq='8L',closed="left")
    return x

def expand_ecg_times(timestamp):
    x = pd.date_range(timestamp, periods=64,freq='4L',closed="left")
    return x

def next_alarm():
    global alarms, alarm, currentPage, number_of_alarms, current_alarm_number, alarmIndicator

    current_alarm_number += 1

    alarm = alarms[current_alarm_number]

    alarmIndicator.value = '{0!s}/{1!s}'.format(current_alarm_number+1, number_of_alarms)

    currentPage = -1

    print(alarms_df.iloc[current_alarm_number])

    jump_forward()

def previous_alarm():
    global alarms, alarm, currentPage, number_of_alarms, current_alarm_number, alarmIndicator

    current_alarm_number -= 1

    alarm = alarms[current_alarm_number]

    alarmIndicator.value = '{0!s}/{1!s}'.format(current_alarm_number+1, number_of_alarms)

    currentPage = -1

    # logger.info(alarm)
    print(alarms_df.iloc[current_alarm_number])

    jump_backward()

#@profile
def change_page():
    """ Request new data to be served to the plot.
    """

    # Call globals just as a reminder to denote what is local and what is global. Globals only being accesed, not reassigned.
    # global ppgDataFrame, qosDataFrame, ekgDataFrame, ppgDataSource, qosDataSource, ekgDataSource, currentPage, vitalDataSource, vitalDataSource2,vitalDataSource3,vitalDataSource4,vitalDataSource5, cleaned_physio_df, alarms
    global isolated_physio_df, current_alarm_number

    isolated_physio_df = isolated_dfs[current_alarm_number]
    qos_df_offset = isolated_qos_dfs[current_alarm_number]

    # cleaned_physio_df[alarm-pd.Timedelta("{} seconds".format(annotatorSettings.timeAroundAlarm)):alarm+pd.Timedelta("{} seconds".format(annotatorSettings.timeAroundAlarm))]
    # isolated_physio_df[["diastolic_bp","mean_bp","systolic_bp"]] = isolated_physio_df["Non-invasive Blood Pressure"].apply(pd.Series).apply(pd.to_numeric,errors='coerce')

    start = isolated_physio_df.index[0].to_pydatetime()
    increment = currentPage*pd.Timedelta("{} seconds".format(annotatorSettings.windowInSecs))
    window_length = pd.Timedelta("{} seconds".format(annotatorSettings.windowInSecs))

    # BEST PRACTICE --- update .data in one step with a new dict (according to Bokeh site/docs).
    # Create new dictionaries which will hold new "step" of data.
    newPpgData = dict()
    newPpgData2 = dict()
    newQosData = dict()
    newQosData2 = dict()
    newEkgData = dict()
    newHrData = dict()
    newSpo2Data = dict()
    newNibpSysData = dict()
    newNibpMeanData = dict()
    newNibpDiaData = dict()

    # Convert times to datetime objects (for bokeh axis) and assign values to new dicts.
    newPpgData['x'] = np.hstack(isolated_physio_df[start+increment:start+increment+window_length].Pleth.dropna().index.to_series().apply(expand_pleth_times))
    newPpgData['y'] = np.hstack(isolated_physio_df[start+increment:start+increment+window_length].Pleth.dropna())

    newPpgData2['x'] = np.hstack(isolated_physio_df[start+increment:start+increment+window_length].Pleth.dropna().index.to_series().apply(expand_pleth_times))
    newPpgData2['y'] = np.hstack(isolated_physio_df[start+increment:start+increment+window_length].Pleth.dropna())

    newEkgData['x'] = np.hstack(isolated_physio_df[start+increment:start+increment+window_length].ECG.dropna().index.to_series().apply(expand_ecg_times))
    newEkgData['y'] = np.hstack(isolated_physio_df[start+increment:start+increment+window_length].ECG.dropna())

    newQosData['x'] = isolated_physio_df[start+increment:start+increment+window_length].qos.dropna().index.to_series()
    newQosData['y'] = isolated_physio_df[start+increment:start+increment+window_length].qos.dropna()

    newQosData2['x'] = qos_df_offset[start+increment:start+increment+window_length].qos.dropna().index.to_series()
    newQosData2['y'] = qos_df_offset[start+increment:start+increment+window_length].qos.dropna()

    newSpo2Data['x'] = isolated_physio_df[start+increment:start+increment+window_length].SpO2.dropna().index.to_series()
    newSpo2Data['y'] = isolated_physio_df[start+increment:start+increment+window_length].SpO2.dropna()

    newHrData['x'] = isolated_physio_df[start+increment:start+increment+window_length]["Heart Rate"].dropna().index.to_series()
    newHrData['y'] = isolated_physio_df[start+increment:start+increment+window_length]["Heart Rate"].dropna()

    newNibpSysData['x'] = isolated_physio_df[start+increment:start+increment+window_length].systolic_bp.dropna().index.to_series()
    newNibpSysData['y'] = isolated_physio_df[start+increment:start+increment+window_length].systolic_bp.dropna()

    newNibpMeanData['x'] = isolated_physio_df[start+increment:start+increment+window_length].mean_bp.dropna().index.to_series()
    newNibpMeanData['y'] = isolated_physio_df[start+increment:start+increment+window_length].mean_bp.dropna()

    newNibpDiaData['x'] = isolated_physio_df[start+increment:start+increment+window_length].diastolic_bp.dropna().index.to_series()
    newNibpDiaData['y'] = isolated_physio_df[start+increment:start+increment+window_length].diastolic_bp.dropna()


    # Update the datasources with the new data.
    ekgDataSource.data = newEkgData
    ppgDataSource.data = newPpgData
    ppgDataSource2.data = newPpgData2
    qosDataSource.data = newQosData
    qosDataSource2.data = newQosData2
    hrDataSource.data = newHrData
    spo2DataSource.data = newSpo2Data
    nibpSysDataSource.data = newNibpSysData
    nibpMeanDataSource.data = newNibpMeanData
    nibpDiaDataSource.data = newNibpDiaData

    # logger.info(newVitalData)

    # print(alarm > start + increment and alarm < start+increment+window_length)
    # if alarm > start+increment and alarm < start+increment+window_length:
    #     # loc = pd.to_datetime(alarm).tz_localize('Etc/GMT+4')
    #     # loc = pd.to_datetime(alarm)
    #     # loc = time.mktime(alarm.timetuple())*1000
    #     # vline = Span(dimension='height', line_color='red', line_width=3)
    #     # ekgViewer.add_layout(vline)
    #     # vline.location = loc
    #
    #     ala = BoxAnnotation(fill_color='purple',fill_alpha=0.5)
    #     ala2 = BoxAnnotation(fill_color='purple',fill_alpha=0.5)
    #     ala3 = BoxAnnotation(fill_color='purple',fill_alpha=0.5)
    #     ala4 = BoxAnnotation(fill_color='purple',fill_alpha=0.5)
    #     ala5 = BoxAnnotation(fill_color='purple',fill_alpha=0.5)
    #     ala6 = BoxAnnotation(fill_color='purple',fill_alpha=0.5)
    #
    #
    #     ekgViewer.add_layout(ala)
    #     ppgViewer.add_layout(ala2)
    #     hrViewer.add_layout(ala3)
    #     ekgViewer.add_layout(ala4)
    #     bpViewer.add_layout(ala5)
    #     spo2Viewer.add_layout(ala6)
    #
    #     ala.left = pd.to_datetime(str(alarm))-pd.Timedelta('0.25 seconds')
    #     ala.right = pd.to_datetime(str(alarm))+pd.Timedelta('0.25 seconds')
    #     ala2.left = pd.to_datetime(str(alarm))-pd.Timedelta('0.25 seconds')
    #     ala2.right = pd.to_datetime(str(alarm))+pd.Timedelta('0.25 seconds')
    #     ala3.left = pd.to_datetime(str(alarm))-pd.Timedelta('0.25 seconds')
    #     ala3.right = pd.to_datetime(str(alarm))+pd.Timedelta('0.25 seconds')
    #     ala4.left = pd.to_datetime(str(alarm))-pd.Timedelta('0.25 seconds')
    #     ala4.right = pd.to_datetime(str(alarm))+pd.Timedelta('0.25 seconds')
    #     ala5.left = pd.to_datetime(str(alarm))-pd.Timedelta('0.25 seconds')
    #     ala5.right = pd.to_datetime(str(alarm))+pd.Timedelta('0.25 seconds')
    #     ala6.left = pd.to_datetime(str(alarm))-pd.Timedelta('0.25 seconds')
    #     ala6.right = pd.to_datetime(str(alarm))+pd.Timedelta('0.25 seconds')

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


# def slide_to_page(attrname, old, new):
#     """Set the current page to the value indicated by the slider on movement.
#
#     Parameters -- required by bokeh
#     ----------
#     attrname:str
#         'value'
#
#     old:int
#         Previous value of the slider widget
#
#     new:int
#         New (i.e. just changed to) value of the slider widget
#
#     Returns
#     -------
#
#     """
#
#     global currentPage, jumpSlider
#
#     if jumpSlider.value > currentPage:
#
#         # -1 for python vs slider indexing
#         currentPage = jumpSlider.value - 1
#         jump_forward()
#
#     elif jumpSlider.value < currentPage:
#         currentPage = jumpSlider.value + 1
#         jump_backward()
#
#     else:
#         logger.info('error')


# def resize_y_scale(attrname, old, new):
#     """Change the scale of the y-axis.
#
#     Parameters -- required by Bokeh
#     ----------
#     attrname:str
#         'value'
#
#     old:int
#         Previous value of the slider widget
#
#     new:int
#         New (i.e. just changed to) value of the slider widget
#
#     Returns
#     -------
#
#     """
#
#     global yScalesToSelect, ppgViewer
#
#     newScale = yScalesToSelect[new - 1]
#     ppgViewer.y_range.start = newScale[0]
#     ppgViewer.y_range.end = newScale[1]


# def change_time_window(attrname, old, new):
#     """Change the scale of the y-axis.
#
#     Parameters -- required by Bokeh
#     ----------
#     attrname:str
#         'value'
#
#     old:int
#         Previous value of the slider widget
#
#     new:int
#         New (i.e. just changed to) value of the slider widget
#
#     Returns
#     -------
#     """
#
#     global windowInSecs, totalPages, jumpSlider
#
#     windowInSecs = new
#     # totalPages = int(ppgDataFrame['time'].size / (windowInSecs * fs)) - 1
#     jumpSlider.end = totalPages
#     change_page()

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

    # # Create box annotation. Color of annotation depends on which button in a group is selected (active).
    # qosComments = BoxAnnotation(fill_color=qosColorSelector[qosButtonGroup.active], fill_alpha=1)
    # ppgViewer.add_layout(qosComments)
    #
    # qosComments.top = annotatorSettings.ppgYRange[1]
    # qosComments.bottom = annotatorSettings.ppgYRange[1] - 100
    # qosComments.left = x0
    # qosComments.right = x1

    save_annotation_dimensions(x0,x1,args.spo2QosAnnotatedFile)

def ppgViewer2SelectionCallback(attr, old, new):
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
    global ppgViewer2, ppgDataFrame, args, ppgColorSelector, qosColorSelector, ppgButtonGroup, qosButtonGroup


    # Edge case. Make sure minimum x value for annotation is 0.
    if new[0]['x0'] < 0:
        x0 = 0
    else:
        x0 = abs(int(new[0]['x0']))

    x1 = abs(int(new[0]['x1']))

    # Create box annotation. Color of annotation depends on which button in a group is selected (active).
    qosComments = BoxAnnotation(fill_color=qosColorSelector[qosButtonGroup.active], fill_alpha=0.5)
    ppgViewer2.add_layout(qosComments)

    # qosComments.top = annotatorSettings.ppgYRange[1]
    # qosComments.bottom = annotatorSettings.ppgYRange[1] - 100
    qosComments.left = x0
    qosComments.right = x1

    save_annotation_dimensions(x0,x1,args.spo2QosAnnotatedFile,qos2=True)


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


def save_annotation_dimensions(left, right, file, qos2=False):

    if file == args.spo2QosAnnotatedFile:
        if not qos2:
            ppgCode = dict(enumerate(annotatorSettings.ppgCodes))
            qosCode = dict(enumerate(annotatorSettings.qosCodes))

            # Save coordinates and values of notes and save to file.
            with open(file,'a+') as outfile:

                outfile.write('{},{},{},'.format(datetime.datetime.fromtimestamp(left/1000).isoformat()[:-3],
                                                   datetime.datetime.fromtimestamp(right/1000).isoformat()[:-3],
                                                   ppgCode[ppgButtonGroup.active],
                                                   )
                              )
                outfile.write('\n')

        else:
            ppgCode = dict(enumerate(annotatorSettings.ppgCodes))
            qosCode = dict(enumerate(annotatorSettings.qosCodes))

            # Save coordinates and values of notes and save to file.
            with open(file,'a+') as outfile:

                outfile.write('{},{},,{}'.format(datetime.datetime.fromtimestamp(left/1000).isoformat()[:-3],
                                                   datetime.datetime.fromtimestamp(right/1000).isoformat()[:-3],
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

# def annotate_selection(attrname, old, new):
#
#     if new == '':
#         pass
#     else:
#
#         annotationTextInput.value = ''

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

    if ppgNote != '':
        ppgIdx = annotatorSettings.ppgCodes.index(ppgNote)

        # Use ppgNote and qosNote to determine color of loaded annotation to add to plot.
        ppgComments = BoxAnnotation(fill_color=ppgColorSelector[ppgIdx])
        ppgViewer.add_layout(ppgComments)

        # FIXME: Timestamp issue likely in the future.
        # I honestly do not know why these values work...but there is a current issue with Bokeh datetime.
        # I subtracted the timestamp provided by x1 and the known epoch UTC timestamp of 1/1/2020 to get 18000000000000.
        # I divided by various magnitudes of 10 until timestamp on bokeh was correct.
        ppgComments.left = pd.to_datetime(str(startTime)).tz_localize('Etc/GMT+4')
        ppgComments.right = pd.to_datetime(str(endTime)).tz_localize('Etc/GMT+4')

    if qosNote != '':
        qosIdx = annotatorSettings.qosCodes.index(qosNote)
        qosComments = BoxAnnotation(fill_color=qosColorSelector[qosIdx],fill_alpha=0.5)
        ppgViewer2.add_layout(qosComments)
        # qosComments.top = annotatorSettings.ppgYRange[1]
        # qosComments.bottom = annotatorSettings.ppgYRange[1] - 100

        qosComments.left = pd.to_datetime(str(startTime)).tz_localize('Etc/GMT+4')
        qosComments.right = pd.to_datetime(str(endTime)).tz_localize('Etc/GMT+4')

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
    ekgComments.left = pd.to_datetime(str(startTime)).tz_localize('Etc/GMT+4')
    ekgComments.right = pd.to_datetime(str(endTime)).tz_localize('Etc/GMT+4')


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


for alarm in alarms:
    ala = BoxAnnotation(fill_color=annotatorSettings.alarmColor,fill_alpha=0.5)
    ala2 = BoxAnnotation(fill_color=annotatorSettings.alarmColor,fill_alpha=0.5)
    ala3 = BoxAnnotation(fill_color=annotatorSettings.alarmColor,fill_alpha=0.5)
    ala4 = BoxAnnotation(fill_color=annotatorSettings.alarmColor,fill_alpha=0.5)
    ala5 = BoxAnnotation(fill_color=annotatorSettings.alarmColor,fill_alpha=0.5)
    ala6 = BoxAnnotation(fill_color=annotatorSettings.alarmColor,fill_alpha=0.5)


    ekgViewer.add_layout(ala)
    ppgViewer.add_layout(ala2)
    hrViewer.add_layout(ala3)
    ekgViewer.add_layout(ala4)
    bpViewer.add_layout(ala5)
    spo2Viewer.add_layout(ala6)

    ala.left = pd.to_datetime(str(alarm))-pd.Timedelta('0.25 seconds')
    ala.right = pd.to_datetime(str(alarm))+pd.Timedelta('0.25 seconds')
    ala2.left = pd.to_datetime(str(alarm))-pd.Timedelta('0.25 seconds')
    ala2.right = pd.to_datetime(str(alarm))+pd.Timedelta('0.25 seconds')
    ala3.left = pd.to_datetime(str(alarm))-pd.Timedelta('0.25 seconds')
    ala3.right = pd.to_datetime(str(alarm))+pd.Timedelta('0.25 seconds')
    ala4.left = pd.to_datetime(str(alarm))-pd.Timedelta('0.25 seconds')
    ala4.right = pd.to_datetime(str(alarm))+pd.Timedelta('0.25 seconds')
    ala5.left = pd.to_datetime(str(alarm))-pd.Timedelta('0.25 seconds')
    ala5.right = pd.to_datetime(str(alarm))+pd.Timedelta('0.25 seconds')
    ala6.left = pd.to_datetime(str(alarm))-pd.Timedelta('0.25 seconds')
    ala6.right = pd.to_datetime(str(alarm))+pd.Timedelta('0.25 seconds')


#########################################
#### 8. CONNECT FUNCTIONS TO WIDGETS ####
#########################################

ppgViewer.tool_events.on_change("geometries", ppgViewerSelectionCallback)
ppgViewer2.tool_events.on_change("geometries", ppgViewer2SelectionCallback)
ekgViewer.tool_events.on_change("geometries", ekgViewerSelectionCallback)
fwdButton.on_click(jump_forward)
bckButton.on_click(jump_backward)
fwdAlarmButton.on_click(next_alarm)
bckAlarmButton.on_click(previous_alarm)
# jumpSlider.on_change('value', slide_to_page)
# yScaleSlider.on_change('value', resize_y_scale)
# timeSlider.on_change('value', change_time_window)
# annotationTextInput.on_change('value', annotate_selection)

#######################
#### 9. INITIALIZE ####
#######################

jump_forward()
print(alarms_df.iloc[current_alarm_number])

###################################################
#### 10. Add plot and widgets to the document. ####
###################################################

curdoc().add_root(Column(
    bpViewer,
    hrViewer,
    spo2Viewer,
    ppgViewer,
    ppgButtonGroup,
    ppgViewer2,
    qosButtonGroup,
    ekgViewer,
    ekgButtonGroup,
    Row(pageIndicator, bckButton, fwdButton),
    Row(alarmIndicator, bckAlarmButton, fwdAlarmButton),
    # Row(pageIndicator, bckButton, fwdButton,alarmIndicator, bckAlarmButton, fwdAlarmButton)

)

)
