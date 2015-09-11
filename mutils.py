# METEOR Utilities

import numpy as np
import pylab as pl

# Read a numeric data set
def read_numerics(fn):
    data = np.fromfile(fn, 'uint16')
    data = np.reshape(data, (3, -1), 'F')

    # First 2 bytes are milliseconds
    times = (data[0, :] + data[1, :]*2^16)
    times = times.astype('float')/1000
    values = data[2, :].astype('float')

    return times, values


def test_read_numerics():
    fn = 'samples/RIHEDUrg CDev-03MP90_PLETH_20150907_125701.txt'
    times, values = read_numerics(fn)

    pl.plot(times, values)
    pl.show()


if __name__ == "__main__":
    test_read_numerics()
