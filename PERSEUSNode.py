"""
PERSEUS Node

Dependencies: Pyro4, Numpy, matplotlib, PyYAML

See README.md for usage, notes, and license info.
"""

import sys
# Assume that duppy may be in PERSEUS/duppy or ../duppy
sys.path.extend(['duppy', '../duppy'])
import logging
from SimpleDisplay import Stripchart
from PyroNode import PyroNode
from mutils import read_waveform, read_numerics, read_alarms
from SMSMessenger import SMSMessenger
import time
import os
import numpy as np
from PERSEUSRule import ParseRules, TestRules

registry = {}


def getNode(pn_id):
    return registry.get(pn_id)


def PERSEUSNode(pn_id, **kwargs):
    # Factory function
    if kwargs.get('type') == 'control':
        node = ControlNode(pn_id=pn_id, **kwargs)
        registry[pn_id] = node
        return node
    elif kwargs.get('type') == 'listener':
        node = ListenerNode(pn_id=pn_id, **kwargs)
        registry[pn_id] = node
        return node
    elif kwargs.get('type') == 'display':
        node = DisplayNode(pn_id=pn_id, **kwargs)
        registry[pn_id] = node
        return node
    else:
        raise NotImplementedError


class ControlNode(PyroNode):
    # Acts as data broker and rule evaluator

    def __init__(self, **kwargs):
        super(ControlNode, self).__init__(**kwargs)
        self.messenger = None
        self.update_funcs.append([self.update, None, [], {}])
        self.rules = []
        self.active_alerts = []
        self.alert_expiry = 10  # in secs
        self.zones = None
        self.devices = None

    def setup_alerts(self, rule_config, zone_config):
        self.rules = ParseRules(rule_config)
        self.messenger = SMSMessenger(zone_config['sms_relay']['user'],
                                      zone_config['sms_relay']['pword'],
                                      zone_config['sms_relay']['name'])
        self.zones = zone_config['zones']
        self.devices = zone_config['devices']

    def issue_alert(self, alert):

        for zone, desc in self.zones.iteritems():
            if alert.source in desc['sources'] and alert.priority.name in desc['priorities']:
                for device in desc['devices']:
                    d = self.devices.get(device)
                    if d:
                        self.logger.debug("Sending to {0}: {1}".format(d['number'], alert.msg))
                        self.messenger.message( d['number'], d['carrier'], alert.msg )


    def test_rules(self, values, source=None):
        alert = TestRules(self.rules, values, source)
        if alert:
            return alert

    def dispatch_alert(self, alert):
        # Check and see if we have already dispatched this one

        for active_alert in self.active_alerts:
            if alert == active_alert:  # ie, same rule and source
                # self.logger.debug("{0}-{1}={2}".format(alert.t, active_alert.t, alert.t - active_alert.t))
                if (alert.t - active_alert.t) < self.alert_expiry:
                    # self.logger.debug("Caught {0}-{1}={2}".format(alert.t, active_alert.t, alert.t - active_alert.t))
                    # Supress this alert
                    return
                else:
                    # Replace the old alert with this one
                    self.active_alerts.remove(active_alert)

        # Issue the message
        self.issue_alert(alert)

        # Mark this alert as dispatched
        self.active_alerts.append(alert)


    def update(self, update_func=None, **kwargs):
        # Create value sets from channels on each active node
        node_values = {}
        for channel, value in self.pn_data.iteritems():
            if not value:
                continue
            if not node_values.get(channel[0]):
                node_values[channel[0]] = {}
            node_values[channel[0]][channel[1]] = value[1]

#        self.logger.debug(node_values)

        # Test each value set against the condition sets
        for node, values in node_values.iteritems():
            alert = self.test_rules(values, node)
            if alert:
                # self.logger.debug('Alert generated by {0} for {1}'.format(node, values))
                self.dispatch_alert(alert)

    def available_nodes(self):
        # Return a list of available nodes for remote monitors to select from
        pass


class ListenerNode(PyroNode):

    def next_value(self, *args):

        channel = args[0]

        t = float(self.times[channel][self.counters[channel]])
        v = self.values[channel][self.counters[channel]]

        if type(v) == np.float64:
            v = float(v)

        # Don't yield faster than the clock
        if self.start_times[channel] < 0 or t < self.last_t[channel] - 1:
            self.start_times[channel] = time.time()
            self.t_offsets[channel] = t
        if (time.time() - self.start_times[channel]) < (t - self.t_offsets[channel]):
            return

        self.counters[channel] += 1

        if self.counters[channel] >= len(self.times[channel]):
            # Reset the loop
            self.start_times[channel] = -1
            self.t_offsets[channel] = -1
            self.counters[channel] = 0
            self.last_t[channel] = -1

        self.last_t[channel] = t
        # self.logger.debug("{0}:{1}".format(t,n))
        return t, v

    def add_waveform_channel(self, channel, **kwargs):
        fn = kwargs.get('fn')
        if fn:
            self.logger.debug('Setting up fake waveform from file')
            self.times[channel], self.values[channel] = read_waveform(fn)
            if channel == "ecg":
                # Do some subsampling for display
                self.times[channel] = self.times[channel][::4]
                self.values[channel] = self.values[channel][::4]
            self.start_times[channel] = -1
            self.t_offsets[channel] = -1
            self.counters[channel] = 0
            self.last_t[channel] = -1
            self.add_update_func(PyroNode.put_in_channel, self.next_value, channel, channel=(self.pn_id, channel))
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
            self.add_update_func(PyroNode.put_in_channel, self.next_value, channel, channel=(self.pn_id, channel))
        else:
            raise NotImplementedError

    def add_alarm_channel(self, channel, **kwargs):
        fn = kwargs.get('fn')
        if fn:
            self.logger.debug('Setting up fake alarms from file')
            self.times[channel], self.values[channel] = read_alarms(fn)
            self.start_times[channel] = -1
            self.t_offsets[channel] = -1
            self.counters[channel] = 0
            self.last_t[channel] = -1
            self.add_update_func(PyroNode.put_in_channel, self.next_value, channel, channel=(self.pn_id, channel))
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
                elif fn.find('alarm') > 0:
                    self.add_alarm_channel('alarms', fn=os.path.join(sim_data_dir, fn))


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
            self.add_channel(node, 'alarms')


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
