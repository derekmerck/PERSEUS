"""
PERSEUS Core
Push Electronic Relay for Smart Alarms for End User Situational Awareness (PERSEUS)

[Derek Merck](derek_merck@brown.edu)
[Leo Kobayashi](lkobayashi@lifespan.org)
Spring 2015

<https://github.com/derekmerck/PERSEUS>

Dependencies: Pyro4, Numpy, matplotlib

See README.md for usage, notes, and license info.
"""

from __future__ import print_function
import os
import argparse
import logging
import time
import yaml
import textwrap
import smtplib
import Pyro4
import numpy as np

__package__ = "PERSEUS"
__description__ = "Push Electronic Relay for Smart Alarms for End User Situational Awareness"
__url__ = "https://github.com/derekmerck/PERSEUS"
__author__ = 'Derek Merck'
__email__ = "derek_merck@brown.edu"
__license__ = "MIT"
__version_info__ = ('0', '2', '0')
__version__ = '.'.join(__version_info__)


class PNode:
    """
    Base class for shared code across PERSEUS nodes.
    """

    def __init__(self, _pid, _settings, _topology):
        self.pid = _pid
        self.settings = _settings
        self.topology = _topology
        self.data = {}
        self._status = 'Init'
        self.pn_type = self.topology[pid]['type']
        logging.basicConfig()
        self.logger = logging.getLogger('.'.join([__package__, self.pn_type]))
        self.logger.setLevel(self.settings['LOGGING_LEVEL'])
        self.logger.info('Starting up node %s' % self.pid)
        self.clock = 0
        self.update_interval = 1.0 / (self.settings['UPDATE_FREQ'])


    def status(self):
        return self._status




class Control(PNode):
    """
    Control's .data dictionary is organized like this:

    ----
    active: [listener01, listener02]
    inactive: [listener02]

    listener01:
      stream: [  [0.1,100,200,0], [0.2,101,199,0], ...
      stream_names:
        - clock time
        - alert status
        - blood pressure
        - heart rate

    ---

    listener01 establishes a stream with control.register_listener(self, stream_names) then it can push updates with
    control.put(self,stream_data)

    Stream data will be pushed into the fixed size deque, old data will be dropped.  Assuming the sample rate is 20/sec
    and the stream_len variable is 2000, that gives us 100 secs or 1.5 mins of immediately available data.

    Old data is flushed to log, csv, or h5 files as it is dumped.

    """

    # TODO: Consider how to push updates back to listener nodes, is that ever necessary?

    class Messenger:
        """
        Handles SMS alerts
        """

        services = textwrap.dedent('''
            # Sender relay servers
            gmail.com: 'smtp.gmail.com:587'

            ---
            # Receiver device gateways
            alltel:     message.alltel.com
            att:        txt.att.net
            boost:      myboostmobile.com
            nextel:     messaging.sprintpcs.com
            sprint:     messaging.sprintpcs.com
            t-mobile:   tmomail.net
            uscellular: email.uscc.net
            verizon:    vtext.com
            virgin:     vmobl.com
            ''')
        relays, gateways = yaml.load_all(services)

        def __init__(self, _settings, _topology, _devices):
            self.devices = _devices
            self.settings = _settings
            self.topology = _topology
            self.logger = logging.getLogger('.'.join([__package__, 'Messenger']))
            self.logger.setLevel(self.settings['LOGGING_LEVEL'])
            self.logger.info('Starting up')
            self.fromaddr = '%s <%s>' % (self.settings['SMS_NAME'], self.settings['SMS_EMAIL'])
            tmp = self.settings['SMS_EMAIL'].split('@')
            self.relay_username = tmp[0]
            self.relay_server = self.relays[tmp[1]]
            self.relay_password = self.settings['SMS_RELAY_PASSWORD']

        def message(self, msg, did):
            number = self.devices[did]['number']
            carrier = self.devices[did]['carrier']
            toaddr = '%s@%s' % (number, self.gateways[carrier])
            self.send_message(self.relay_server, self.relay_username, self.relay_password, self.fromaddr, toaddr, msg)

        @staticmethod
        def send_message(relay_server, relay_username, relay_password, fromaddr, toaddr, msg):
            logger.info([relay_server, relay_username, relay_password, fromaddr, toaddr, msg])
            if not settings['SMS']['ENABLE']:
                return
            server = smtplib.SMTP(relay_server)
            server.starttls()
            server.login(relay_username, relay_password)
            server.sendmail(fromaddr, toaddr, msg)
            server.quit()

    def __init__(self, _pid, _settings, _topology, _devices):
        PNode.__init__(self, _pid, _settings, _topology)
        self.max_stream_len = self.settings["CTRL_STREAM_LEN"]
        self.messenger = Control.Messenger(_settings, _topology, _devices)

    def send_alert(self, _pid):
        """
        Handle an alert raised in a listener node
        """
        did = self.topology[_pid]['alert_device']
        self.messenger.message('There\'s an alert!', did)

    def get(self, _pid, key="stream", clock="0"):
        """Getting 'stream_names' returns a list of available streams"""
        if self.data.get(_pid) is not None:
            if self.data[_pid].get(key) is not None:
                value = self.data[_pid][key]
                self.logger.debug("{0} requested {1}, returning {2}.".format(_pid, key, value))
                return value
        # TODO: If "clock" is set in the request, we want to only return samples that are bigger than that

    def put(self, _pid, value, key="stream"):
        if self.data.get(_pid, None) is None:
            self.data[_pid] = {}
        self.data[_pid][key] = value
        self.logger.debug("{0} set {1} to {2}.".format(_pid, key, self.data[_pid][key]))

    def start(self):
        self._status = "Ready"
        Pyro4.Daemon.serveSimple(
            {
                node: "perseus." + self.pid
            },
            ns=True)


class Listener(PNode):
    def __init__(self, _pid, _settings, _topology):
        PNode.__init__(self, _pid, _settings, _topology)
        self.controller_id = self.topology[self.pid]['controller']
        self.control = Pyro4.Proxy("PYRONAME:perseus." + self.controller_id)
        self.stream_names = ['clock', 'sample01', 'sample02']

        self.times = None
        self.values = None
        self.i = None
        self.setup_pseudodata_from_file('RIHEDUrg CDev-03MP90_PLETH_20150907_125701.txt'
)

    def register(self):
        status = self.control.status()
        if status == 'Ready':
            self.control.put(self.pid, self.stream_names, "stream_names")
            self.logger.debug("{0} registering stream_names with {1}.".format(self.pid, self.controller_id))
            self._status = "Ready"

    def put(self, value):

        while self._status != "Ready":
            self.register()
        # TODO: Add a timeout here

        if self.control.status() == 'Ready':
            self.control.put(self.pid, value)
            self.logger.debug("{0} sending stream {1}.".format(self.pid, value))

    # TODO: Replace this with an interactive connection to a local "METEOR"
    def generate_random_data(self):
        data = np.random.rand(2, 1).tolist()
        self.put([self.clock, data[0][0], data[1][0]])

    def setup_pseudodata_from_file(self, fn):
        import mutils
        self.times, self.values = mutils.read_numerics(fn)
        self.i = 0

    def generate_pseudodata(self):
        self.i = self.i+1
        self.clock = self.times(self.i)
        self.data = self.values(self.i)

    def start(self):
        while True:
            self.clock += self.update_interval
            self.generate_pseudodata()
            time.sleep(self.update_interval)


class Display(PNode):
    def __init__(self, _pid, _settings, _topology):
        PNode.__init__(self, _pid, _settings, _topology)
        self.controller_id = self.topology[self.pid]['controller']
        self.control = Pyro4.Proxy("PYRONAME:perseus." + self.controller_id)

    def get(self, _pid, key="stream", clock="-1"):
        if self.control.status() == 'Ready':
            data = self.control.get(_pid, key)
            self.logger.debug("Requested pid {0}, got {1}.".format(_pid, data))
            return data

    def start(self):
        self.simple_display()

    def simple_display(self):
        import SimpleDisplay
        SimpleDisplay.Stripchart(self)


def get_args():
    """
    Setup args and usage
    """

    parser = argparse.ArgumentParser(description='PERSEUS Core')
    parser.add_argument('-p', '--pid', help='P-node id REQ', required=True)
    parser.add_argument('-c', '--config', help='Configuration file (default: config.yaml)', default='config.yaml')
    parser.add_argument('-s', '--shadow', help='Shadow config file (default: shadow.yaml)', default='shadow.yaml')

    # Can build a simple single node topology out of this if no config is provided
    parser.add_argument('--type', help='(config-free REQ) P-node type (server, monitor, display)')
    parser.add_argument('--controller', help='Controller node name (default=control0)',
                        default='control0')
    parser.add_argument('--location', help='P-node location', default='Unspecified')
    parser.add_argument('--devices', help='Dictionary of alert devices for control nodes', default={})
    return parser.parse_args()


def setup_config(args):
    """
    Parse together config and shadow to create settings, topology, and devices
    """

    # Load config & shadow config
    package_directory = os.path.dirname(os.path.abspath(__file__))
    # TODO: Add catch for no config file
    fn = os.path.join(package_directory, args.config)
    f = open(fn, 'r')
    [settings_, topology_, devices_] = yaml.load_all(f)
    # TODO: Add catch for no shadow file
    fn = os.path.join(package_directory, args.shadow)
    f = open(fn, 'r')
    [sh_settings, sh_topology, sh_devices] = yaml.load_all(f)
    if sh_settings is not None:
        settings_.update(sh_settings)
    if sh_topology is not None:
        topology_.update(sh_topology)
    if sh_devices is not None:
        devices_.update(sh_devices)
    return settings_, topology_, devices_


if __name__ == "__main__":

    arg_dict = get_args()
    settings, topology, devices = setup_config(arg_dict)

    # Setup logging
    logging.basicConfig()
    logger = logging.getLogger('.'.join([__package__, 'Core']))
    logger.setLevel(settings['LOGGING_LEVEL'])
    logger.info('version %s' % __version__)

    # TODO: Add sensible defaults for settings
    # TODO: Add catch for no topology file by using input args
    # TODO: Add empty dict for devices if none

    # Output config to logger
    logger.debug("SETTINGS=" + str(settings))
    logger.debug("TOPOLOGY=" + str(topology))
    logger.debug("DEVICES =" + str(devices))

    # Start up the node
    pid = arg_dict.pid
    pn_type = topology[pid]['type']

    node = None
    if pn_type == 'control':
        node = Control(pid, settings, topology, devices)
    elif pn_type == 'display':
        node = Display(pid, settings, topology)
    elif pn_type == 'listener':
        node = Listener(pid, settings, topology)
    else:
        logger.warning('No P-node type to invoke for %s' % pn_type)

    if node is not None:
        node.start()
