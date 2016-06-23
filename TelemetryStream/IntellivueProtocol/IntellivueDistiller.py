"""
Contributions:
Contributors:

Original copyright (c) 2015-2016, Uday Agrawal, Adewole Oyalowo, Asaad Lab under MIT License. See full license and associated
project at < https://bitbucket.org/asaadneurolab/pymind/ > .
"""

from __future__ import division

import datetime
import time
import numpy as np
from IntellivueDecoder import IntellivueDecoder
import logging


class IntellivueDistiller(object):
    """
    This class works with decoded messages yielded by the IntellivueDecoder and
    extracts key vitals data into timestamped dictionaries.
    """

    def __init__(self):

        # Initialize Intellivue because has data types
        self.Intellivue = IntellivueDecoder()

        # Initialize data reading/writing variables
        self.initialTime = str(datetime.datetime.now())
        self.initialTimeDateTime = datetime.datetime.now()
        self.relativeInitialTime = 0

        # Creates file to store data (without overwriting previous data)
        # self.patientFolder = patientDirectory
        # self.VitalsNumericsAlarmsDataFile = self.patientFolder + '/VitalsData' + '_' + time.strftime('%m.%d.%Y') + '_' + time.strftime('%H.%M.%S') + '.json'

        # Dictionary to be dumped into json file
        self.VitalsWaveData = {}
        self.VitalsWaveInfo = {}
        self.VitalsNumericsInfo = {}
        self.VitalsNumericsAlarmsData = {}
        self.VitalsNumericsAlarmsData['Info'] = {}
        self.fileTime = 60*60

    # Stores initial time, which all following times are based off
    def saveInitialTime(self, decodedInitialTime, relativeDecodedInitialTime):

        self.initialTime = '{0}/{1}/{2}{3}, {4}:{5}:{6}'.format(decodedInitialTime['month'],decodedInitialTime['day'], decodedInitialTime['century'], decodedInitialTime['year'], decodedInitialTime['hour'], decodedInitialTime['minute'], decodedInitialTime['second'])
        self.VitalsNumericsAlarmsData['Info']['InitialTime'] = self.initialTime
        self.relativeInitialTime = relativeDecodedInitialTime
        self.initialTimeDateTime = datetime.datetime(decodedInitialTime['year']+decodedInitialTime['century']*100,decodedInitialTime['month'],decodedInitialTime['day'], decodedInitialTime['hour'], decodedInitialTime['minute'], decodedInitialTime['second'])

    def timestamp(self, decoded_message):
        # Initialize timestamp
        return self.initialTimeDateTime + datetime.timedelta(seconds=float((decoded_message['PollMdibDataReplyExt']['RelativeTime'] - self.relativeInitialTime)/8192))

    def strftime(self, ts):
        return ts.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

    def refine(self, decoded_message):
        # Handle a decoded message

        m = None # Secondary message decoding to "important stuff"
        if decoded_message['PollMdibDataReplyExt']['Type']['OIDType'] == 'NOM_MOC_VMO_METRIC_SA_RT':
            m = self.refine_wave_message(decoded_message)
        elif decoded_message['PollMdibDataReplyExt']['Type']['OIDType'] == 'NOM_MOC_VMO_METRIC_NU':
            m = self.refine_numerics_message(decoded_message)
        elif decoded_message['PollMdibDataReplyExt']['Type']['OIDType'] == 'NOM_MOC_VMO_AL_MON':
            m = self.refine_alarms_message(decoded_message)
        else:
            logging.info('No refinement handler.')

        # if m:
        #     logging.debug(m)

        return m


    # Save the wave data
    def refine_wave_message(self, decoded_message):
        """
        Saves data into numpy arrays with timestamps and writes to file
        """

        temp_times = np.zeros(1)
        ret = {}

        # Go through all of the Single Context Polls
        for singleContextPolls in decoded_message['PollMdibDataReplyExt']['PollInfoList']:

            # Make sure that they are dicts (ie not length, count), and they aren't empty
            if type(decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]) == dict and decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info']['length'] > 0:

                # Go through all of the Observation Polls (each data modality stored in separate observation poll)
                for observationPolls in decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info']:

                    # Make sure that they are dicts (ie not length, count)
                    if type(decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]) == dict:

                        my_data = decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']

                        # If the message contains data regarding value conversion, units, and sampling freq, and is a compound value, store as defined below:
                        if 'NOM_ATTR_SCALE_SPECN_I16' in my_data and 'NOM_ATTR_SA_CMPD_VAL_OBS' in my_data:

                            # Iterate through all the different data types (ie scada) in the compound value
                            for scada in decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_SA_CMPD_VAL_OBS']['AttributeValue']['SaObsValueCmp']:

                                # Make sure that they are dicts (ie not length, count)
                                if type(decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_SA_CMPD_VAL_OBS']['AttributeValue']['SaObsValueCmp'][scada]) == dict:

                                    # Store label (in case of compound value, simply the scada label)
                                    label = decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_SA_CMPD_VAL_OBS']['AttributeValue']['SaObsValueCmp'][scada]['SaObsValue']['SCADAType']

                                    # If this label isn't in self.VitalsWaveInfo, then initialize values for it
                                    if label not in self.VitalsWaveInfo:

                                        # Stores basic attributes of each data type
                                        self.VitalsWaveInfo[label] = {}

                                        # Sampling frequency

                                        logging.debug(decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType'])

                                        fs = int(8192/decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_TIME_PD_SAMP']['AttributeValue']['RelativeTime'])

                                        # Initialize numpy array for timestamps and data (length is fs*desired file time - time already elapsed)
                                        self.VitalsWaveData[label] = np.zeros((2,fs*self.fileTime - fs*int((decoded_message['PollMdibDataReplyExt']['RelativeTime'] - self.relativeInitialTime)/8192)), dtype = 'float32')

                                        # # Set numpy data array in HDF5 file
                                        # self.VitalsGroup.create_dataset(label, data = self.VitalsNumericsAlarmsData[label])

                                        # Initialize index (to keep track of index of data values)
                                        self.VitalsWaveInfo[label]['Index'] = 0

                                        # Initialize linear conversion values (ie y = mx + b)
                                        self.VitalsWaveInfo[label]['ValueConversion'] = self.convertValues(decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_SCALE_SPECN_I16']['AttributeValue']['ScaleRangeSpec16'])

                                        # Initialize units
                                        self.VitalsWaveInfo[label]['Units'] = decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_UNIT_CODE']['AttributeValue']['UNITType']
                                        #self.VitalsGroup[label].attrs['Units'] = decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_UNIT_CODE']['AttributeValue']['UNITType']

                                        # Initialize sampling frequency
                                        # self.VitalsGroup[label].attrs['SamplingFreq'] = fs
                                        self.VitalsWaveInfo[label]['SamplingFreq'] = fs

                                        # Inititialize Handle (to help uniquely identify scada)
                                        self.VitalsWaveInfo[label]['Handle'] = decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_ID_HANDLE']['AttributeValue']['Handle']

                        # If the message contains data regarding value conversion, units, and sampling freq, and is not compound, store it as defined below:
                        elif 'NOM_ATTR_SCALE_SPECN_I16' in decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']:

                            # Store label (in case of normal value, is the TextId)
                            label = decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_ID_LABEL']['AttributeValue']['TextId']

                            # If this label isn't in self.VitalsWaveInfo, then initialize values for it
                            if label not in self.VitalsWaveInfo:

                                # Stores basic attributes of each data type
                                self.VitalsWaveInfo[label] = {}

                                # Sampling frequency
                                fs = int(8192/decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_TIME_PD_SAMP']['AttributeValue']['RelativeTime'])

                                # Initialize numpy array - 1hr
                                self.VitalsWaveData[label] = np.zeros((2,fs*self.fileTime - fs*int((decoded_message['PollMdibDataReplyExt']['RelativeTime'] - self.relativeInitialTime)/8192)), dtype = 'float32')

                                # # Set numpy array in HDF5 file
                                # self.VitalsGroup.create_dataset(label, data = self.VitalsNumericsAlarmsData[label])

                                # Initialize index
                                self.VitalsWaveInfo[label]['Index'] = 0

                                # Initialize linear conversion values (ie y = mx + b)
                                self.VitalsWaveInfo[label]['ValueConversion'] = self.convertValues(decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_SCALE_SPECN_I16']['AttributeValue']['ScaleRangeSpec16'])

                                # Initialize units
                                self.VitalsWaveInfo[label]['Units'] = decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_UNIT_CODE']['AttributeValue']['UNITType']
                                # self.VitalsGroup[label].attrs['Units'] = decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_UNIT_CODE']['AttributeValue']['UNITType']

                                # Initialize sampling frequency
                                #self.VitalsGroup[label].attrs['SamplingFreq'] = fs
                                self.VitalsWaveInfo[label]['SamplingFreq'] = fs

                                # Inititialize Handle (to help uniquely identify data type)
                                self.VitalsWaveInfo[label]['Handle'] = decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_ID_HANDLE']['AttributeValue']['Handle']

                        # If the message contains data, save it
                        if 'NOM_ATTR_SA_VAL_OBS' in decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']:

                            # Determine label based on SCADA Type and Handle
                            for dataTypes in self.VitalsWaveInfo:

                                # If label identified (ie handle and SCADA type match Text ID)...
                                if self.VitalsWaveInfo[dataTypes]['Handle'] == decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['Handle'] and decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_SA_VAL_OBS']['AttributeValue']['SaObsValue']['SCADAType'] in self.Intellivue.DataKeys['PhysioKeys'][dataTypes]:

                                    label = dataTypes

                                    # Create temporary time and data variables
                                    temp_array = np.array(decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_SA_VAL_OBS']['AttributeValue']['SaObsValue']['PhysioValue']['VariableData']['value'])
                                    temp_times = np.linspace((decoded_message['PollMdibDataReplyExt']['RelativeTime'] - self.relativeInitialTime)/8192, (decoded_message['PollMdibDataReplyExt']['RelativeTime'] - self.relativeInitialTime)/8192 + temp_array.size/self.VitalsWaveInfo[label]['SamplingFreq'], temp_array.size)

                                    #*self.checkPatientFile(self.VitalsWaveInfo[label], temp_array.size, self.VitalsNumericsAlarmsData[label].shape[1])

                                    # Save on RAM in python dict
                                    # self.VitalsWaveData[label][:,self.VitalsWaveInfo[label]['Index']:self.VitalsWaveInfo[label]['Index']+temp_array.size] = [temp_times,temp_array*self.VitalsWaveInfo[label]['ValueConversion'][0] + self.VitalsWaveInfo[label]['ValueConversion'][1]]

                                    # Save data to HDF5 File
                                    # self.VitalsGroup[label][:,self.VitalsWaveInfo[label]['Index']:self.VitalsWaveInfo[label]['Index']+temp_array.size] = [temp_times,temp_array*self.VitalsWaveInfo[label]['ValueConversion'][0] + self.VitalsWaveInfo[label]['ValueConversion'][1]]

                                    # Add to index
                                    # self.VitalsWaveInfo[label]['Index'] += temp_array.size

                                    ret[label] = temp_array*self.VitalsWaveInfo[label]['ValueConversion'][0] + self.VitalsWaveInfo[label]['ValueConversion'][1]

                        # If the message contains compound data, save it
                        if 'NOM_ATTR_SA_CMPD_VAL_OBS' in decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']:

                            # Determine label based on SCADA Type and Handle
                            for dataTypes in self.VitalsWaveInfo:

                                # If handle matches...
                                if self.VitalsWaveInfo[dataTypes]['Handle'] == decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['Handle']:

                                    # iterate through all the compound values
                                    for saObsValues in decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_SA_CMPD_VAL_OBS']['AttributeValue']['SaObsValueCmp']:

                                        # iterate through dictionaries only (ie not count, length)
                                        if type(decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_SA_CMPD_VAL_OBS']['AttributeValue']['SaObsValueCmp'][saObsValues]) == dict:

                                            # Make sure scada type matches data type
                                            if decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_SA_CMPD_VAL_OBS']['AttributeValue']['SaObsValueCmp'][saObsValues]['SaObsValue']['SCADAType'] == dataTypes:

                                                # Set label appropriately
                                                label = dataTypes

                                                # Create temporary time and data variables
                                                temp_array = np.array(decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_SA_CMPD_VAL_OBS']['AttributeValue']['SaObsValueCmp'][saObsValues]['SaObsValue']['PhysioValue']['VariableData']['value']).T
                                                temp_times = np.linspace((decoded_message['PollMdibDataReplyExt']['RelativeTime'] - self.relativeInitialTime)/8192, (decoded_message['PollMdibDataReplyExt']['RelativeTime'] - self.relativeInitialTime)/8192 + temp_array.size/self.VitalsWaveInfo[label]['SamplingFreq'], temp_array.size).T

                                                #*self.checkPatientFile(self.VitalsWaveInfo[label], temp_array.size, self.VitalsNumericsAlarmsData[label].shape[1])

                                                # Save on RAM in python dict
#                                                self.VitalsWaveData[label][:,self.VitalsWaveInfo[label]['Index']:self.VitalsWaveInfo[label]['Index']+temp_array.size] = [temp_times,temp_array*self.VitalsWaveInfo[label]['ValueConversion'][0] + self.VitalsWaveInfo[label]['ValueConversion'][1]]

                                                # Save data to HDF5 File
                                                # self.VitalsGroup[label][:,self.VitalsWaveInfo[label]['Index']:self.VitalsWaveInfo[label]['Index']+temp_array.size] = [temp_times,temp_array*self.VitalsWaveInfo[label]['ValueConversion'][0] + self.VitalsWaveInfo[label]['ValueConversion'][1]]

                                                # Add to index
#                                                self.VitalsWaveInfo[label]['Index'] += temp_array.size

                                                ret[label] = temp_array*self.VitalsWaveInfo[label]['ValueConversion'][0] + self.VitalsWaveInfo[label]['ValueConversion'][1]

        ret['timestamp'] = self.timestamp(decoded_message)

        if temp_times.any():
            # about 25 samples/250ms, so back up 10ms
            ret['end_time'] = ret['timestamp'] + datetime.timedelta(milliseconds=250-10)

        if len(ret) < 2:
            return None

        return ret

    # Save the numeric data
    def refine_numerics_message(self, decoded_message):
        """
        Saves data into numpy arrays with timestamps and writes to file
        """

        currentTime = None

        # Go through all of the Single Context Polls
        for singleContextPolls in decoded_message['PollMdibDataReplyExt']['PollInfoList']:

            # Make sure that they are dicts (ie not length, count), and they aren't empty
            if type(decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]) == dict and decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info']['length'] > 0:

                # Go through all of the Observation Polls
                for observationPolls in decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info']:

                    # Make sure that they are dicts (ie not length, count)
                    if type(decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]) == dict:

                        # If the message contains the TextId, append it to self.Vitals['Info']
                        if 'NOM_ATTR_ID_LABEL' in decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']:

                            # TextID
                            label = decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_ID_LABEL']['AttributeValue']['TextId']

                            # Check to make sure label isn't already in self.Vitals['Info']
                            if label not in self.VitalsNumericsAlarmsData['Info']:

                                # Initialize to store attributes of data type
                                self.VitalsNumericsAlarmsData['Info'][label] = {}

                                # Inititalize Index
                                # self.VitalsNumericsInfo[label]['Index'] = 0
                        else:
                            label = 'noLabel'

                        # If there is data, store it
                        if 'NOM_ATTR_NU_VAL_OBS' in decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']:

                            # Unique label
                            # label = decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_ID_LABEL']['AttributeValue']['TextId']

                            # If first time storing data, initialize attributes
                            if label not in self.VitalsNumericsAlarmsData['Info']:

                                # Fs = 1 Hz
                                #fs = 1
                                #self.VitalsNumericsInfo[label]['SamplingFreq'] = fs

                                # Initialize numpy array - 1 hr chunk
                                # self.VitalsNumericsAlarmsData[label] = np.zeros((2,fs*self.fileTime), dtype = 'float32')

                                # Store data in HDF5 file
                                # self.VitalsNumericsGroup.create_dataset(label, data = self.VitalsNumericsData[label])

                                # Initialize units
                                self.VitalsNumericsAlarmsData['Info'][label] = {}
                                self.VitalsNumericsAlarmsData['Info'][label]['Units'] = decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_NU_VAL_OBS']['AttributeValue']['NuObsValue']['UNITType']
                                # self.VitalsNumericsGroup[label].attrs['Units'] = decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_NU_VAL_OBS']['AttributeValue']['NuObsValue']['UNITType']

                            # If attributes confirmed, then can start storing
                            else:
                                # temporary time values
                                temp_time = (decoded_message['PollMdibDataReplyExt']['RelativeTime'] - self.relativeInitialTime)/8192

                                # Initialize timestamp
                                currentTime = self.initialTimeDateTime + datetime.timedelta(seconds = int((decoded_message['PollMdibDataReplyExt']['RelativeTime'] - self.relativeInitialTime)/8192))
                                currentTime = str(currentTime.time())

                                # temporary values
                                temp_value = decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_NU_VAL_OBS']['AttributeValue']['NuObsValue']['FLOATType']

                                # If its a string, then don't store it
                                if type(temp_value) != str:

                                    #self.checkPatientFile(self.Vitals['Info'][label], 1, self.VitalsNumericsData[label].shape[1])

                                    # Store data
                                    if currentTime in self.VitalsNumericsAlarmsData:
                                        self.VitalsNumericsAlarmsData[currentTime][label] = temp_value
                                    else:
                                        self.VitalsNumericsAlarmsData[currentTime] = {}
                                        self.VitalsNumericsAlarmsData[currentTime]['timestamp'] = temp_time
                                        self.VitalsNumericsAlarmsData[currentTime][label] = temp_value

                        # If compound data type...
                        if 'NOM_ATTR_NU_CMPD_VAL_OBS' in decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']:

                            # NOT unique label (each value within the compound value has it)
                            #label = decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_ID_LABEL']['AttributeValue']['TextId']

                            # If the label has been created,
                            if label in self.VitalsNumericsAlarmsData['Info']:

                                # Store temporary time values
                                temp_time = (decoded_message['PollMdibDataReplyExt']['RelativeTime'] - self.relativeInitialTime)/8192

                                # Initialize timestamp
                                currentTime = self.initialTimeDateTime + datetime.timedelta(seconds = int((decoded_message['PollMdibDataReplyExt']['RelativeTime'] - self.relativeInitialTime)/8192))
                                currentTime = str(currentTime.time())

                                # For each individual value within the compound
                                for scada in decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_NU_CMPD_VAL_OBS']['AttributeValue']['NuObsValCmp']:

                                    # Make sure to iterate through dicts (ie not count, length)
                                    if type(decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_NU_CMPD_VAL_OBS']['AttributeValue']['NuObsValCmp'][scada]) == dict:

                                        # Create unique scada_label which has both TextID and scada_type
                                        scada_type = decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_NU_CMPD_VAL_OBS']['AttributeValue']['NuObsValCmp'][scada]['NuObsValue']['SCADAType']
                                        scada_label = label + '_' + scada_type.split('_')[-1]

                                        # If no data written yet, initialize attributes
                                        if scada_label not in self.VitalsNumericsAlarmsData['Info']:

                                            # Initialize attribute info
                                            self.VitalsNumericsAlarmsData['Info'][scada_label] = {}

                                            # Sampling Frequency = 1 Hz
                                            #fs = 1
                                            #self.Vitals['Info'][scada_label]['SamplingFreq'] = fs

                                            # Initialize numpy array
                                            #self.VitalsNumericsData[scada_label] = np.zeros((2,fs*self.fileTime), dtype = 'float32')

                                            # Store numpy array in HDF5
                                            #self.VitalsNumericsGroup.create_dataset(scada_label, data = self.VitalsNumericsData[scada_label])

                                            # Initialize units
                                            self.VitalsNumericsAlarmsData['Info'][scada_label]['Units'] = decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_NU_CMPD_VAL_OBS']['AttributeValue']['NuObsValCmp'][scada]['NuObsValue']['UNITType']
                                            #self.VitalsNumericsGroup[scada_label].attrs['Units'] = decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_NU_CMPD_VAL_OBS']['AttributeValue']['NuObsValCmp'][scada]['NuObsValue']['UNITType']

                                            # Initialize index
                                            #self.Vitals['Info'][scada_label]['Index'] = 0

                                        # If everything initialized, start writing data
                                        else:
                                            # temporary values
                                            temp_value = decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_NU_CMPD_VAL_OBS']['AttributeValue']['NuObsValCmp'][scada]['NuObsValue']['FLOATType']

                                            # If its a string, then don't store it
                                            if type(temp_value) != str:

                                                # self.checkPatientFile(self.Vitals['Info'][scada_label], 1, self.VitalsNumericsData[scada_label].shape[1])

                                                # save data
                                                # self.VitalsNumericsData[scada_label][:,self.Vitals['Info'][scada_label]['Index']] = [temp_time,temp_value]
                                                # self.VitalsNumericsGroup[scada_label][:,self.Vitals['Info'][scada_label]['Index']] = [temp_time,temp_value]

                                                # Store data
                                                if currentTime in self.VitalsNumericsAlarmsData:
                                                    self.VitalsNumericsAlarmsData[currentTime][label] = temp_value
                                                else:
                                                    self.VitalsNumericsAlarmsData[currentTime] = {}
                                                    self.VitalsNumericsAlarmsData[currentTime]['timestamp'] = temp_time
                                                    self.VitalsNumericsAlarmsData[currentTime][label] = temp_value

                                            # add to index
                                            #self.Vitals['Info'][scada_label]['Index'] += 1

        ret = {'timestamp': self.timestamp(decoded_message)}

        if currentTime:
            for key, value in self.VitalsNumericsAlarmsData[currentTime].iteritems():
                if key != 'timestamp':
                    ret[key] = value
            # This possibly fixes growing forever problem
            del self.VitalsNumericsAlarmsData[currentTime]

        if len(ret) < 2:
            return None

        return ret

    # Save the alarm data
    def refine_alarms_message(self, decoded_message):
        """
        Saves data into numpy arrays with timestamps and writes to file
        """

        # Initialize return values
        currentTime = None

        # Go through all of the Single Context Polls
        for singleContextPolls in decoded_message['PollMdibDataReplyExt']['PollInfoList']:

            # Make sure that they are dicts (ie not length, count), and they aren't empty
            if type(decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]) == dict and decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info']['length'] > 0:

                # Go through all of the Observation Polls (each data modality stored in separate observation poll)
                for observationPolls in decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info']:

                    # Make sure that they are dicts (ie not length, count)
                    if type(decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]) == dict:

                        # Initialize timestamp
                        currentTime = self.initialTimeDateTime + datetime.timedelta(seconds = int((decoded_message['PollMdibDataReplyExt']['RelativeTime'] - self.relativeInitialTime)/8192))
                        currentTime = str(currentTime.time())

                        # Initialize currentTime
                        if currentTime not in self.VitalsNumericsAlarmsData:
                            self.VitalsNumericsAlarmsData[currentTime] = {}

                        # If the message active patient alarm data, store it
                        if 'NOM_ATTR_AL_MON_P_AL_LIST' in decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']:

                            i = 0

                            # Iterate through all the different data types (ie scada) in the compound value
                            for devAlarm in decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_AL_MON_P_AL_LIST']['AttributeValue']['DevAlarmList']:

                                # Make sure that they are dicts (ie not length, count)
                                if type(decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_AL_MON_P_AL_LIST']['AttributeValue']['DevAlarmList'][devAlarm]) == dict:

                                    self.VitalsNumericsAlarmsData[currentTime]['Alarm_P_' + str(i)] = {}
                                    self.VitalsNumericsAlarmsData[currentTime]['Alarm_P_' + str(i)] ['timestamp'] = currentTime
                                    self.VitalsNumericsAlarmsData[currentTime]['Alarm_P_' + str(i)]['code'] = decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]\
                                    ['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_AL_MON_P_AL_LIST']['AttributeValue']['DevAlarmList'][devAlarm]['DevAlarmEntry']['al_code']#.split('NOM_EVT_')[1]
                                    self.VitalsNumericsAlarmsData[currentTime]['Alarm_P_' + str(i)]['source'] = decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]\
                                    ['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_AL_MON_P_AL_LIST']['AttributeValue']['DevAlarmList'][devAlarm]['DevAlarmEntry']['al_source']#.split('NOM_')[1]
                                    self.VitalsNumericsAlarmsData[currentTime]['Alarm_P_' + str(i)]['alarmType'] = decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]\
                                    ['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_AL_MON_P_AL_LIST']['AttributeValue']['DevAlarmList'][devAlarm]['DevAlarmEntry']['AlertType']#.split('_')[0] + '_P'
                                    self.VitalsNumericsAlarmsData[currentTime]['Alarm_P_' + str(i)]['state'] = decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]\
                                    ['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_AL_MON_P_AL_LIST']['AttributeValue']['DevAlarmList'][devAlarm]['DevAlarmEntry']['AlertState']#.split('AL_')[1]
                                    self.VitalsNumericsAlarmsData[currentTime]['Alarm_P_' + str(i)]['string'] = decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]\
                                    ['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_AL_MON_P_AL_LIST']['AttributeValue']['DevAlarmList'][devAlarm]['DevAlarmEntry']['StrAlMonInfo']['String']['value']
                                    i += 1

                        # If the patient contains active technical alarms, store it
                        if 'NOM_ATTR_AL_MON_T_AL_LIST' in decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']:

                            i = 0

                            # Iterate through all the different data types (ie scada) in the compound value
                            for devAlarm in decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_AL_MON_T_AL_LIST']['AttributeValue']['DevAlarmList']:

                                # Make sure that they are dicts (ie not length, count)
                                if type(decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_AL_MON_T_AL_LIST']['AttributeValue']['DevAlarmList'][devAlarm]) == dict:

                                    self.VitalsNumericsAlarmsData[currentTime]['Alarm_T_' + str(i)] = {}
                                    self.VitalsNumericsAlarmsData[currentTime]['Alarm_T_' + str(i)] ['timestamp'] = currentTime
                                    self.VitalsNumericsAlarmsData[currentTime]['Alarm_T_' + str(i)]['code'] = decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]\
                                    ['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_AL_MON_T_AL_LIST']['AttributeValue']['DevAlarmList'][devAlarm]['DevAlarmEntry']['al_code']#.split('NOM_EVT_')[1]
                                    self.VitalsNumericsAlarmsData[currentTime]['Alarm_T_' + str(i)]['source'] = decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]\
                                    ['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_AL_MON_T_AL_LIST']['AttributeValue']['DevAlarmList'][devAlarm]['DevAlarmEntry']['al_source']#.split('NOM_')[1]
                                    self.VitalsNumericsAlarmsData[currentTime]['Alarm_T_' + str(i)]['alarmType'] = decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]\
                                    ['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_AL_MON_T_AL_LIST']['AttributeValue']['DevAlarmList'][devAlarm]['DevAlarmEntry']['AlertType']#.split('_')[0] + '_T'
                                    self.VitalsNumericsAlarmsData[currentTime]['Alarm_T_' + str(i)]['state'] = decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]\
                                    ['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_AL_MON_T_AL_LIST']['AttributeValue']['DevAlarmList'][devAlarm]['DevAlarmEntry']['AlertState']#.split('AL_')[1]
                                    self.VitalsNumericsAlarmsData[currentTime]['Alarm_T_' + str(i)]['string'] = decoded_message['PollMdibDataReplyExt']['PollInfoList'][singleContextPolls]['SingleContextPoll']['poll_info'][observationPolls]\
                                    ['ObservationPoll']['AttributeList']['AVAType']['NOM_ATTR_AL_MON_T_AL_LIST']['AttributeValue']['DevAlarmList'][devAlarm]['DevAlarmEntry']['StrAlMonInfo']['String']['value']
                                    i += 1

                        # # Append to file _if_ you are keeping a text file
                        # with open(self.VitalsNumericsAlarmsDataFile, 'a+') as outfile:
                        #     json.dump(self.VitalsNumericsAlarmsData, outfile)

        ret = {'timestamp': self.timestamp(decoded_message),
               'alarms': {} }

        if currentTime:
            for key, value in self.VitalsNumericsAlarmsData[currentTime].iteritems():
                if key.startswith('Alarm'):
                    ret['alarms'][key] = {'source': value['source'],
                                          'code': value['code'],
                                          'state': value['state'],
                                          'string': value['string'],
                                          'type': value['alarmType']}

            # This possibly fixes growing forever problem
            del self.VitalsNumericsAlarmsData[currentTime]

        if not ret['alarms']:
            return None

        return ret

    # Reads in dict specified by ScaleRangeSpec16, returns a and b of y = ax + b
    def convertValues(self, ScaleRangeSpec16):
        """
        Converts values to physiologcal range using y = ax + b
        returns a, b so that values can be quickly converted
        """
        # Difference py3 vs py27, want to check for unicode not str
        if isinstance(ScaleRangeSpec16['upper_absolute_value']['FLOATType'], unicode):
            return 1, 0

        else:
            x_range = ScaleRangeSpec16['upper_scaled_value'] - ScaleRangeSpec16['lower_scaled_value']
            y_range = ScaleRangeSpec16['upper_absolute_value']['FLOATType'] - ScaleRangeSpec16['lower_absolute_value']['FLOATType']
            a = y_range/x_range
            b = ScaleRangeSpec16['lower_absolute_value']['FLOATType'] - a * ScaleRangeSpec16['lower_scaled_value']

            return a, b
