# Outline for a telemetry stream library and wrapper functions with structured event
# logging to text files and to Splunk
#
# Dependencies: PyYAML, splunk-sdk, matplotlib
#
# Merck, Spring 2016

import argparse
import logging
import time
import json
import socket
import datetime
from splunklib import client as SplunkClient
import os
import hashlib
import base64
import yaml
import math
from SimpleStripchart import Stripchart


__version_info__ = ('0', '0', '3')
__version__ = '.'.join(__version_info__)

# Lookup credentials from either os.env or shadow.yaml
# This prevents a developer from inadvertently hardcoding and checking in confidential information
shadow = None
with file("shadow.yaml") as f:
    shadow_env = yaml.load(f)
os.environ.update(shadow_env)


class TelemetryGUI(object):
    # Use a class like this to wrap your GUI, be it in QT or MatPlotLib or whatever

    def __init__(self, tstream):
        self.tstream = tstream
        self.display = None

    def update(self):
        self.display.update(_(self.tstream.read(1)))

    def start(self):
        # Make some QT or matplot lib widgets, may want to base which widgets on what
        # vars are defined in the telemetry stream
        self.display = Stripchart()

        # Start listening
        self.tstream.open()

        # Start the polling loop
        while 1:
            self.update()
            time.sleep(0.05)


class TelemetryStream(object):
    # This is an abstract class and/or factory that provides a consistent interface across
    # vendors and devices.
    #
    # The naming convention is based on the standard io.stream functions.

    def __init__(self, *args, **kwargs):
        # Setup a default console logger
        self.logger = logging.getLogger()
        # Do anything else that would be generic across all monitor readers here
        # self.stream = io.BufferedReader
        self.update_funcs = []

    def add_update_func(self, f):
        self.update_funcs.append(f)

    def open(self, *args, **kwargs):
        raise NotImplementedError

    def close(self, *args, **kwargs):
        raise NotImplementedError

    def read(self, *args, **kwargs):
        # Read should echo data to self.logger at "info" level
        raise NotImplementedError

    # May want to add a "__del__" function that always closes or "__exit__" and insist that
    # TelemetryStream be used in a "with"


class StructuredLogDict(dict):
    # This is a convenience class that adds host/time variables and a unique ID to a dictionary
    # and produces a JSON dump when asked for a string.

    # May want to track multiple monitors on a single host eventually, but for now just use
    # the host name as the source
    host = socket.gethostname()

    def __init__(self, _dict):
        super(StructuredLogDict, self).__init__(_dict)
        self['timestamp'] = str(datetime.datetime.now())
        self['source'] = StructuredLogDict.host
        # Often useful to have a uid attached to every entry for disambiguation
        self['id'] = base64.b64encode(hashlib.md5(str(self)).digest()).strip("=")

    def __str__(self):
        return json.dumps(self)

_ = StructuredLogDict  # Naming shortcut for legibility


class SplunkLogHandler(logging.Handler):
    # Send an event to a Splunk index as a specific sourcetype

    host = socket.gethostname()

    def __init__(self, index_name=None, sourcetype='JSON'):
        super(SplunkLogHandler, self).__init__()
        # Create a Service instance and log in
        self.service = SplunkClient.connect(
            host=os.environ['SPLUNK_HOST'],
            port=os.environ['SPLUNK_PORT'],
            username=os.environ['SPLUNK_USER'],
            password=os.environ['SPLUNK_PWORD'])

        # Verify login
        if not self.service.apps:
            raise IOError

        # Retrieve the index for the data
        self.index = self.service.indexes[index_name]
        self.sourcetype = sourcetype

    def emit(self, record):
        # Submit an event over HTTP
        self.index.submit(str(record.msg), sourcetype=self.sourcetype, host=SplunkLogHandler.host)


class PhilipsTelemetryStream(TelemetryStream):
    # Implements specific handshaking and parsing for Philips monitor serial protocol

    def __init__(self, *args, **kwargs):
        super(PhilipsTelemetryStream, self).__init__(args, kwargs)
        self.logger.name = 'PhilipsTelemetry'
        self.logger_format = "philips_telemetry_v2"

    def open(self):
        # Do some handshake stuff
        pass

    def close(self):
        # Do some stuff
        pass

    def read(self, size):
        # data = self.stream.read(size)

        def fake_read1():
            # Return a some arbitrary data values
            x = time.time()
            ecg = math.cos(x)
            pleth = math.sin(x)
            bpm = 80
            spo2 = 95
            alarm_type = None
            alarm_source = None
            return {'ecg': ecg,
                    'pleth': pleth,
                    'bpm': bpm,
                    'spo2': spo2,
                    'alarm_type': alarm_type,
                    'alarm_source': alarm_source}

        data = fake_read1()

        # Call any update functions in the order they were added
        for f in self.update_funcs:
            new_data = f(**data)
            data.update(new_data)

        self.logger.info(_(data))  # The '_' leader will add host/timestamp and dump to JSON
        return data


def parse_args():
    # Creates an options array from the command-line arguments

    parser = argparse.ArgumentParser(description='Philips Monitor Telemetry Stream')
    parser.add_argument('-V', '--version',
                        action='version',
                        version='%(prog)s (version ' + __version__ + ')')
    parser.add_argument('-b', '--binary', help="Name of an hdf5 file for binary logging")
    parser.add_argument('-f', '--file', help="Name of a text file for event logging")
    parser.add_argument('-s', '--splunk', help="Name of a Splunk index for event logging")
    parser.add_argument('-g', '--gui', help="Display a graphic user interface")
    parser.add_argument('--values', nargs="+", help="Select values to monitor")

    _opts = parser.parse_args()
    return _opts


if __name__ == "__main__":

    # By default, we want to look at _all_ messages on the console
    logging.basicConfig(level=logging.DEBUG)

    opts = parse_args()

    # Test output types, as if this were given on the command line
    # opts.file = 'test.log'
    # opts.splunk = 'perseus'
    opts.gui = 'simple_strip'

    # Let's assume that we always only want to open a single stream
    tstream = PhilipsTelemetryStream()

    # Attach any additional loggers
    if opts.file:
        # Add a file stuctured log handler that only saves "INFO" level messages
        fh = logging.FileHandler(opts.file)
        fh.setLevel(logging.INFO)
        tstream.logger.addHandler(fh)

    if opts.splunk:
        # Add a splunk API structured log handler
        sh = SplunkLogHandler(opts.splunk, tstream.logger_format)
        sh.setLevel(logging.INFO)
        tstream.logger.addHandler(sh)

    if opts.binary:
        # Set flag for a binary file output
        # You want to store that waveform data in a compact binary format, not as text files
        pass

    # Let's say we have some different quality of signal functions that we might want to compute
    def qos(*args, **kwargs):
        val = kwargs.get('pleth') > 0
        return {'qos': val}

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
        gui = TelemetryGUI(tstream)
        gui.start()
