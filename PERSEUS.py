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
__version_info__ = ('0', '1', '4')
__version__ = '.'.join(__version_info__)


class Pnode:
    """
    Base class for shared code across PERSEUS nodes.
    """

    def __init__(self, _pid, _settings, _topology):
        self.pid = _pid
        self.settings = _settings
        self.topology = _topology
        self.data = {}
        self._status = 'Ready'
        self.pn_type = self.topology[pid]['type']
        logging.basicConfig()
        self.logger = logging.getLogger('.'.join([__package__, self.pn_type]))
        self.logger.setLevel(self.settings['LOGGING_LEVEL'])
        self.logger.info('Starting up node %s' % self.pid)


class Control(Pnode):
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
        Pnode.__init__(self, _pid, _settings, _topology)
        self.messenger = Control.Messenger(_settings, _topology, _devices)

    def send_alert(self, _pid):
        # An alert has been raised in a listener node
        did = self.topology[_pid]['alert_device']
        self.messenger.message('There\'s an alert!', did)

    def status(self):
        return self._status

    def get(self, _pid, key):
        """Getting 'active' returns a list of available streams"""
        self.logger.debug("{0} requested {1}, returning {2}.".format(_pid, key, self.data[key]))
        return self.data[key]

    def put(self, _pid, value, key=None):
        # TODO: Anytime a pid is added, set a key 'active'; after it stops, move it to 'inactive'
        if key is None:
            key = _pid
        self.data[key] = value
        self.logger.debug("{0} set {1} to {2}.".format(_pid, key, self.data[key]))

    def start(self):
        Pyro4.Daemon.serveSimple(
            {
                node: "perseus." + self.pid
            },
            ns=True)

        # TODO: Consider how to push updates back to listener nodes, is that ever necessary?


class Listener(Pnode):
    def __init__(self, _pid, _settings, _topology):
        Pnode.__init__(self, _pid, _settings, _topology)
        self.controller_id = self.topology[self.pid]['controller']
        self.control = Pyro4.Proxy("PYRONAME:perseus." + self.controller_id)

    def put(self, value):
        status = self.control.status()
        if status == 'Ready':
            self.control.put(self.pid, value)
            self.logger.debug("For key {0}, set {1}.".format(self.pid, value))

    # TODO: Replace this with an interactive connection to a local "METEOR"
    def generate_data(self):
        data = np.random.rand(1)
        self.put(data)

    def start(self):
        self.put('Hello there!')


class Display(Pnode):
    def __init__(self, _pid, _settings, _topology):
        Pnode.__init__(self, _pid, _settings, _topology)
        self.controller_id = self.topology[self.pid]['controller']
        self.control = Pyro4.Proxy("PYRONAME:perseus." + self.controller_id)

    def get(self, key):
        status = self.control.status()
        if status == 'Ready':
            data = self.control.get(self.pid, key)
            self.logger.debug("Requested key {0}, got {1}.".format(key, data))
            return data

    def start(self):
        self.simple_display()

    def simple_display(self):
        import SimpleDisplay

        def emitter(p=0.03):
            """
            return a random value with probability p, else 0
            """
            while True:
                v = np.random.rand(1)
                if v > p:
                    yield 0.
                else:
                    yield np.random.rand(1)

        # TODO: Pass in get from listener0
        SimpleDisplay.Stripchart(emitter)


def get_args():
    """
    Setup args and usage
    """

    parser = argparse.ArgumentParser(description='PERSEUS Core')
    parser.add_argument('-p', '--pid', help='P-node id REQ', required=True)
    parser.add_argument('-c', '--config', help='Configuration file (default: config.yaml)', default='config.yaml')
    parser.add_argument('-s', '--shadow', help='Shadow config file (default: shadow.yaml)', default='shadow.yaml')
    parser.add_argument('--type', help='(config-free REQ) P-node type (server, monitor, display)')
    parser.add_argument('--controller', help='(config-free OPT) Controller node name (default=control0)',
                        default='control0')
    parser.add_argument('--location', help='(config-free OPT) P-node location', default='Unspecified')
    parser.add_argument('--devices', help='(config-free OPT) Dictionary of alert devices for control nodes')
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
        settings.update(sh_settings)
    if sh_topology is not None:
        topology.update(sh_topology)
    if sh_devices is not None:
        devices.update(sh_devices)
    return settings_, topology_, devices_


print('hi')
if __name__ == "__main__":

    print("hello")

    arg_dict = get_args()
    settings, topology, devices = setup_config(arg_dict)

    # Setup logging
    logging.basicConfig()
    logger = logging.getLogger('.'.join([__package__, 'Core']))
    logger.setLevel(settings['LOGGING_LEVEL'])
    logger.info('version %s' % __version__)

    # Output config to logger
    logger.debug("SETTINGS=" + str(settings))
    logger.debug("TOPOLOGY=" + str(topology))
    logger.debug("DEVICES =" + str(devices))

    # Start up the node
    # TODO: Add catch for no topology file by using input args
    pid = arg_dict.pid
    pn_type = topology[pid]['type']

    if pn_type == 'control':
        node = Control(pid, settings, topology, devices)
        node.start()
    elif pn_type == 'display':
        node = Display(pid, settings, topology)
        node.start()
    elif pn_type == 'listener':
        node = Listener(pid, settings, topology)
        node.start()
    else:
        logger.warning('No P-node type to invoke for %s' % pn_type)