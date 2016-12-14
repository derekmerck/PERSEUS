"""
First implementation of offline visual dataviewer and annotator. Written in Bokeh 0.12.3.
As per the documentation and gallery examples, script makes use of global variables. Will try to make easier to read in
future revisions, but initial attempts at class based OOP version was slower than current implementation.

Run using:
bokeh serve --show ScriptName.py --args ppgFile.txt qosFile.txt annotatedFile.txt

Useful tutorials/comments can be found at:

http://bokeh.pydata.org/en/latest/docs/user_guide/server.html
http://stackoverflow.com/questions/33869292/how-can-i-set-the-x-axis-as-datetimes-on-a-bokeh-plot/33873209#33873209
http://bokeh.pydata.org/en/latest/docs/reference/models/formatters.html
http://stackoverflow.com/questions/969285/how-do-i-translate-a-iso-8601-datetime-string-into-a-python-datetime-object

@author: aoyalowo
"""

from bokeh.io import curdoc
from bokeh.models import Range1d, DatetimeTickFormatter, Circle
from bokeh.plotting import figure
from bokeh.models.layouts import Column, HBox
from bokeh.models.widgets import Slider, TextInput, Button
from bokeh.models.tools import HoverTool, BoxSelectTool, TapTool, WheelZoomTool
import pandas as pd
import numpy as np
import sys

# FIXME: Clean up load data (functions perhaps?)
#### Load pleth data and qos data from csv files. ####
ppgFile = str(sys.argv[1])
qosFile = str(sys.argv[2])

try:
    annotatedFile = sys.argv[3]
except IndexError:
    annotatedFile = None

#### Create file to save annotations. ####
if annotatedFile:
    annotationFileName = annotatedFile
else:
    annotationFileName = "{}_Annotations.txt".format(ppgFile)

    with open(annotationFileName, 'a') as f:
        f.write('"timestamp","Annotation"')
        f.write('\n')

#### Create dataframes from loaded data. ####
ppgDataFrame = pd.read_csv(ppgFile, header=0, names=['time', 'pleth'], low_memory=False)
qosDataFrame = pd.read_csv(qosFile, header=0, names=['time', 'qos'], low_memory=False)
ppgDataFrame['notes'] = pd.Series(data=np.full(ppgDataFrame.index.shape, 'None', dtype='object'), dtype='object')

if annotatedFile:
    annotatedDataFrame = pd.read_csv(annotatedFile, header=0, names=['time', 'notes'], low_memory=False)
    ppgDataFrame.loc[ppgDataFrame['time'].isin(annotatedDataFrame['time']), ['notes']] = annotatedDataFrame.sort_values('time')['notes'].values
    print("Will load existing annotations.")
else:
    print("No existing annotations to load.")

#### CUSTOMIZABLE SETTINGS ####
currentPage = -1
windowInSecs = 30
fs = 128
selectedIdx = np.array([]).astype(np.object)
yScalesToSelect = [[ppgDataFrame['pleth'].min(), ppgDataFrame['pleth'].max() * 1.1], [-15000, 15000], [-30000, 30000]]
totalPages = int(ppgDataFrame['time'].size / (windowInSecs * fs)) - 1

# FIXME: Clean up widgets

#### Add widgets for interactions (callbacks assigned below). ####
fwdButton = Button(label="Next")
bckButton = Button(label="Previous")
jumpSlider = Slider(title='Jump to page', start=0, end=totalPages, step=1)
yScaleSlider = Slider(title='Y-scale', start=1, end=len(yScalesToSelect), step=1)
timeSlider = Slider(title='Window in secs', start=15, end=120, value=30, step=15)
pageIndicator = TextInput(value='{0!s}/{1!s}'.format(currentPage, totalPages), title='Current Page')
annotationTextInput = TextInput(title='Enter annotation below:')

# FIXME: Clean up plots

#### Create the figure to plot and format its properties. ####

mainViewer = figure(
    title=ppgFile,
    plot_width=1200,
    plot_height=550,
    toolbar_location='below',
    toolbar_sticky=False,
    x_axis_type='datetime',
    y_range=[ppgDataFrame['pleth'].min(), ppgDataFrame['pleth'].max() * 1.1],
    # tools=TOOLS,
    # active_drag='box_select',
    # active_tap='tap',
    # active_scroll='wheel_zoom',
)
mainViewer.extra_y_ranges = {"qosRange": Range1d(start=-1.1, end=1.1)}
mainViewer.xaxis.formatter = DatetimeTickFormatter(
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

#### Add empty lines and markers and assign their data sources. ####
ppgLine = mainViewer.line(x=[], y=[], color='navy', alpha=0.5)
ppgLineMarkers = mainViewer.circle(x=[], y=[], color='navy', alpha=0.5, visible=False)
qosMarkers = mainViewer.circle(x=[], y=[], color='red', y_range_name='qosRange')
annotation = mainViewer.line(x=[], y=[], color='navy', visible=True, line_width=3)

ppgDataSource = ppgLine.data_source
ppgLineMarkersDataSource = ppgLineMarkers.data_source
qosDataSource = qosMarkers.data_source
annotatedDataSource = annotation.data_source

#### Describe how selected data are handled. ####
selected_circle = Circle(fill_color='navy', visible=True)
nonselected_circle = Circle(fill_color='navy', visible=False)
ppgLineMarkers.selection_glyph = selected_circle
ppgLineMarkers.nonselection_glyph = nonselected_circle

wheel_zoom = WheelZoomTool()
tap_tool = TapTool()
box_select = BoxSelectTool(dimensions="width")
hover = HoverTool(
    point_policy='snap_to_data',
    line_policy='nearest',
    tooltips=[
        ("index", "$index"),
        ("Value", "@y"),
        # ("desc", "@desc"),
        ("Time", '@time'),
        ("Note", "@notes"),
    ],
    renderers=[
        qosMarkers,
        ppgLineMarkers,
    ]
)

mainViewer.add_tools(hover, box_select, tap_tool)
mainViewer.toolbar.active_drag = box_select
mainViewer.toolbar.active_scroll = wheel_zoom
mainViewer.toolbar.active_tap = tap_tool


# FIXME: Clean up callbacks

def jump_forward():
    """
    Callback for forward button. Increment the current page and create new data sources based on a dataframe subselection.

    :return:
    """
    global currentPage, ppgDataFrame

    currentPage += 1

    ppgTimesAsStr = ppgDataFrame['time'][currentPage * windowInSecs * fs:(currentPage * windowInSecs * fs) + (windowInSecs * fs)]
    correspondingQosTimes = qosDataFrame['time'][qosDataFrame['time'] > ppgTimesAsStr.values[0]][qosDataFrame['time'] < ppgTimesAsStr.values[-1]]
    qosValues = qosDataFrame['qos'][correspondingQosTimes.index]

    # BEST PRACTICE --- update .data in one step with a new dict
    newPpgData = dict()
    newQosData = dict()
    newAnnotatedData = dict()

    newPpgData['x'] = pd.to_datetime(ppgTimesAsStr)
    newPpgData['y'] = ppgDataFrame['pleth'][currentPage * windowInSecs * fs:(currentPage * windowInSecs * fs) + (windowInSecs * fs)]
    newPpgData['time'] = ppgTimesAsStr
    newPpgData['notes'] = ppgDataFrame['notes'][currentPage * windowInSecs * fs:(currentPage * windowInSecs * fs) + (windowInSecs * fs)]

    annotatedDataFrame = pd.DataFrame(newPpgData)
    newAnnotatedData['x'] = annotatedDataFrame['x'][annotatedDataFrame['notes'] != 'None']
    newAnnotatedData['y'] = annotatedDataFrame['y'][annotatedDataFrame['notes'] != 'None']

    newQosData['x'] = pd.to_datetime(correspondingQosTimes)
    newQosData['y'] = qosValues
    newQosData['time'] = correspondingQosTimes

    annotatedDataSource.data = newAnnotatedData
    ppgDataSource.data = newPpgData
    ppgLineMarkersDataSource.data = newPpgData
    qosDataSource.data = newQosData

    pageIndicator.value = '{0!s}/{1!s}'.format(currentPage, totalPages)

    print(currentPage, '/', totalPages)


def jump_backward():
    """
    Callback for backward button. Increment the current page and create new data sources based on a dataframe subselection.

    :return:
    """

    global currentPage, ppgDataFrame

    currentPage -= 1

    ppgTimesAsStr = ppgDataFrame['time'][currentPage * windowInSecs * fs:(currentPage * windowInSecs * fs) + (windowInSecs * fs)]
    correspondingQosTimes = qosDataFrame['time'][qosDataFrame['time'] > ppgTimesAsStr.values[0]][qosDataFrame['time'] < ppgTimesAsStr.values[-1]]
    qosValues = qosDataFrame['qos'][correspondingQosTimes.index]

    # BEST PRACTICE --- update .data in one step with a new dict
    newPpgData = dict()
    newQosData = dict()
    newAnnotatedData = dict()

    newPpgData['x'] = pd.to_datetime(ppgTimesAsStr)
    newPpgData['y'] = ppgDataFrame['pleth'][currentPage * windowInSecs * fs:(currentPage * windowInSecs * fs) + (windowInSecs * fs)]
    newPpgData['time'] = ppgTimesAsStr
    newPpgData['notes'] = ppgDataFrame['notes'][currentPage * windowInSecs * fs:(currentPage * windowInSecs * fs) + (windowInSecs * fs)]

    annotatedDataFrame = pd.DataFrame(newPpgData)
    newAnnotatedData['x'] = annotatedDataFrame['x'][annotatedDataFrame['notes'] != 'None']
    newAnnotatedData['y'] = annotatedDataFrame['y'][annotatedDataFrame['notes'] != 'None']

    newQosData['x'] = pd.to_datetime(correspondingQosTimes)
    newQosData['y'] = qosValues
    newQosData['time'] = correspondingQosTimes

    annotatedDataSource.data = newAnnotatedData
    ppgDataSource.data = newPpgData
    ppgLineMarkersDataSource.data = newPpgData
    qosDataSource.data = newQosData

    pageIndicator.value = '{0!s}/{1!s}'.format(currentPage, totalPages)

    print(currentPage, '/', totalPages)


def slide_to_page(attrname, old, new):
    """
    Callback for slider. Parameters required by bokeh.
    :param attrname: Name of the attribute (in this case 'value')
    :param old: The previous value
    :param new: The new/current/updated value
    :return:
    """

    global currentPage

    if jumpSlider.value > currentPage:
        currentPage = jumpSlider.value - 1
        jump_forward()

    elif jumpSlider.value < currentPage:
        currentPage = jumpSlider.value + 1
        jump_backward()

    else:
        print('error')


def selection_change(attrname, old, new):
    """
    Callback for selection. Parameters required by bokeh.
    :param attrname: Name of the attribute (in this case 'value')
    :param old: The previous value
    :param new: The new/current/updated value
    :return:
    """
    global selectedIdx
    selected = new['1d']['indices']
    selected.sort()
    selectedIdx = np.array([selected])


def annotate_selection(attrname, old, new):
    """
    Callback for selection. Parameters required by bokeh.
    :param attrname: Name of the attribute (in this case 'value')
    :param old: The previous value
    :param new: The new/current/updated value
    :return:
    """

    if new == '':
        pass
    else:
        # ppgDataFrame['notes'][selectedIdx[0] + (currentPage*windowInSecs*fs)] = new
        ppgDataFrame.loc[selectedIdx[0] + (currentPage * windowInSecs * fs), ['notes']] = new
        temp = ppgDataFrame[['time', 'notes']]
        temp2 = temp.loc[selectedIdx[0] + (currentPage * windowInSecs * fs)]
        temp2.to_csv(annotationFileName, mode='a', index=False, header=False)
        annotationTextInput.value = ''


def resize_y_scale(attrname, old, new):
    """
    Callback for slider. Parameters required by bokeh.
    :param attrname: Name of the attribute (in this case 'value')
    :param old: The previous value
    :param new: The new/current/updated value
    :return:
    """
    newScale = yScalesToSelect[new - 1]
    mainViewer.y_range.start = newScale[0]
    mainViewer.y_range.end = newScale[1]


def change_time_window(attrname, old, new):
    """
    Callback for slider. Parameters required by bokeh.
    :param attrname: Name of the attribute (in this case 'value')
    :param old: The previous value
    :param new: The new/current/updated value
    :return:
    """
    global windowInSecs, totalPages
    windowInSecs = new
    totalPages = int(ppgDataFrame['time'].size / (windowInSecs * fs)) - 1
    jumpSlider.end = totalPages


fwdButton.on_click(jump_forward)
bckButton.on_click(jump_backward)
jumpSlider.on_change('value', slide_to_page)
yScaleSlider.on_change('value', resize_y_scale)
timeSlider.on_change('value', change_time_window)
annotationTextInput.on_change('value', annotate_selection)
ppgDataSource.on_change('selected', selection_change)
ppgLineMarkersDataSource.on_change('selected', selection_change)

#### Initialize ####
jump_forward()

#### Add plot and widgets to the document. ####
curdoc().add_root(Column(

    mainViewer,
    HBox(pageIndicator, annotationTextInput, bckButton, fwdButton),
    HBox(yScaleSlider, timeSlider, jumpSlider),

)

)
