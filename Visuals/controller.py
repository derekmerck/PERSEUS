from __future__ import division

import argparse
import datetime
import time
import warnings
# import memory_profiler
import logging
import pytz

import numpy as np
import pandas as pd

from bokeh.models.tools import BoxAnnotation

import annotatorSettings
import csv
import os.path

logger = logging.getLogger()

import views
import model

def parse_args():
    """ Create command line interface for entering command line arguments.

    Returns
    -------
    parsedArgs: Parser object
        Object for holding parsed command line arguments

    """

    now = time.strftime("%Y-%m-%dT%H-%M-%S")

    parser = argparse.ArgumentParser()
    parser.add_argument('rawJsonFile')
    parser.add_argument('alarmsFile')

    parser.add_argument('-p','--preload', action="store_true")
    parser.add_argument('-s','--spo2QosAnnotatedFile', default="{}_ppgFile.txt".format(now), nargs='?')
    parser.add_argument('-e','--ekgAnnotatedFile', default="{}_ekgFile.txt".format(now), nargs='?')
    parser.add_argument('-b','--bpAnnotatedFile', default="{}_bpFile.txt".format(now), nargs='?')
    parsedArgs = parser.parse_args()

    return parsedArgs

def check_files(args):

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

    if os.path.isfile(args.bpAnnotatedFile):

        warnings.warn("File {} already exists and will be written to. Please check to make sure you are annotating the correct file.".format(args.bpAnnotatedFile))

        bpAnnotatedFile = args.bpAnnotatedFile

    else:
        with open(args.bpAnnotatedFile,'w') as outfile:
            outfile.write('{},{},{}'.format('startTime','endTime','bpNote'))
            outfile.write('\n')

            bpAnnotatedFile = outfile.name

def start_controller(args):
    logger.info('Loading user interface')
    views.start_view()
    logger.info('User interface loaded')

    logger.info('Loading alarms')
    alarms = model.Alarms(args.alarmsFile)
    alarms.load_alarms()
    logger.info('Alarms loaded')

    if args.preload:
        logger.info('Loading physio data -- data will be preloaded')
        data = model.Data(args.rawJsonFile)
        data.load_physio_data()
        data.create_single_data_streams(load_then_display=True)
        logger.info('Physio data loaded')

    else:
        logger.info('Loading physio data -- data will be computed on the fly')
        data = model.Data(args.rawJsonFile)
        data.load_physio_data()
        data.create_single_data_streams(load_then_display=False)
        logger.info('Physio data loaded')

    return alarms, data

args = parse_args()
logger.info(args)
check_files(args)
alarms, data = start_controller(args)

alarmNumber = -1
pageNumber = -1

def expand_pleth_times(timestamp):
    x = pd.date_range(timestamp, periods=32,freq='8L',closed="left")
    return x

def expand_ecg_times(timestamp):
    x = pd.date_range(timestamp, periods=64,freq='4L',closed="left")
    return x

def get_next_alarm():
    global alarmNumber, pageNumber

    if alarmNumber < alarms.number_of_alarms:

        alarmNumber += 1
        pageNumber = 0

        views.alarmIndicator.value='{0!s}/{1!s}'.format(alarmNumber+1,alarms.number_of_alarms+1)

        change_page()
        add_anno()
        change_viewer_title_text()

def get_previous_alarm():
    global alarmNumber, pageNumber

    if alarmNumber > 0:
        alarmNumber -= 1
        pageNumber = 0

        views.alarmIndicator.value='{0!s}/{1!s}'.format(alarmNumber+1,alarms.number_of_alarms+1)

        change_page()
        change_viewer_title_text()

def next_page():
    global pageNumber

    pageNumber += 1

    change_page()

def previous_page():
    global pageNumber

    if pageNumber > 0:
        pageNumber -= 1

        change_page()

def change_page():

    if pageNumber < 10:

        begin = alarms.alarms[alarmNumber] - pd.Timedelta('315 seconds') + pageNumber*pd.Timedelta('60 seconds')
        end = begin + pd.Timedelta('60 seconds')

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

        newEkgData['x'] = np.hstack(data.ecg[begin:end].index.to_series().apply(expand_ecg_times))
        newEkgData['y'] = np.hstack(data.ecg[begin:end].values)

        newPpgData['x'] = np.hstack(data.pleth[begin:end].index.to_series().apply(expand_pleth_times))
        newPpgData['y'] = np.hstack(data.pleth[begin:end].values)

        newPpgData2['x'] = np.hstack(data.pleth[begin:end].index.to_series().apply(expand_pleth_times))
        newPpgData2['y'] = np.hstack(data.pleth[begin:end].values)

        newQosData['x'] = data.qos[begin:end].index
        newQosData['y'] = data.qos[begin:end].values

        newQosData2['x'] = data.qos[begin:end].index
        newQosData2['y'] = data.qos[begin+pd.Timedelta('5 seconds'):end+pd.Timedelta('5 seconds')].values[:-5]
        newQosData2['x'] = newQosData2['x'][:newQosData2['y'].size]

        newSpo2Data['x'] = data.spo2[begin:end].index
        newSpo2Data['y'] = data.spo2[begin:end].values

        newHrData['x'] = data.hr[begin:end].index
        newHrData['y'] = data.hr[begin:end].values

        if data.load_then_display:
            # Uncomment for long load time but short page time
            newNibpSysData['x'] = data.nibp[begin:end].index
            newNibpSysData['y'] = data.nibp[begin:end].systolic.values

            newNibpMeanData['x'] = data.nibp[begin:end].index
            newNibpMeanData['y'] = data.nibp[begin:end]['mean'].values

            newNibpDiaData['x'] = data.nibp[begin:end].index
            newNibpDiaData['y'] = data.nibp[begin:end].diastolic.values

        else:
            # Uncomment for short load time but long page time
            newNibpSysData['x'] = data.nibp[begin:end].dropna().apply(pd.Series).apply(pd.to_numeric,errors='coerce').dropna().index
            newNibpSysData['y'] = data.nibp[begin:end].dropna().apply(pd.Series).apply(pd.to_numeric,errors='coerce').dropna().systolic.values

            newNibpMeanData['x'] = data.nibp[begin:end].dropna().apply(pd.Series).apply(pd.to_numeric,errors='coerce').dropna().index
            newNibpMeanData['y'] = data.nibp[begin:end].dropna().apply(pd.Series).apply(pd.to_numeric,errors='coerce').dropna()['mean'].values

            newNibpDiaData['x'] = data.nibp[begin:end].dropna().apply(pd.Series).apply(pd.to_numeric,errors='coerce').dropna().index
            newNibpDiaData['y'] = data.nibp[begin:end].dropna().apply(pd.Series).apply(pd.to_numeric,errors='coerce').dropna().diastolic.values


        views.ekgDataSource.data = newEkgData
        views.ppgDataSource.data = newPpgData
        views.hrDataSource.data = newHrData
        views.ppgDataSource2.data = newPpgData2
        views.spo2DataSource.data = newSpo2Data
        views.qosDataSource.data = newQosData
        views.qosDataSource2.data = newQosData2
        views.nibpSysDataSource.data = newNibpSysData
        views.nibpMeanDataSource.data = newNibpMeanData
        views.nibpDiaDataSource.data = newNibpDiaData


        views.pageIndicator.value='{0!s}/{1!s}'.format(pageNumber+1, 10)

    else:

        pass

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


    # Edge case. Make sure minimum x value for annotation is 0.
    if new[0]['x0'] < 0:
        x0 = 0
    else:
        x0 = abs(int(new[0]['x0']))

    x1 = abs(int(new[0]['x1']))

    # Create box annotation. Color of annotation depends on which button in a group is selected (active).
    ppgComments = BoxAnnotation(fill_color=annotatorSettings.ppgColorSelector[views.ppgButtonGroup.active])
    views.ppgViewer.add_layout(ppgComments)

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

def add_anno():
    alarm = alarms.alarms[alarmNumber]
    ala = BoxAnnotation(fill_color=annotatorSettings.alarmColor,fill_alpha=0.5)
    ala2 = BoxAnnotation(fill_color=annotatorSettings.alarmColor,fill_alpha=0.5)
    ala3 = BoxAnnotation(fill_color=annotatorSettings.alarmColor,fill_alpha=0.5)
    ala5 = BoxAnnotation(fill_color=annotatorSettings.alarmColor,fill_alpha=0.5)
    ala6 = BoxAnnotation(fill_color=annotatorSettings.alarmColor,fill_alpha=0.5)
    ala7 = BoxAnnotation(fill_color=annotatorSettings.alarmColor,fill_alpha=0.5)

    views.ekgViewer.add_layout(ala)
    views.ppgViewer.add_layout(ala2)
    views.hrViewer.add_layout(ala3)
    views.bpViewer.add_layout(ala5)
    views.spo2Viewer.add_layout(ala6)
    views.ppgViewer2.add_layout(ala7)

    ala.left = pd.to_datetime(str(alarm))-pd.Timedelta('0.25 seconds')
    ala.right = pd.to_datetime(str(alarm))+pd.Timedelta('0.25 seconds')
    ala2.left = pd.to_datetime(str(alarm))-pd.Timedelta('0.25 seconds')
    ala2.right = pd.to_datetime(str(alarm))+pd.Timedelta('0.25 seconds')
    ala3.left = pd.to_datetime(str(alarm))-pd.Timedelta('0.25 seconds')
    ala3.right = pd.to_datetime(str(alarm))+pd.Timedelta('0.25 seconds')
    ala5.left = pd.to_datetime(str(alarm))-pd.Timedelta('0.25 seconds')
    ala5.right = pd.to_datetime(str(alarm))+pd.Timedelta('0.25 seconds')
    ala6.left = pd.to_datetime(str(alarm))-pd.Timedelta('0.25 seconds')
    ala6.right = pd.to_datetime(str(alarm))+pd.Timedelta('0.25 seconds')
    ala7.left = pd.to_datetime(str(alarm))-pd.Timedelta('0.25 seconds')
    ala7.right = pd.to_datetime(str(alarm))+pd.Timedelta('0.25 seconds')

def change_viewer_title_text():
    views.ekgViewer.title.text = 'ECG: '+ str(alarms.alarms[alarmNumber].astimezone(pytz.utc)) + ' '+ str(alarms.desc[alarmNumber])
    views.ppgViewer.title.text = 'Pleth: '+ str(alarms.alarms[alarmNumber].astimezone(pytz.utc)) +' '+str(alarms.desc[alarmNumber])
    views.hrViewer.title.text = 'Heart Rate: '+ str(alarms.alarms[alarmNumber].astimezone(pytz.utc)) +' '+str(alarms.desc[alarmNumber])
    views.bpViewer.title.text = 'Non-invasive Blood Pressure: '+ str(alarms.alarms[alarmNumber].astimezone(pytz.utc)) +' '+str(alarms.desc[alarmNumber])
    views.spo2Viewer.title.text = 'SpO2: '+ str(alarms.alarms[alarmNumber].astimezone(pytz.utc)) +' '+str(alarms.desc[alarmNumber])
    views.ppgViewer2.title.text = 'Pleth -5 Offset: '+ str(alarms.alarms[alarmNumber].astimezone(pytz.utc)) +' '+str(alarms.desc[alarmNumber])

def save_annotation_dimensions(left, right, file, qos2=False):

    if file == args.spo2QosAnnotatedFile:
        if not qos2:
            ppgCode = dict(enumerate(annotatorSettings.ppgCodes))
            qosCode = dict(enumerate(annotatorSettings.qosCodes))

            # Save coordinates and values of notes and save to file.
            with open(file,'a+') as outfile:

                outfile.write('{},{},{},'.format(datetime.datetime.fromtimestamp(left/1000).isoformat()[:-3],
                                                   datetime.datetime.fromtimestamp(right/1000).isoformat()[:-3],
                                                   ppgCode[views.ppgButtonGroup.active],
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
                                                   qosCode[views.qosButtonGroup.active],
                                                   )
                              )
                outfile.write('\n')


    elif file == args.ekgAnnotatedFile:

        ekgCode = dict(enumerate(annotatorSettings.ekgCodes))

        # Save coordinates and values of notes and save to file.
        with open(file,'a+') as outfile:

            outfile.write('{},{},{}'.format(datetime.datetime.fromtimestamp(left/1000).isoformat()[:-3],
                                               datetime.datetime.fromtimestamp(right/1000).isoformat()[:-3],
                                            ekgCode[views.ekgButtonGroup.active],
                                            ))
            outfile.write('\n')

    elif file == args.bpAnnotatedFile:

        bpCode = dict(enumerate(annotatorSettings.bpCodes))

        # Save coordinates and values of notes and save to file.
        with open(file,'a+') as outfile:

            outfile.write('{},{},{}'.format(datetime.datetime.fromtimestamp(left/1000).isoformat()[:-3],
                                               datetime.datetime.fromtimestamp(right/1000).isoformat()[:-3],
                                            bpCode[views.bpButtonGroup.active],
                                            ))
            outfile.write('\n')

    else:
        warnings.warn('nothing implemented')

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


    # Edge case. Make sure minimum x value for annotation is 0.
    if new[0]['x0'] < 0:
        x0 = 0
    else:
        x0 = abs(int(new[0]['x0']))

    x1 = abs(int(new[0]['x1']))

    # Create box annotation. Color of annotation depends on which button in a group is selected (active).
    qosComments = BoxAnnotation(fill_color=annotatorSettings.qosColorSelector[views.qosButtonGroup.active], fill_alpha=0.5)
    views.ppgViewer2.add_layout(qosComments)

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

    # Edge case. Make sure minimum x value for annotation is 0.
    if new[0]['x0'] < 0:
        x0 = 0
    else:
        x0 = abs(int(new[0]['x0']))

    x1 = abs(int(new[0]['x1']))

    # Create box annotation. Color of annotation depends on which button in a group is selected (active).
    ekgComments = BoxAnnotation(fill_color=annotatorSettings.ekgColorSelector[views.ekgButtonGroup.active])
    ekgComments.left = x0
    ekgComments.right = x1
    views.ekgViewer.add_layout(ekgComments)

    save_annotation_dimensions(x0,x1,args.ekgAnnotatedFile)

def bpViewerSelectionCallback(attr, old, new):
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

    # Edge case. Make sure minimum x value for annotation is 0.
    if new[0]['x0'] < 0:
        x0 = 0
    else:
        x0 = abs(int(new[0]['x0']))

    x1 = abs(int(new[0]['x1']))

    # Create box annotation. Color of annotation depends on which button in a group is selected (active).
    bpComments = BoxAnnotation(fill_color=annotatorSettings.bpColorSelector[views.bpButtonGroup.active])
    bpComments.left = x0
    bpComments.right = x1
    views.bpViewer.add_layout(bpComments)

    save_annotation_dimensions(x0,x1,args.bpAnnotatedFile)

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

    if ppgNote != '':
        ppgIdx = annotatorSettings.ppgCodes.index(ppgNote)

        # Use ppgNote and qosNote to determine color of loaded annotation to add to plot.
        ppgComments = BoxAnnotation(fill_color=annotatorSettings.ppgColorSelector[ppgIdx])
        views.ppgViewer.add_layout(ppgComments)

        # FIXME: Timestamp issue likely in the future.
        # I honestly do not know why these values work...but there is a current issue with Bokeh datetime.
        # I subtracted the timestamp provided by x1 and the known epoch UTC timestamp of 1/1/2020 to get 18000000000000.
        # I divided by various magnitudes of 10 until timestamp on bokeh was correct.
        ppgComments.left = pd.to_datetime(str(startTime)).tz_localize('Etc/GMT+4')
        ppgComments.right = pd.to_datetime(str(endTime)).tz_localize('Etc/GMT+4')

    if qosNote != '':
        qosIdx = annotatorSettings.qosCodes.index(qosNote)
        qosComments = BoxAnnotation(fill_color=annotatorSettings.qosColorSelector[qosIdx],fill_alpha=0.5)
        views.ppgViewer2.add_layout(qosComments)
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

    ekgIdx = annotatorSettings.ekgCodes.index(ekgNote)

    ekgComments = BoxAnnotation(fill_color=annotatorSettings.ekgColorSelector[ekgIdx])
    views.ekgViewer.add_layout(ekgComments)

    # FIXME: Timestamp issue likely in the future.
    # I honestly do not know why these values work...but there is a current issue with Bokeh datetime.
    # I subtracted the timestamp provided by x1 and the known epoch UTC timestamp of 1/1/2020 to get 18000000000000.
    # I divided by various magnitudes of 10 until timestamp on bokeh was correct.
    ekgComments.left = pd.to_datetime(str(startTime)).tz_localize('Etc/GMT+4')
    ekgComments.right = pd.to_datetime(str(endTime)).tz_localize('Etc/GMT+4')

with open(args.spo2QosAnnotatedFile,'r') as readfile:
    reader = csv.reader(readfile)
    next(reader)
    for row in reader:
        load_existing_ppgQos_annotations(row[0], row[1], row[2], row[3])

with open(args.ekgAnnotatedFile,'r') as readfile:
    reader = csv.reader(readfile)
    next(reader)
    for row in reader:
        load_existing_ekgAnnotations(row[0], row[1], row[2])

views.fwdButton.on_click(next_page)
views.bckButton.on_click(previous_page)
views.fwdAlarmButton.on_click(get_next_alarm)
views.bckAlarmButton.on_click(get_previous_alarm)
views.alarmIndicator.value='{0!s}/{1!s}'.format(alarmNumber+1,alarms.number_of_alarms)
views.ppgViewer.tool_events.on_change("geometries", ppgViewerSelectionCallback)
views.ppgViewer2.tool_events.on_change("geometries", ppgViewer2SelectionCallback)
views.ekgViewer.tool_events.on_change("geometries", ekgViewerSelectionCallback)
views.bpViewer.tool_events.on_change("geometries", bpViewerSelectionCallback)

alarmNumber +=1
views.alarmIndicator.value='{0!s}/{1!s}'.format(alarmNumber+1,alarms.number_of_alarms)
next_page()
change_viewer_title_text()
add_anno()
