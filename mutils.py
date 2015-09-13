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


message = '''
=========================================================================
Year	Month	Day	Hour	Minute	Second	Mili second
=========================================================================
2015	5	8	0	8	47	0
=========================================================================
Physio_id			State		Unit_code	Value
=========================================================================
NOM_PRESS_BLD_NONINV_SYS	UNAVAILABLE	mmHg		8388607.00
NOM_PRESS_BLD_NONINV_DIA	UNAVAILABLE	mmHg		8388607.00
NOM_PRESS_BLD_NONINV_MEAN	UNAVAILABLE	mmHg		8388607.00
NOM_PRESS_BLD_NONINV_PULS_RATE	UNAVAILABLE	bpm		8388607.00
NOM_ECG_CARD_BEAT_RATE		ERROR		bpm		60.00
NOM_RESP_RATE			ERROR		rpm		30.00
NOM_ECG_AMPL_ST_I		ERROR		mm		1677721.38
NOM_ECG_AMPL_ST_II		ERROR		mm		1677721.25
NOM_ECG_AMPL_ST_III		ERROR		mm		1677721.38
NOM_ECG_AMPL_ST_AVR		ERROR		mm		0.30
NOM_ECG_AMPL_ST_AVL		ERROR		mm		0.00
NOM_ECG_AMPL_ST_AVF		ERROR		mm		1677721.25
NOM_ECG_AMPL_ST_V		ERROR		mm		1677721.50
NOM_ECG_AMPL_ST_MCL		ERROR		mm		1677721.50
NOM_ECG_V_P_C_CNT		ERROR		bpm		0.00
NOM_PULS_OXIM_SAT_O2		INVALID	%		8388607.00
NOM_PLETH_PULS_RATE		ERROR		bpm		8388607.00
NOM_PULS_OXIM_PERF_REL		INVALID	-		8388607.00
=========================================================================
'''

#
# import astropy.io.ascii as asciitable
#
# timestamp = asciitable.read(message, header_start=0, data_start=1, data_end=2, comment='=+')
# data = asciitable.read(message, header_start=2, data_start=3, comment='=+')
# #
# # import timeit
# # print timeit.timeit(stmt='asciitable.read(message, header_start=2, data_start=3, comment=\'=+\')',
# #               setup='from __main__ import message\nimport astropy.io.ascii as asciitable', number=1000)
#
#
# print timestamp
#
# print timestamp['Year']
#
# #print data
