#! /usr/bin/python
"""
PERSEUS Core
Push Electronic Relay for Smart Alarms for End User Situational Awareness (PERSEUS)

[Derek Merck](derek_merck@brown.edu)
[Leo Kobayashi](lkobayashi@lifespan.org)
Spring 2016

<https://github.com/derekmerck/PERSEUS>

Dependencies: PyYAML, splunk-sdk, Twilio, numpy, scipy, pyserial, matplotlib

See README.md for usage, notes, and license info.
"""

import argparse
import logging
import os
import yaml
import subprocess

from Dispatch import Dispatch
from TelemetryStream import TelemetryStream, PhilipsTelemetryStream

__package__ = "PERSEUS"
__description__ = "Push Electronic Relay for Smart Alarms for End User Situational Awareness"
__url__ = "https://github.com/derekmerck/PERSEUS"
__author__ = 'Derek Merck'
__email__ = "derek_merck@brown.edu"
__license__ = "MIT"
__version_info__ = ('0', '3', '4')
__version__ = '.'.join(__version_info__)

__hash__ = None
try:
    __hash__ = subprocess.check_output(["git", "describe", "--tags"]).strip()
except:
    __hash__ = __version__

try:
    with file("shadow.yaml") as f:
        shadow_env = yaml.load(f)
    os.environ.update(shadow_env)
except IOError as e:
    print("Unable to open shadow.yaml file for additional environment vars") # Does not exist OR no read permissions


def parse_args():

    parser = argparse.ArgumentParser(prog='PERSEUS', description=__description__)

    parser.add_argument('-V', '--version',
                        action='version',
                        version='%(prog)s (version ' + __version__ + ')')

    subparsers = parser.add_subparsers(dest='command')

    # create the parser for the "dispatch" command
    parser_dispatch = subparsers.add_parser('dispatch',
                                            description=Dispatch.__description__,
                                            help='Start an instance of a PERSEUS Dispatch server')
    parser_dispatch = Dispatch.configure_parser(parser_dispatch)

    # create the parser for the "listen" command
    parser_listen = subparsers.add_parser('listener',
                                           description=TelemetryStream.__description__,
                                           help='Start an instance of a PERSEUS Listener node')
    parser_listen = TelemetryStream.configure_parser(parser_listen)

    _opts = parser.parse_args()
    return _opts

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    opts = parse_args()

    if opts.command == 'dispatch':

        logging.debug('PERSEUS Dispatch v{0}'.format(__hash__))

        with open(opts.config, 'rU') as f:
            config = yaml.load(f)
            rules, zones, roles = config.get('rules'), config.get('zones'), config.get('roles')

        dispatch = Dispatch.Dispatch(rules=rules, zones=zones, roles=roles)
        dispatch.run()

    elif opts.command == 'listener':

        logging.debug('PERSEUS Listener {0}'.format(__hash__))
        logging.debug('Forked from the pyMind Philips Vitals Monitor Decoder')

        tstream, polling_interval, redraw_interval = None, None, None
        if opts.port == "sample":
            tstream = TelemetryStream.SampleTelemetryStream(values=opts.values, polling_interval=0.25)
            redraw_interval = 0.1
        else:
            tstream = PhilipsTelemetryStream.PhilipsTelemetryStream(polling_interval=0.05, **vars(opts))
            tstream.add_update_func(PhilipsTelemetryStream.qos)
            redraw_interval = 0.05

        TelemetryStream.attach_loggers(tstream, opts)

        if opts.gui:
            # Pass the stream to a gui for use in it's own polling function and main loop
            gui = TelemetryStream.TelemetryGUI(tstream, type=opts.gui, redraw_interval=redraw_interval)
            gui.run(blocking=True)

        else:
            tstream.run(blocking=True)
