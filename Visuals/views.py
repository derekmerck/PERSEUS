from __future__ import division

# import memory_profiler
import logging

from bokeh.io import curdoc
from bokeh.models import Range1d, DatetimeTickFormatter, Circle, ColumnDataSource, Label, Span
from bokeh.models.layouts import Column, HBox, VBox, Row
from bokeh.models.tools import HoverTool, BoxSelectTool, TapTool, WheelZoomTool, ResizeTool, BoxAnnotation
from bokeh.models.widgets import Slider, TextInput, Button, RadioButtonGroup, DataTable, TableColumn
from bokeh.plotting import figure

import annotatorSettings
logger = logging.getLogger()


# FIXME: Clean up plots
###########################
#### 3. CREATE VIEWERS ####
###########################


def _create_viewer(title,y_range,toolbar_location=None,toolbar_sticky=False,tools="",
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


bpViewer = _create_viewer("Non-invasive Blood Pressure",annotatorSettings.YRange3,plot_height=annotatorSettings.nibpViewerHeight)
hrViewer = _create_viewer("Heart Rate",annotatorSettings.hrYRange,plot_height=annotatorSettings.hrViewerHeight)
spo2Viewer = _create_viewer("SpO2",annotatorSettings.spo2YRange,plot_height=annotatorSettings.spo2ViewerHeight)

ekgViewer = _create_viewer("ECG",annotatorSettings.ekgYRange)

ppgViewer = _create_viewer("Pleth",annotatorSettings.ppgYRange)
ppgViewer.extra_y_ranges = {"qosRange": Range1d(start=-1.1, end=1.1)}

ppgViewer2 = _create_viewer("Pleth: -5 Second Offset",annotatorSettings.ppgYRange)
ppgViewer2.extra_y_ranges = {"qosRange": Range1d(start=-1.1, end=1.1)}


######################################################
#### 4. CREATE LINES AND DATASOURCES FOR PLOTTING ####
######################################################

hrLine = hrViewer.line(x=[], y=[], color=annotatorSettings.hrLineColor)
hrPatch = hrViewer.patch(x=[],y=[],color='black',alpha=0.5)

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
hrDataSource2 = hrPatch.data_source
nibpSysDataSource = nibpSysLine.data_source
nibpMeanDataSource = nibpMeanLine.data_source
nibpDiaDataSource = nibpDiaLine.data_source
spo2DataSource = spo2Line.data_source



# FIXME: Clean up widgets
################################################################################
#### 6. ADD WIDGETS FOR INTERACTIONS (callbacks assigned at end of script). ####
################################################################################

fwdButton = Button(label="Next")
bckButton = Button(label="Previous")
fwdAlarmButton = Button(label="Next Alarm")
bckAlarmButton = Button(label="Previous Alarm")
pageIndicator = TextInput(value='{0!s}/{1!s}'.format(0, 10), title='Current Page')
alarmIndicator = TextInput(value='{0!s}/{1!s}'.format(0, 0), title='Current Alarm')
annotationTextInput = TextInput(title='Enter annotation below:')
ekgButtonGroup = RadioButtonGroup(labels=annotatorSettings.ekgCodes, active=0, width=annotatorSettings.viewerWidth)
ppgButtonGroup = RadioButtonGroup(labels=annotatorSettings.ppgCodes, active=0, width=annotatorSettings.viewerWidth)
qosButtonGroup = RadioButtonGroup(labels=annotatorSettings.qosCodes, active=0, width=annotatorSettings.viewerWidth)

def start_view():
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
