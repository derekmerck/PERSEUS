from __future__ import print_function

__author__ = 'Derek Merck'
__version_info__ = ('0', '1', '0')
__version__ = '.'.join(__version_info__)

"""
PERSEUS Core, Spring 2015
Merck

Dependencies: Pyro4

Config-file-free usage:
    main$ python -m Pyro4.naming
    main$ ./PERSEUS.py --pid control0  --type control --devices '{"phone001": {"number": 4014445555, "carrier": "***REMOVED***"}}'
    main$ ./PERSEUS.py --pid display0  --type display --controller control0
    remote$ ./PERSEUS.py --pid listener0 --type listener --controller control0 --alert_device phone001

Usage with config file:
    main$ python -m Pyro4.naming
    main$ ./PERSEUS.py -p control0  -c config.yaml
    main$ ./PERSEUS.py -p display0  -c config.yaml
    remote$ ./PERSEUS.py -p listener0 -c config.yaml

Where config.yaml looks like this:

    ---
    # Settings

    LOGGING_LEVEL: warning
    ENABLE_SMS: False
    SMS_USER: perseus_dispatch
    # ... etc.

    ---
    # Topology

    control0:
      type: control
      location: Main station

    display0:
      type: display
      location: Main station

    listener0:
      type: listener
      location: Remote patient monitor
      alert_device: phone001

    --
    # Alert Devices

    phone001:
      number: 4014445555
      carrier: ***REMOVED***

    ---

And the controller for a listener or display node is the _first_ control-type node listed
(with subsequent controls being used as backup)

Notes:

If the SMS Messenger is using gmail, this requires _either_ turning off app
security in gmail, or assigning a special password in the context of 2-step auth.

Acknowledgements:
- Messenger class cribbed in part from <https://github.com/CrakeNotSnowman/Python_Message>


Todo:
- console type?

"""

import os
import sys
import argparse
import logging
import yaml
import textwrap
from enum import Enum
import smtplib
import Pyro4
import numpy as np

if sys.version_info<(3,0):
    input = raw_input

# Check args
parser = argparse.ArgumentParser(description='PERSEUS Core')

parser.add_argument('-p', '--pid',
                    help='P-node id',
                    required=True)

parser.add_argument('-c', '--config',
                    help='Configuration file (default: config.yaml)',
                    default='config.yaml')

# If no config file is provided, _type_ at least is required and controller and location may also be specified
parser.add_argument('--type',       help='P-node type (server, monitor, display)')
parser.add_argument('--controller', help='Controller node name (default=control0)', default='control0')
parser.add_argument('--location',   help='P-node location',                         default='Unspecified')

args = parser.parse_args()

# Load config
package_directory = os.path.dirname(os.path.abspath(__file__))
fn = os.path.join(package_directory, args.config)
f = open(fn, 'r')
[settings, topology, devices] = yaml.load_all(f)

# Setup logging
logging.basicConfig()
logger = logging.getLogger('PERSEUS.Core')
logger.setLevel(settings['LOGGING_LEVEL'])

logger.info("SETTINGS=" + str(settings))
logger.info("TOPOLOGY=" + str(topology))
logger.info("DEVICES =" + str(devices))

# Setup consts
alerts = Enum('alerts', 'info ok moderate severe')

if sys.version_info < (3, 0):
    input = raw_input


class Pnode:

    def __init__(self):
        self.data = {}


class Control(Pnode):

    class Messenger:

        services = textwrap.dedent( '''
            # Sender relay servers
            gmail.com: 'smtp.gmail.com:587'

            ---
            # Receiver device gateways
            alltel:     message.alltel.com
            att:        txt.att.net
            boost:      myboostmobile.com
            ***REMOVED***:     messaging.sprintpcs.com
            sprint:     messaging.sprintpcs.com
            t-mobile:   tmomail.net
            uscellular: email.uscc.net
            ***REMOVED***:    vtext.com
            virgin:     vmobl.com
            ''' )
        relays, gateways = yaml.load_all(services)

        logger = logging.getLogger('PERSEUS.Messenger')
        logger.setLevel(settings['LOGGING_LEVEL'])

        def __init__(self):
            self.fromaddr = '%s <%s>' % (settings['SMS']['name'], settings['SMS']['email'])
            tmp = settings['SMS']['email'].split('@')
            self.relay_username = tmp[0]
            self.relay_server = self.relays[tmp[1]]
            self.relay_password = settings['SMS']['relay_password']

        def message(self, msg, did):
            number = devices[did]['number']
            carrier = devices[did]['carrier']
            toaddr = '%s@%s' % (number, self.gateways[carrier])
            self.send_message(self.relay_server, self.relay_username, self.relay_password, self.fromaddr, toaddr, msg)

        @staticmethod
        def send_message( relay_server, relay_username, relay_password, fromaddr, toaddr, msg ):
            logger.info( [relay_server, relay_username, relay_password, fromaddr, toaddr, msg] )
            if not settings['SMS']['ENABLE']: return
            server = smtplib.SMTP( relay_server )
            server.starttls()
            server.login( relay_username, relay_password )
            server.sendmail( fromaddr, toaddr, msg)
            server.quit()

    def __init__(self, pid):
        Pnode.__init__(self)
        self.messenger = Control.Messenger()
        self.pid = pid
        self._status = 'Ready'

        self.logger = logging.getLogger('PERSEUS.Control')
        self.logger.setLevel(settings['LOGGING_LEVEL'])

    def send_alert(self, pid):
        # An alert has been raised in a listener node
        did = topology[pid]['alert_device']
        self.messenger.message('There\'s an alert!', did)

    def status(self):
        return self._status

    def get(self, pid, key):
        self.logger.debug("{0} requested {1}, returning {2}.".format(pid, key, self.data[key]))
        return self.data[key]

    def put(self, pid, value, key=None):
        if key is None:
            key = pid
        self.data[key] = value
        self.logger.debug("{0} set {1} to {2}.".format(pid, key, self.data[key]))

class Listener(Pnode):

    def __init__(self, pid, controller):
        Pnode.__init__(self)
        self.pid = pid
        self.controller_id = controller
        self.control = Pyro4.Proxy("PYRONAME:perseus." + self.controller_id)

        # Init streams
        self.data['bogus'] = []

        self.logger = logging.getLogger('PERSEUS.Listener')
        self.logger.setLevel(settings['LOGGING_LEVEL'])

    def put(self, value):
        status = self.control.status()
        if status == 'Ready':
            self.control.put(self.pid, value)
            self.logger.debug("For key {0}, set {1}.".format(self.pid, value))

    def generate_data(self):
        data = np.random.rand(1)
        self.put(data)


class Display(Pnode):

    def __init__(self, pid, controller):
        Pnode.__init__(self)
        self.pid = pid
        self.controller_id = controller
        self.control = Pyro4.Proxy("PYRONAME:perseus." + self.controller_id)

        self.logger = logging.getLogger('PERSEUS.Display')
        self.logger.setLevel(settings['LOGGING_LEVEL'])

    def get(self, key):
        status = self.control.status()
        if status == 'Ready':
            data = self.control.get(self.pid, key)
            self.logger.debug("Requested key {0}, got {1}.".format(key, data))
            return data

    def stripchart(self):
        import Stripchart

        def emitter(p=0.03):
            """return a random value with probability p, else 0"""
            while True:
                v = np.random.rand(1)
                if v > p:
                    yield 0.
                else:
                    yield np.random.rand(1)

        fig, ax = Stripchart.plt.subplots()
        scope = Stripchart.Scope(ax)

        # pass a generator in "emitter" to produce data for the update func
        ani = Stripchart.animation.FuncAnimation(fig, scope.update, emitter, interval=10, blit=True)

        Stripchart.plt.show()



def start_control(pid):
    node = Control(pid)
    Pyro4.Daemon.serveSimple(
            {
                node: "perseus." + pid
            },
            ns=True)


def start_listener(pid, controller):
    node = Listener(pid, controller)
    node.put('Hello there!')

    # Main loop, continually generate data


def start_display(pid, controller):
    node = Display(pid, controller)
#    node.get('listener0')
    node.stripchart()


if __name__=="__main__":

    _pid = args.pid
    _type = topology[_pid]['type']
    _controller = topology[_pid].get('controller', None)

    if _type == 'control':
        start_control(_pid)
    elif _type == 'display':
        start_display(_pid, _controller)
    elif _type == 'listener':
        start_listener(_pid, _controller)
    else:
        logger.warning('No P-node type to invoke for %s' % _type)

