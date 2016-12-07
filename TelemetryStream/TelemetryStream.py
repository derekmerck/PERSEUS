# Outline for a telemetry stream library and wrapper functions with structured event
# logging to text files and to Splunk
#
# Dependencies: PyYAML, splunk-sdk, matplotlib, pyserial, numpy
#
# Merck, Spring 2016

from __future__ import unicode_literals, division

import random
import argparse
import logging
import time
import json
import socket
import datetime
from splunklib import client as SplunkClient
import os
import yaml
import numpy as np
import subprocess
import collections

__hash__ = None
try:
    __hash__ = subprocess.check_output(["git", "describe", "--tags"]).strip()
except:
    __hash__ = 'unknown'

try:
    from SimpleStripchart import Stripchart
except ImportError:
    logging.error('Cannot import Stripchart, check Matplotlib')

# @derek
# TODO: Split out data logger and status loggers
# TODO: Split into multiple threads -- is this really going to make a difference?

__description__ = "Monitor decoder for PERSEUS (Push Electronic Relay for Smart Alarms for End User Situational Awareness)"

# Lookup credentials from either os.env or shadow.yaml
# This prevents a developer from inadvertently hardcoding and checking in confidential information
try:
    with file("shadow.yaml") as f:
        shadow_env = yaml.load(f)
    os.environ.update(shadow_env)
except IOError as e:
    print("Unable to open shadow.yaml file for additional environment vars") # Does not exist OR no read permissions


class TelemetryGUI(object):
    # Use a class like this to wrap your GUI, be it in QT or MatPlotLib or whatever

    def __init__(self, tstream, **kwargs):
        self.tstream = tstream
        self.display = None
        self.display_type = kwargs.get('display_type', 'SimpleStripchart')
        self.redraw_interval = kwargs.get('redraw_interval', 0.1)
        self.last_redraw = time.time()
        self.last_poll = self.last_redraw

    def update(self, blocking=False):
        now = time.time()

        if now > (self.last_poll + self.tstream.polling_interval):
            data = self.tstream.read(1, blocking=blocking)
            if data:
                self.display.update_data(data, self.tstream.sampled_data)
                self.last_poll = now

        if now > (self.last_redraw + self.redraw_interval):
            self.display.redraw()
            self.last_redraw = now

    def run(self, blocking=False):

        if self.display_type == 'SimpleStripchart':
            self.display = Stripchart(self.tstream)
        else:
            logging.warn('Unknown display type requested!')

        # Start listening
        self.tstream.open()

        # Start the polling loop
        while 1:
            self.update(blocking)
            time.sleep(self.redraw_interval/2)


class SampledDataBuffer(object):
    # This is a fixed-length double queue for time/value pairs s.t. f(t)=y
    # Once initialized, it can be updated with a single time point and a set of values
    # taken at a given frequency.
    # t is re-evaluated relative to the initialization time

    def __init__(self, freq, dur):
        self.freq = freq
        self.dur = dur
        self.y = np.zeros(self.freq*self.dur)
        self.t = np.zeros(self.freq*self.dur)
        self.start_time = datetime.datetime.now()
        self.t1 = None
        self.dropped_packets = 0

        # self.t = np.linspace(now-self.dur, now-1, self.freq*self.dur)

    def rolling_append(self, _t0, values):

        if values is None:
            return

        # Convert t0 to seconds since start_time
        t0 = (_t0 - self.start_time).total_seconds()
        if not self.t1:
            self.t1 = t0
        # logging.debug('t0 {0}'.format(t0))
        # logging.debug('t1 {0}'.format(self.t1))

        t0 -= self.t1

        length = values.size or 1  # For scalar
        # logging.debug('len {0}'.format(length))
        if length == 1:
            times = t0
        else:
            sec_offset = length/self.freq
            times = np.linspace(t0, t0+sec_offset, length)

        # TODO: Fix this if it's important; it needs to fix itself so it does't get into a loop
        # if t0 - self.t[-1] > 0:
        #     self.dropped_packets += 1
        #     logging.warn('>{0} dropped packets (t0={t0} != t[-1]={t1})'.format(self.dropped_packets, t0=t0, t1=self.t[-1]))
        #     # Everytime this happens, it increases the total duration; if it's consistent, it
        #     # will be a multiplier on the duration.

        self.y = np.roll(self.y, -length)
        self.y[-length:] = values
        self.t = np.roll(self.t, -length)
        self.t[-length:] = times

        # logging.debug(self.y)
        # logging.debug(self.t)


class TelemetryStream(object):
    # This is an abstract class and/or factory that provides a consistent interface across
    # vendors and devices.

    def __init__(self, *args, **kwargs):
        # Setup a specialized output logger
        self.logger = logging.getLogger()
        # self.logger.setLevel(logging.WARN)
        # Do anything else that would be generic across all monitor readers here
        self.update_funcs = []
        self.polling_interval = kwargs.get('polling_interval', 0.25)
        self.sampled_data_dur = kwargs.get('sampled_data_dur', 7)
        self.sampled_data = {}

        sampled_data_args = kwargs.get('values')
        # logging.debug(sampled_data_args)
        if sampled_data_args:
            for key, freq in zip(sampled_data_args[0::2], sampled_data_args[1::2]):
                self.sampled_data[key] = {'freq': freq,
                                          'samples': SampledDataBuffer(freq, self.sampled_data_dur)}

        # logging.debug('sampled data array')
        # logging.debug(self.sampled_data)

    def update_sampled_data(self, data):
        if not data:
            return

        for key, value in data.iteritems():
            if key in self.sampled_data.keys():
                t = data['timestamp']
                y = data[key]
                self.sampled_data[key]['samples'].rolling_append(t,y)

    def __del__(self):
        # Note that logging may no longer exist by here
        print("Tearing down connection object")
        self.close()

    def add_update_func(self, f):
        self.update_funcs.append(f)

    def run(self, blocking=False):
        # Create a main loop that just echoes the results to the loggers
        self.open()
        while 1:
            self.read(1, blocking=blocking)
            time.sleep(self.polling_interval)

    def open(self, *args, **kwargs):
        raise NotImplementedError

    def close(self, *args, **kwargs):
        raise NotImplementedError

    def read(self, *args, **kwargs):
        # Read should echo data to self.logger at "info" level
        raise NotImplementedError


class TelemetryEncoder(json.JSONEncoder):
    def default(self, o):
        # Deal with datetime
        if isinstance(o, datetime.datetime):
            return o.isoformat()
        # Deal with numpy
        if type(o).__module__ == np.__name__:
            return o.tolist()
        return json.JSONEncoder.default(self, o)


class JSONLogHandler(logging.FileHandler):

    def __init__(self, *args, **kwargs):
        super(JSONLogHandler, self).__init__(*args)
        self.show_host_time = kwargs.get('host_time', False)

    def emit(self, record):
        # Submit an event over HTTP
        # logging.debug("Emitting: {0}".format(record.msg))
        if not record.msg: return
        if record.levelno != logging.INFO: return
        if self.show_host_time:
            record.msg['timestamp'] = datetime.datetime.now()
        # Sorts the timestamp up to the front for legibility/indexing
        msg = collections.OrderedDict([('timestamp', record.msg['timestamp'])])
        msg.update(record.msg)
        msgs = json.dumps(msg, cls=TelemetryEncoder, ensure_ascii=False).encode('ascii', errors='ignore')
        record.msg = msgs
        super(JSONLogHandler, self).emit(record)


class SplunkLogHandler(logging.Handler):
    # TODO: Could extend HTTPHandler instead and use built-in mapping function
    # Send an event to a Splunk index as a specific sourcetype

    host = socket.gethostname()

    def __init__(self, index_name=None, sourcetype='_json', **kwargs):
        super(SplunkLogHandler, self).__init__()
        self.show_host_time = kwargs.get('host_time', False)

        # Create a Service instance and log in
        self.service = SplunkClient.connect(
            host=os.environ['SPLUNK_HOST'],
            port=os.environ['SPLUNK_PORT'],
            username=os.environ['SPLUNK_USER'],
            password=os.environ['SPLUNK_PWORD'])

        # Verify login
        if not self.service.apps:
            logging.error('Unable to connect to Splunk server')
            raise IOError

        # Retrieve the index for the data
        self.index = self.service.indexes[index_name]
        self.sourcetype = sourcetype

    def emit(self, record):
        # Submit an event over HTTP
        # logging.debug("Emitting: {0}".format(record.msg))
        if not record.msg: return
        if record.levelno != logging.INFO: return
        if self.show_host_time:
            record.msg['timestamp'] = datetime.datetime.now
        # Sorts the timestamp up to the front for legibility/indexing
        msg = collections.OrderedDict([('timestamp', record.msg['timestamp'])])
        msg.update(record.msg)
        msgs = json.dumps(msg, cls=TelemetryEncoder, ensure_ascii=False).encode('ascii', errors='ignore')
        self.index.submit(msgs, sourcetype=self.sourcetype, host=SplunkLogHandler.host)

class SampleTelemetryStream(TelemetryStream):
    # Implements specific handshaking and parsing for Philips monitor serial protocol

    def __init__(self, *args, **kwargs):
        super(SampleTelemetryStream, self).__init__(*args, **kwargs)
        self.logger.name = 'SampleTelemetry'
        self.polling_freq = 4  # Expected number of polls per second to simulate
        self.drop_rate = 0.01   # Fraction of polls to drop

    def open(self):
        # Do some handshake stuff
        pass

    def close(self):
        # Do some stuff
        pass

    def read(self, size, **kwargs):

        def fake_read1():
            # Drop every few samples
            if random.random() < self.drop_rate:
                logging.warn('Dropping a poll')
                return

            # Return a some arbitrary data values
            now = time.time()

            ret = {'timestamp': datetime.datetime.now() - datetime.timedelta(seconds=5)}

            data0 = self.sampled_data.get('ECG')
            data1 = self.sampled_data.get('Pleth')
            if data0:
                x0 = np.linspace(now-1.0/self.polling_freq, now, data0['freq']/self.polling_freq)
                y0 = np.cos(x0)
                ret['ECG'] = y0
            if data1:
                x1 = np.linspace(now-1.0/self.polling_freq, now, data1['freq']/self.polling_freq)
                y1 = np.sin(x1)
                ret['Pleth'] = (y1*900)+2000

            ret['Heart Rate'] = 80
            ret['SpO2'] = 95
            ret['alarms'] = {'A0' : {'type': None,
                                     'source': None } }
            return ret

        data = fake_read1()

        # Update the sampled data buffer
        self.update_sampled_data(data)

        # Call any update functions in the order they were added
        if data:
            for f in self.update_funcs:
                new_data = f(sampled_data=self.sampled_data, **data)
                data.update(new_data)

        self.logger.info(data)
        return data


def configure_parser(parser):
    parser.add_argument('-b', '--binary', help="Name of an hdf5 file for binary logging")
    parser.add_argument('-f', '--file', help="Name of a text file for event logging")
    parser.add_argument('-ht', '--host_time', help="Include host time in file outputs", action='store_true')
    parser.add_argument('-s', '--splunk', help="Name of a Splunk index for event logging")
    parser.add_argument('-g', '--gui', help="Display a graphic user interface, e.g., 'SimpleStripchart'")
    # Default for PL203 usb to serial device
    parser.add_argument('-p', '--port', help="Device port (or 'test')", default="/dev/cu.usbserial")
    parser.add_argument('--values', nargs="+",
                        help="List of paired value names and frequencies to monitor, e.g. 'Pleth 128 ECG 256'",
                        default=['Pleth', 128, 'ECG', 256])
    return parser


def parse_args():
    # Creates an options array from the command-line arguments

    parser = argparse.ArgumentParser(description=__description__)
    parser.add_argument('-V', '--version',
                        action='version',
                        version='%(prog)s (version ' + __hash__ + ')')
    parser = configure_parser(parser)
    _opts = parser.parse_args()
    return _opts


def attach_loggers(tstream, opts):
    # Attach any additional loggers
    if opts.file:
        # Add a file stuctured log handler that only saves "INFO" level messages
        fh = JSONLogHandler(opts.file, host_time=opts.host_time)
        fh.setLevel(logging.INFO)
        tstream.logger.addHandler(fh)

    if opts.splunk:
        # Add a splunk API structured log handler
        sh = SplunkLogHandler(opts.splunk)
        sh.setLevel(logging.INFO)
        tstream.logger.addHandler(sh)

    if opts.binary:
        # Set flag for a binary file output
        # You want to store that waveform data in a compact binary format, not as text files
        pass


if __name__ == "__main__":

    # By default, we want to look at _all_ messages on the console
    logging.basicConfig(level=logging.DEBUG)
    logging.debug('PERSEUS Listener v{0}'.format(__hash__))
    logging.debug('Forked from the pyMind Philips Vitals Monitor Decoder')

    opts = parse_args()

    # Test output types, as if this were given on the command line
    # opts.file = 'test.log'
    # opts.splunk = 'perseus'
    # opts.gui = 'SimpleStripchart'
    # opts.values = ['ECG', 128, 'Pleth', 32]

    # Let's assume that we always only want to open a single stream
    tstream = SampleTelemetryStream(values=opts.values)

    attach_loggers(tstream, opts)

    # Let's say we have some different quality of signal functions that we might want to compute
    def qos(*args, **kwargs):
        history = kwargs.get('sampled_data')
        if history:
            val = history.get('ECG').get('samples').y > 0
            return {'qos': np.count_nonzero(val)}
        else:
            return -1

    # Attach any post-processing functions
    tstream.add_update_func(qos)

    # Start listening
    tstream.open()

    if not opts.gui:
        # Create a main loop that just echoes the results to the loggers
        while 1:
            tstream.read(1)
            time.sleep(0.5)

    else:
        # Pass the to a gui for use in it's own polling function and main loop
        gui = TelemetryGUI(tstream, type=opts.gui)
        gui.run()
