"""
@author: uagrawal last update: 2/29/16
@fixes: backport to 2.7 by derek

Requires pyserial (for RS232)
"""

# @leo/@uday/@derek
# TODO: How do we want to smooth the QoS values

from __future__ import unicode_literals

import logging
import time
from IntellivueProtocol.IntellivueDecoder import IntellivueDecoder
from IntellivueProtocol.RS232 import RS232
from IntellivueProtocol.IntellivueDistiller import IntellivueDistiller
from TelemetryStream import *
from QualityOfSignal import QualityOfSignal as QoS

__description__ = "PERSEUS telemetry stream listener for Philips Invellivue devices with serial connections"
__version_info__ = ('0', '7', '0')
__version__ = '.'.join(__version_info__)

# Wrapper for UCSF QoS code
def qos(*args, **kwargs):
    my_qos = QoS()
    history = kwargs.get('sampled_data')
    if history:
        res = my_qos.isPPGGoodQuality(history.get('Pleth').get('samples').y,
                                      history.get('Pleth').get('samples').t,
                                      32 * 4)
        return {'qos': res}
    else:
        return -1

class PhilipsTelemetryStream(TelemetryStream):
    """
    This class utilizes the data structures defined in IntellivueDecoder and
    the functions to communicate with the monitor via RS232.
    """

    # def __init__(self, serialPort, patientDirectory, selectedDataTypes):
    def __init__(self, *args, **kwargs):
        super(PhilipsTelemetryStream, self).__init__(*args, **kwargs)

        self.logger.name = 'PhilipsTelemetry'

        serialPort = kwargs.get('port')
        selectedDataTypes = kwargs.get('values')[::2]  # These come in as value, freq pairs; just need names

        self.port = serialPort
        self.rs232 = None  # This will be the socket object

        # Initialize Intellivue Decoder and Distiller
        self.decoder = IntellivueDecoder()
        self.distiller = IntellivueDistiller()

        # Initialize variables to keep track of time, and values to collect

        # Note: The listener automatically shuts down after this many seconds
        self.dataCollectionTime = 60 * 60 * 12  # seconds
        self.dataCollection = {'RelativeTime': self.dataCollectionTime * 8192}
        self.KeepAliveTime = 0
        self.messageTimes = []
        self.desiredWaveParams = {'TextIdLabel': selectedDataTypes}
        self.initialTime = 0
        self.relativeInitialTime = 0

        #  Initialize Messages
        self.AssociationRequest = self.decoder.writeData('AssociationRequest')
        self.AssociationAbort = self.decoder.writeData('AssociationAbort')
        self.ConnectIndication = {}
        self.AssociationResponse = ''
        self.MDSCreateEvent = {}
        self.MDSParameters = {}
        self.MDSCreateEventResult = ''
        self.MDSSetPriorityListWave = self.decoder.writeData('MDSSetPriorityListWAVE', self.desiredWaveParams)
        self.MDSSetPriorityListNumeric = ''
        self.MDSSetPriorityListResultWave = {}
        self.MDSSetPriorityListResultNumeric = {}
        self.MDSGetPriorityList = self.decoder.writeData('MDSGetPriorityList')
        self.MDSGetPriorityListResult = {}
        self.ReleaseRequest = self.decoder.writeData('ReleaseRequest')
        self.MDSExtendedPollActionNumeric = self.decoder.writeData('MDSExtendedPollActionNUMERIC',
                                                                   self.dataCollection)
        self.MDSExtendedPollActionWave = self.decoder.writeData('MDSExtendedPollActionWAVE', self.dataCollection)
        self.MDSExtendedPollActionAlarm = self.decoder.writeData('MDSExtendedPollActionALARM', self.dataCollection)
        self.KeepAliveMessage = self.decoder.writeData('MDSSinglePollAction')

        # Boolean to keep track of whether data should still be polled
        self.data_flow = False

        self.last_read_time = time.time()
        self.timeout = 5

        self.last_keep_alive = time.time()

    def initiate_association(self, blocking=False):

        # There are 2 phases to the association, the request/response and the creation event
        # If any phase fails, throw an error
        def request_assocation():
            self.rs232.send(self.AssociationRequest)
            self.logger.info('Sent Association Request...')

        def receive_association_response():
            association_message = self.rs232.receive()

            # Could handle no message in getMessageType (hrm)
            if not association_message:
                logging.warn('No association received')
                raise IOError

            message_type = self.decoder.getMessageType(association_message)
            self.logger.info('Received ' + message_type + '.')

            # If we got an AssociationResponse we can return
            if message_type == 'AssociationResponse':
                return association_message

            # Fail and reset!
            elif message_type == 'AssociationAbort' or message_type == 'ReleaseRequest' or message_type == 'Unknown' or message_type == 'TimeoutError':
                self.close()
                raise IOError

            # If data still coming in from a previous connection or no data is coming in, abort/release
            elif message_type == 'MDSExtendedPollActionResult' or message_type == 'LinkedMDSExtendedPollActionResult':
                self.rs232.send(self.AssociationAbort)
                self.rs232.send(self.ReleaseRequest)
                self.close()
                raise IOError

            else:
                raise IOError

        def receive_event_creation(association_message):
            # This is the create event message now
            event_message = self.rs232.receive()

            message_type = self.decoder.getMessageType(event_message)
            logging.info('Received ' + message_type + '.')

            # ie, we got the create event response
            if message_type == 'MDSCreateEvent':
                self.AssociationResponse = self.decoder.readData(association_message)

                logging.debug("Association response: {0}".format(self.AssociationResponse))

                self.KeepAliveTime = \
                    self.AssociationResponse['AssocRespUserData']['MDSEUserInfoStd']['supported_aprofiles'][
                        'AttributeList']['AVAType']['NOM_POLL_PROFILE_SUPPORT']['AttributeValue']['PollProfileSupport'][
                        'min_poll_period']['RelativeTime'] / 8192
                self.MDSCreateEvent, self.MDSParameters = self.decoder.readData(event_message)

                # Store the absolute time marker that everything else will reference
                self.initialTime = self.MDSCreateEvent['MDSCreateInfo']['MDSAttributeList']['AttributeList']['AVAType'][
                    'NOM_ATTR_TIME_ABS']['AttributeValue']['AbsoluteTime']
                self.relativeInitialTime = \
                    self.MDSCreateEvent['MDSCreateInfo']['MDSAttributeList']['AttributeList']['AVAType'][
                        'NOM_ATTR_TIME_REL']['AttributeValue']['RelativeTime']
                if 'saveInitialTime' in dir(self.distiller):
                    self.distiller.saveInitialTime(self.initialTime, self.relativeInitialTime)

                # Send MDS Create Event Result
                self.MDSCreateEventResult = self.decoder.writeData('MDSCreateEventResult', self.MDSParameters)
                self.rs232.send(self.MDSCreateEventResult)
                logging.info('Sent MDS Create Event Result...')
                return
            else:
                # We didn't get a properly formed create event message!
                self.logger.error('Bad handshake!')
                self.close()
                raise IOError

        # Keep trying until success
        if blocking:
            while 1:
                try:
                    request_assocation()
                    m = receive_association_response()
                    receive_event_creation(m)
                    break
                except IOError:
                    time.sleep(2.0)
                    continue

        else:
            request_assocation()
            m = receive_association_response()
            receive_event_creation(m)


    # Set Priority Lists (ie what data should be polled)
    def set_priority_lists(self):
        """
        Sends MDSSetPriorityListWave
        Receives the confirmation
        """
        # Writes priority lists
        self.MDSSetPriorityListWave = self.decoder.writeData('MDSSetPriorityListWAVE', self.desiredWaveParams)

        # Send priority lists
        self.rs232.send(self.MDSSetPriorityListWave)
        logging.info('Sent MDS Set Priority List Wave...')

        # Read in confirmation of changes
        no_confirmation = True
        while (no_confirmation):

            message = self.rs232.receive()
            if not message:
                logging.warn('No priority list msg received!')
                break

            message_type = self.decoder.getMessageType(message)

            # If Priority List Result, store message, advance script
            if message_type == 'MDSSetPriorityListResult':
                PriorityListResult = self.decoder.readData(message)

                # If there are wave data objects, create a group for them
                if 'NOM_ATTR_POLL_RTSA_PRIO_LIST' in PriorityListResult['SetResult']['AttributeList']['AVAType']:
                    self.MDSSetPriorityListResultWave = PriorityListResult
                    logging.info('Received MDS Set Priority List Result Wave.')

                no_confirmation = False

            # If MDSCreateEvent, then state failure to confirm
            elif message_type == 'MDSCreateEvent':
                no_confirmation = False
                logging.warn('Failed to confirm setting of priority lists.')

    def submit_keep_alive(self):
        self.rs232.send(self.KeepAliveMessage)
        self.last_keep_alive = time.time()
        logging.info('Sent Keep Alive Message...')

    # Extended retrieve data from monitor; this is unused but preserved from original code
    def extended_poll(self):
        """
        Sends Extended Poll Requests for Numeric and Wave Data
        """

        # Need to poll numerics to keep machine alive, but don't save if not
        # specified
        self.rs232.send(self.MDSExtendedPollActionNumeric)
        self.rs232.send(self.MDSExtendedPollActionWave)
        self.rs232.send(self.MDSExtendedPollActionAlarm)
        logging.info('Sent MDS Extended Poll Action for Numerics...')
        logging.info('Sent MDS Extended Poll Action for Waves...')
        logging.info('Sent MDS Extended Poll Action for Alarms...')

        keep_alive_messages = 1
        self.data_flow = True
        while (self.data_flow):

            message = self.rs232.receive()
            if not message:
                logging.warn('No data msg received!')
                self.data_flow = False
                break

            message_type = self.decoder.getMessageType(message)

            if message_type == 'AssociationAbort':
                logging.info('Data Collection Terminated.')
                self.rs232.close()
                self.data_flow = False

            elif message_type == 'RemoteOperationError':
                logging.error('Error Message')

            elif message_type == 'MDSSinglePollActionResult':
                # logging.info('Message Kept Alive!')
                pass

            elif message_type == 'MDSExtendedPollActionResult' or message_type == 'LinkedMDSExtendedPollActionResult':

                decoded_message = self.decoder.readData(message)
                # This will send to splunk/file whatever
                # self.logger.info(decoded_message)
                #logging.info("Decoded message: {0}".format(decoded_message))

                m = None # Secondary message decoding to "important stuff"

                if decoded_message['PollMdibDataReplyExt']['Type']['OIDType'] == 'NOM_MOC_VMO_METRIC_SA_RT':
                    m = self.distiller.refine_wave_message(decoded_message)

                    # To store and output message times (in order to log when to send Keep Alive Messages)
                    if decoded_message['ROapdus']['length'] > 100:
                        if 'RelativeTime' in decoded_message['PollMdibDataReplyExt'] and \
                                        decoded_message['PollMdibDataReplyExt']['sequence_no'] != 0:
                            self.messageTimes.append((decoded_message['PollMdibDataReplyExt'][
                                                          'RelativeTime'] - self.relativeInitialTime) / 8192)
                            # print(self.messageTimes[-1])

                            # print('Received Monitor Data.')
                elif decoded_message['PollMdibDataReplyExt']['Type']['OIDType'] == 'NOM_MOC_VMO_METRIC_NU':
                    m = self.distiller.refine_numerics_message(decoded_message)
                    # print('Received Monitor Data.')
                elif decoded_message['PollMdibDataReplyExt']['Type']['OIDType'] == 'NOM_MOC_VMO_AL_MON':
                    m = self.distiller.refine_alarms_message(decoded_message)
                    # print('Received Alarm Data.')

                if m:
                    mm = self.condense(m)
                    logging.info(mm)

            else:
                logging.info('Received ' + message_type + '.')

    def close(self):
        """
        Sends Release Request and waits for confirmation, closes rs232 port
        """
        # Have to use `print` in here b/c logging may be gone if there is an error shutdown

        # If we have already closed or otherwise lost the port, pass and return
        if self.rs232 is None:
            return

        # Send Association Abort and Release Request
        self.rs232.send(self.AssociationAbort)
        print('Sent Association Abort...')
        self.rs232.send(self.ReleaseRequest)
        print('Sent Release Request...')

        not_refused = True

        # Loop to ensure breaking of connection
        count = 0
        while not_refused:
            message = self.rs232.receive()

            if not message:
                print('No release msg received!')
                break

            message_type = self.decoder.getMessageType(message)
            print('Received ' + message_type + '.')

            # If release response or association abort received, continue
            if message_type == 'ReleaseResponse' or message_type == 'AssociationAbort' or message_type == 'TimeoutError' or message_type == 'Unknown':
                print('Connection with monitor released.')
            else:
                if count == 0:
                    logging.info('Disconnecting...')
                    count = 1

        self.rs232.close()
        self.rs232 = None

    def start_polling(self):
        """
        Sends Extended Poll Requests for Numeric, Alarm, and Wave Data
        """
        self.rs232.send(self.MDSExtendedPollActionNumeric)
        logging.info('Sent MDS Extended Poll Action for Numerics...')
        self.rs232.send(self.MDSExtendedPollActionWave)
        logging.info('Sent MDS Extended Poll Action for Waves...')
        self.rs232.send(self.MDSExtendedPollActionAlarm)
        logging.info('Sent MDS Extended Poll Action for Alarms...')

    def single_poll(self):

        now = time.time()

        # Send keep alive if necessary
        if (now - self.last_keep_alive) > (self.KeepAliveTime - 5):
            self.submit_keep_alive()

        m = None

        message = self.rs232.receive()
        if not message:
            logging.warn('No message received')
            if (now - self.last_read_time) >  self.timeout:
                logging.error('Data stream timed out')
                raise IOError

        message_type = self.decoder.getMessageType(message)
        logging.debug(message_type)

        if message_type == 'AssociationAbort' or message_type == 'ReleaseResponse':
            logging.info('Received \'Data Collection Terminated\' message type.')
            self.rs232.close()
            raise IOError

        elif message_type == 'TimeoutError':
            if time.time() - self.last_read_time > 5:
                self.close()
                raise IOError

        elif message_type == 'RemoteOperationError':
            logging.error('Received (unhandled) \'RemoteOpsError\' message type')

        elif message_type == 'MDSSinglePollActionResult':
            logging.info('Received (unhandled) \'SinglePollActionResult\' message type')

        elif message_type == 'MDSExtendedPollActionResult' or message_type == 'LinkedMDSExtendedPollActionResult':
            decoded_message = self.decoder.readData(message)
            m = self.distiller.refine(decoded_message)
            self.last_read_time = time.time()

        else:
            logging.warn('Received {0}'.format(message_type))

        # Update current state
        if m:
            return self.condense(m)

    @staticmethod
    def condense(m):
        # Second pass distillation, from long intermediate format to condensed PERSEUS format

        # logging.debug(m)

        # This is 'NOM_ECG_ELEC_POTL_II' on my monitors, but let's many _any_ ECG wave label to ECG
        ecg_label = None
        for key in m.keys():
            if 'ECG' in key:
                ecg_label = key
                break

        ret =  {'ECG': m.get(ecg_label),
                'Pleth': m.get('PLETH wave label'),
                'Heart Rate': m.get('Heart Rate'),
                'SpO2': m.get('Arterial Oxygen Saturation'),
                'Systolic Blood Pressure': m.get('non-invasive blood pressure_SYS'),
                'Respiration Rate': m.get('Respiration Rate'),
                'alarms': m.get('alarms'),
                'timestamp': m.get('timestamp')}

        # logging.debug(ret)

        return ret

    # TelemetryStream parent class API
    def open(self, blocking=False):
        self.rs232 = RS232(self.port)
        self.initiate_association(blocking)
        self.set_priority_lists()
        self.start_polling()

    def read(self, count=1, blocking=False):
        # Only read(1) is 'safe' and will block until it reconnects.

        if count < 0:
            # Read forever
            self.extended_poll()

        elif count == 0:
            return

        elif count == 1:
            try:
                data = self.single_poll()
                #self.logger.debug(data)

                # Update the sampled data buffer
                self.update_sampled_data(data)

                # Call any update functions in the order they were added
                if data:
                    for f in self.update_funcs:
                        new_data = f(sampled_data=self.sampled_data, **data)
                        data.update(new_data)

                self.logger.info(data)
                return data
            except IOError:
                logging.debug('Caught IOError, closing and reopening')
                self.close()
                self.open(blocking)
                return self.read(1)

        else:
            ret = []
            for i in xrange(0, count):
                data = self.single_poll()
                if data:
                    ret.append(data)
            return ret



if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)

    opts = parse_args()
    # opts.splunk = "perseus"
    opts.gui = "SimpleStripchart"
    # ECG is 64 samples and Pleth is 32 samples every 0.25 secs
    opts.values = ["Pleth", 32*4, 'ECG', 64*4]
    # Pleth _must_ be listed first if both Pleth and ECG are included

    tstream = PhilipsTelemetryStream(port=opts.port, values=opts.values, polling_interval=0.05)

    # Wrapper for UCSF QoS code
    def qos(*args, **kwargs):
        my_qos = QoS()
        history = kwargs.get('sampled_data')
        if history:
            res = my_qos.isPPGGoodQuality(history.get('Pleth').get('samples').y,
                           history.get('Pleth').get('samples').t,
                           32*4)
            return {'qos': res}
        else:
            return -1

    # Attach any post-processing functions
    tstream.add_update_func(qos)
    attach_loggers(tstream, opts)

    if not opts.gui:

        # Create a main loop that just echoes the results to the loggers
        tstream.run(blocking=True)
        # tstream.open()
        # while 1:
        #     tstream.read(1, blocking=True)
        #     time.sleep(0.05)

    else:
        # Pass the to a gui for use in it's own polling function and main loop
        gui = TelemetryGUI(tstream, type=opts.gui, redraw_interval=0.05)
        gui.run(blocking=True)
