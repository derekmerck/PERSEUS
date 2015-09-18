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

import sys
# Assume that duppy may be in PERSEUS/duppy
sys.path.append('duppy')
import logging
from SimpleDisplay import Stripchart
from PyroNode import PyroNode
from mutils import read_waveform, read_numerics
from SMSMessenger import SMSMessenger
import time
import os
import argparse
import yaml

# import Pyro4
# Pyro4.config.USE_MSG_WAITALL = False
# Pyro4.config.NS_HOST = "10.229.156.225"

__package__ = "PERSEUS"
__description__ = "Push Electronic Relay for Smart Alarms for End User Situational Awareness"
__url__ = "https://github.com/derekmerck/PERSEUS"
__author__ = 'Derek Merck'
__email__ = "derek_merck@brown.edu"
__license__ = "MIT"
__version_info__ = ('0', '2', '1')
__version__ = '.'.join(__version_info__)


def PERSEUSNode(pn_id, **kwargs):
    # Factory function
    if kwargs.get('type') == 'control':
        return ControlNode(pn_id=pn_id, **kwargs)
    elif kwargs.get('type') == 'listener':
        return ListenerNode(pn_id=pn_id, **kwargs)
    elif kwargs.get('type') == 'display':
        return DisplayNode(pn_id=pn_id, **kwargs)
    else:
        raise NotImplementedError

class ControlNode(PyroNode):
    # Acts as data broker and rule evaluator

    def __init__(self, **kwargs):
        super(ControlNode, self).__init__(**kwargs)
        self.messenger = SMSMessenger('derek@gmail.com', 'password')

    # Add a channel->variable set translator for each node (set of channels)
    # Add a rule-sieve to each variable set
    # Add rules to the rule-sieve


class ListenerNode(PyroNode):

    def next_numeric_value(self, *args):

        channel = args[0]

        t = float(self.times[channel][self.counters[channel]])
        n = self.values[channel][self.counters[channel]]

        # Don't yield faster than the clock
        if self.start_times[channel] < 0 or t < self.last_t[channel] - 1:
            self.start_times[channel] = time.time()
            self.t_offsets[channel] = t

        if (time.time() - self.start_times[channel]) < (t - self.t_offsets[channel]):
            return

        self.counters[channel] = self.counters[channel] + 1
        self.last_t[channel] = t
        # self.logger.debug("{0}:{1}".format(t,n))
        return t, n

    def next_waveform_value(self, *args):
        channel = args[0]

        t = float(self.times[channel][self.counters[channel]])
        y = float(self.values[channel][self.counters[channel]])

        # Don't yield faster than the clock
        if self.start_times[channel] < 0 or t < self.last_t[channel] - 1:
            self.start_times[channel] = time.time()
            self.t_offsets[channel] = t

        #self.logger.debug("{0}+{1}<{2}+{3}".format(time.time(), self.t_offsets[channel], self.start_times[channel], t))

        if (time.time() - self.start_times[channel]) < (t - self.t_offsets[channel]):
            #self.logger.debug('FAILED: {0}<{1}'.format((time.time() - self.start_times[channel]), (t - self.t_offsets[channel])))
            return

        #self.logger.debug('PASSED: {0}<{1}'.format((time.time() - self.start_times[channel]), (t - self.t_offsets[channel])))
        self.counters[channel] = self.counters[channel] + 1
        self.last_t[channel] = t
        return t, y

    def add_waveform_channel(self, channel, **kwargs):
        fn = kwargs.get('fn')
        if fn:
            self.logger.debug('Setting up fake waveform from file')
            self.times[channel], self.values[channel] = read_waveform(fn)
            if channel == "ecg":
                # Do some subsampling for display
                self.times[channel] = self.times[channel][::4]
                self.values[channel] = self.values[channel][::4]
            #self.logger.debug(self.times)
            self.start_times[channel] = -1
            self.t_offsets[channel] = -1
            self.counters[channel] = 0
            self.last_t[channel] = -1
            self.add_update_func(PyroNode.put_in_channel, self.next_waveform_value, channel, channel=(self.pn_id, channel))
        else:
            raise NotImplementedError

    def add_numeric_channel(self, channel, **kwargs):
        fn = kwargs.get('fn')
        if fn:
            self.logger.debug('Setting up fake numerics from file')
            self.times[channel], self.values[channel] = read_numerics(fn)
            self.start_times[channel] = -1
            self.t_offsets[channel] = -1
            self.counters[channel] = 0
            self.last_t[channel] = -1
            self.add_update_func(PyroNode.put_in_channel, self.next_numeric_value, channel, channel=(self.pn_id, channel))
        else:
            raise NotImplementedError

    def __init__(self, **kwargs):
        super(ListenerNode, self).__init__(**kwargs)
        self.times = {}

        self.values = {}
        self.counters = {}
        self.start_times = {}
        self.t_offsets = {}
        self.last_t = {}

        sim_data_dir = kwargs.get('sim_data_dir')
        if sim_data_dir:
            # Get the directory listing
            fns = os.listdir(sim_data_dir)

            for fn in fns:
                if fn.find('PLETH') > 0:
                    self.add_waveform_channel('pleth', fn=os.path.join(sim_data_dir, fn))
                elif fn.find('ECG') > 0:
                   self.add_waveform_channel('ecg', fn=os.path.join(sim_data_dir, fn))
                elif fn.find('numerics') > 0:
                    self.add_numeric_channel('numerics', fn=os.path.join(sim_data_dir, fn))


class DisplayNode(PyroNode):

    def add_channel(self, node, channel):
        self.add_update_func(PyroNode.get_from_channel, self.display.update, channel, channel=(node, channel))

    def __init__(self, **kwargs):
        super(DisplayNode, self).__init__(**kwargs)
        self.display = Stripchart()

        node = kwargs.get('node')
        if node:
            self.add_channel(node, 'pleth')
            self.add_channel(node, 'ecg')
            self.add_channel(node, 'numerics')


def test_perseus():
    control0 = ControlNode(pn_id='control0')
    control0.run()
    #
    # listener0 = ListenerNode(pn_id='listener0',
    #                          broker='control0',
    #                          sim_data_dir='samples/DEV-03 sample 1A  NORMAL-  NORMAL RHYTHM + GOOD NORMOXIC PLETH   (5min NSR + 100% SpO2)')
    #                          # sim_data_dir='samples/DEV-03 sample 1E  FALSE POSITIVE-  VFIB + GOOD NORMOXIC PLETH   (5min VF + 98% SpO2)')
    # listener0.run()

    # listener1 = ListenerNode(pn_id='listener1',
    #                          broker='control0',
    #                          sim_data_dir='samples/DEV-03 sample 1D  TRUE POSITIVE-  VTACH + GOOD NORMOXIC PLETH   (5min VT + 98% SpO2 [last half of tracing])')
    # listener1.run()

    display0 = DisplayNode(pn_id='display0', broker='control0', node='listener0')
    display0.run()

    # display1 = DisplayNode(pn_id='display1', broker='control0', node='listener1')
    # display1.run()

    logging.debug("Threads running.")

    PyroNode.daemon.requestLoop()


def parse_args():

    parser = argparse.ArgumentParser(description='PERSEUS Core')
    parser.add_argument('pn_id',
                        nargs='+',
                        metavar='node id')
    parser.add_argument('--config',
                        default='config.yaml')

    p = parser.parse_args()

    with open(p.config, 'r') as f:
        topology, rules, zones = yaml.load_all(f)

    return p, topology, rules, zones


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    p, topology, rules, zones = parse_args()

    for item in p.pn_id:
        node = PERSEUSNode(item, **topology[item])
        node.run()

    logging.debug("Threads running.")
    PyroNode.daemon.requestLoop()

