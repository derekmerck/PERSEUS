import sys
sys.path.append('duppy')

import logging
from SimpleDisplay import Stripchart
from PyroNode import PyroNode
from mutils import read_waveform, read_numerics
from SMSMessenger import SMSMessenger
import time


class ControlNode(PyroNode):
    # Acts as data broker and rule evaluator

    def __init__(self, **kwargs):
        super(ControlNode, self).__init__(**kwargs)
        self.messenger = SMSMessenger('derek@gmail.com', 'password')

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
        self.logger.debug("{0}:{1}".format(t,n))
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


class DisplayNode(PyroNode):

    def add_channel(self, node, channel):
        self.add_update_func(PyroNode.get_from_channel, self.display.update, channel, channel=(node, channel))

    def __init__(self, **kwargs):
        super(DisplayNode, self).__init__(**kwargs)
        self.display = Stripchart()


def test_perseus():
    control0 = ControlNode(pn_id='control0')
    control0.run()

    listener0 = ListenerNode(pn_id='listener0', broker='control0')
    fn = 'samples/RIHEDUrg CDev-03MP90_PLETH_20150907_125701.txt'
    listener0.add_waveform_channel('pleth', fn=fn)
    fn = 'samples/RIHEDUrg CDev-03MP90_ECG_I_20150907_125701.txt'
    listener0.add_waveform_channel('ecg', fn=fn)
    fn = 'samples/RIHEDUrg CDev-03MP90_numerics_20150907_125701.txt'
    listener0.add_numeric_channel('numerics', fn=fn)
    listener0.run()

    # listener1 = ListenerNode(pn_id='listener1', broker='control0', channel='ecg')
    # # fn = 'samples/DEV-03 sample 1D  TRUE POSITIVE-  VTACH + GOOD NORMOXIC PLETH   (5min VT + 98% SpO2 [last half of tracing])/RIHEDUrg CDev-03MP90_ECG_I_20150907_133838.txt'
    # fn = 'samples/RIHEDUrg CDev-03MP90_ECG_I_20150907_125701.txt'
    # listener1.add_waveform_channel('ecg', fn=fn)
    # listener1.run()

    display0 = DisplayNode(pn_id='display0', broker='control0')
    display0.add_channel('listener0', 'pleth')
    display0.add_channel('listener0', 'ecg')
    display0.add_channel('listener0', 'numerics')
    display0.run()

    logging.debug("Threads running.")

    PyroNode.daemon.requestLoop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    test_perseus()