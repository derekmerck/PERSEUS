
import logging
from SimpleDisplay import Stripchart
from PyroNode import PyroNode
from mutils import read_numerics
from SMSMessenger import SMSMessenger


class ControlNode(PyroNode):
    # Acts as data broker and rule evaluator

    def __init__(self, **kwargs):
        super(ControlNode, self).__init__(**kwargs)
        self.messenger = SMSMessenger('derek@gmail.com', 'password')

class ListenerNode(PyroNode):

    def next_value(self):
        self.counter = self.counter + 1
        return (float(self.times[self.counter]), float(self.values[self.counter]))

    def __init__(self, **kwargs):
        super(ListenerNode, self).__init__(**kwargs)
        fn = 'samples/RIHEDUrg CDev-03MP90_PLETH_20150907_125701.txt'
        self.times, self.values = read_numerics(fn)
        self.counter = 0

        self.add_update_func(PyroNode.put_in_channel, self.next_value, channel=(self.pn_id, 'test-1'))


class DisplayNode(PyroNode):

    def __init__(self, **kwargs):
        super(DisplayNode, self).__init__(**kwargs)
        display = Stripchart()
        self.add_update_func(PyroNode.get_from_channel, display.update, channel=('listener0', 'test-1'))


def test_perseus():
    control0 = ControlNode(pn_id='control0')
    control0.run()

    listener0 = ListenerNode(pn_id='listener0', broker='control0')
    listener0.run()

    listener1 = ListenerNode(pn_id='listener1', broker='control0')
    listener1.run()

    display0 = DisplayNode(pn_id='display0', broker='control0')
    display0.run()

    logging.debug("Threads running.")

    PyroNode.daemon.requestLoop()

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    test_perseus()