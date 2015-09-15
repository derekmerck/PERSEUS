# METEOR Utilities
# Read waveform data (ecg, pleth), numerics (heart rate), alarms

import numpy as np
import pylab as pl
import logging
import time
import re

# Read a waveform data set
def read_waveform(fn):

    data = np.fromfile(fn, 'uint16')
    data = np.reshape(data, (3, -1), 'F')

    # First 2 bytes are milliseconds
    # Note that ^ is NOT ** in numpy-notation
    times = data[0, :].astype('uint32') + data[1, :].astype('uint32')*(2**16)
    times = times.astype('float')/1000.0
    values = data[2, :].astype('float')

    return times, values


def test_read_waveform():
    fn = 'samples/RIHEDUrg CDev-03MP90_PLETH_20150907_125701.txt'
    times, values = read_waveform(fn)

    pl.plot(times, values)
    pl.show()


class NumericsSample(object):

    def __init__(self, t):
        self.numerics = []
        self.t = t

    def add_numeric(self, n):
        self.numerics.append(n)

# This does not serialize nicely with Pyro4
#Numeric = namedtuple('Numeric', ['id', 'state', 'units', 'value'])

def parse_numerics_message( m ):

    def get_time_from_header( h ):
        time_fmt = '%Y %m %d %H %M %S %f'
        # logging.debug(' '.join(h.strip('\n').split()))
        ts = time.strptime(' '.join(h.strip('\n').split()), time_fmt)
        t = time.mktime(ts)
        return t

    def get_numeric_from_line( l ):
        # logging.debug(l)
        return l.split()
#        return Numeric( *l.split() )

    # Turn it into sections
    sep = re.compile(r'=+$', re.M)
    sections = sep.split(m)
    # logging.debug(sections)

    # First line is the timestamp
    if not sections[0]:
        # Incomplete message received
        return None, None
    t = get_time_from_header(sections[0])

    # section[1] is just the reader for the numerics

    bpm = 0
    spo2 = 0

    # Identify the numerics
    for l in sections[2].split('\n'):
        if not l:
            continue
        n = get_numeric_from_line(l)
        value = float(n[3])
        if n[0] == 'NOM_ECG_CARD_BEAT_RATE' and value < 300 and value > 0:
            bpm = value
        elif n[0] == 'NOM_PULS_OXIM_SAT_O2' and value < 101 and value > 0:
            spo2 = value

    return t, (bpm, spo2)


def read_numerics(fn):

    f = open(fn, 'rU')
    message_str = f.read()

    # Split the messages by ^Year ... \n =====...===\n
    h = re.compile(r'^Year.*\n=+$', re.M)
    messages = h.split(message_str)

    T = []
    N = []

    for m in messages:
        t, n = parse_numerics_message(m)
        if t:
            T.append(t)
            N.append(n)

    logging.debug(T)
    logging.debug(N)

    return T, N


def test_read_numerics():

    fn = 'samples/RIHEDUrg CDev-03MP90_numerics_20150907_125701.txt'
    read_numerics(fn)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    test_read_waveform()


