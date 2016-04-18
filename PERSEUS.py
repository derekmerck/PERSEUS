"""
PERSEUS Core
Push Electronic Relay for Smart Alarms for End User Situational Awareness (PERSEUS)

[Derek Merck](derek_merck@brown.edu)
[Leo Kobayashi](lkobayashi@lifespan.org)
Spring 2015

<https://github.com/derekmerck/PERSEUS>

Dependencies: PyYAML, splunk-sdk, Twilio

See README.md for usage, notes, and license info.
"""

import argparse
import logging
import os
import yaml

from Dispatch import Dispatch
from TelemetryStream import TelemetryStream, PhilipsTelemetryStream

__package__ = "PERSEUS"
__description__ = "Push Electronic Relay for Smart Alarms for End User Situational Awareness"
__url__ = "https://github.com/derekmerck/PERSEUS"
__author__ = 'Derek Merck'
__email__ = "derek_merck@brown.edu"
__license__ = "MIT"
__version_info__ = ('0', '7', '0')
__version__ = '.'.join(__version_info__)

try:
    with file("shadow.yaml") as f:
        shadow_env = yaml.load(f)
    os.environ.update(shadow_env)
except IOError as e:
    print("Unable to open shadow.yaml file for additional environment vars") #Does not exist OR no read permissions


def parse_args():

    parser = argparse.ArgumentParser(prog='PERSEUS', description=__description__)

    parser.add_argument('-V', '--version',
                        action='version',
                        version='%(prog)s (version ' + __version__ + ')')

    subparsers = parser.add_subparsers(help='sub-command help')

    # create the parser for the "dispatch" command
    parser_dispatch = subparsers.add_parser('dispatch',
                                            dest='dispatch',
                                            description=Dispatch.__description__,
                                            help='Start an instance of a PERSEUS Dispatch server')
    parser_dispatch.add_argument('--config',
                        default='config.yaml',
                        help='YAML description of the alert rules, zones, and roles (default: config.yaml)')

    # create the parser for the "listen" command
    parser_listen = subparsers.add_parser('listen',
                                           alias=['monitor'],
                                           dest='listen',
                                           description=PhilipsTelemetryStream.__description__,
                                           help='Start an instance of a PERSEUS Listener node')
    parser_listen.add_argument('-b', '--binary', help="Name of an hdf5 file for binary logging (UNIMPLEMENTED)")
    parser_listen.add_argument('-f', '--file', help="Name of a text file for event logging")
    parser_listen.add_argument('-s', '--splunk', help="Name of a Splunk index for event logging")
    parser_listen.add_argument('-g', '--gui', help="Display a graphic user interface, e.g., 'SimpleStripchart'")
    # Default for PL203 usb to serial device
    parser_listen.add_argument('-p', '--port', help="Device port", default="/dev/cu.usbserial")
    parser_listen.add_argument('--values', nargs="+",
                        help="List of paired value names and frequencies to monitor, e.g. 'ecg, 100, pleth, 64'")

    _opts = parser.parse_args()
    return _opts

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    opts = parse_args()

    if opts.dest == 'dispatch':
        logging.debug('PERSEUS Dispatch v{0}'.format(Dispatch.__version__))

        with open(opts.config, 'rU') as f:
            config = yaml.load(f)
            rules, zones, roles = config.get('rules'), config.get('zones'), config.get('roles')

        dispatch = Dispatch.Dispatch(rules=rules, zones=zones, roles=roles)
        dispatch.run()

    elif opts.dest == 'listen':

        logging.debug('PERSEUS Listener v{0}'.format(PhilipsTelemetryStream.__version__))
        logging.debug('Forked from the NeuroLogic Philips Vitals Monitor Decoder')

        tstream = PhilipsTelemetryStream.PhilipsTelemetryStream(**opts)
        tstream.add_update_func(PhilipsTelemetryStream.qos)
        TelemetryStream.attach_loggers(opts)

        if opts.gui:
            # Pass the to a gui for use in it's own polling function and main loop
            gui = TelemetryStream.TelemetryGUI(tstream, type=opts.gui, polling_interval=0.05, redraw_interval=0.05)
            gui.run(blocking=True)

        else:
            tstream.run()
