"""
SimpleStripchart

[Derek Merck](derek_merck@brown.edu)
Spring 2015

<https://github.com/derekmerck/PERSEUS>

Dependencies: Numpy, matplotlib

See README.md for usage, notes, and license info.
"""


from __future__ import division

import matplotlib
matplotlib.use('tkagg')  # Better for Mac

import logging
from matplotlib.lines import Line2D
import matplotlib.pyplot as plt
import time
import datetime


class Stripchart(object):

    class Datastrip(object):
        def __init__(self, name, ylim, ax):

            self.name = name
            self.ylim = ylim
            self.ax = ax

            self.ax.set_ylabel(self.name)
            self.ax.set_ylim(self.ylim)

            self.line = Line2D([0], [0])
            self.ax.add_line(self.line)
            self.t = None

        def update(self, sampled_data):

            channel = sampled_data.get(self.name)
            if not channel:
                logging.warn('Missing channel: {0}'.format(self.name))
                return
            samples = channel.get('samples')

            # logging.debug('Updating channel: {0} over range [{1},{2}] ({3} secs)'\
            #               .format(self.name, samples.t.min(), samples.t.max(),
            #                       samples.t.max() - samples.t.min()))
            # logging.debug(samples.y)
            # logging.debug(samples.t)

            self.t = samples.t
            self.line.set_data(samples.t, samples.y)

    def __init__(self, tstream, dur=7, redraw_interval=0.1):

        self.redraw_interval = redraw_interval
        self.dur = dur
        self.start_time = datetime.datetime.now()

        plt.ion()

        # Create two regions
        self.fig, self.ax = plt.subplots(2, 1, sharex=True)

        if len(tstream.sampled_data.keys())>0:
            self.name0 = tstream.sampled_data.keys()[0]
        else:
            self.name0 = None

        if len(tstream.sampled_data.keys())>1:
            self.name1 = tstream.sampled_data.keys()[1]
        else:
            self.name1 = None

        def range_of(name):
            if name.lower() == 'pleth': return (1000, 3000)
            elif name.lower() == 'ecg': return (-1.2, 1.2)
            else:
                logging.warn('Missing range for {0}'.format(name))
                return (-1,1)

        self.strip0 = Stripchart.Datastrip(self.name0, range_of(self.name0), self.ax[0])
        self.strip1 = Stripchart.Datastrip(self.name1, range_of(self.name1), self.ax[1])

        self.numerics = self.fig.text(0.79, 0.95,
                         'bpm:  \nspo2: ',
                         horizontalalignment='left',
                         verticalalignment='center',
                         transform=self.fig.transFigure)

        self.qos = self.fig.text(0.90, 0.95,
                         'qos:  \n: ',
                         horizontalalignment='left',
                         verticalalignment='top',
                         transform=self.fig.transFigure)

        self.alarms = self.fig.text(0.13, 0.95,
                         'source:  \ncode: ',
                         horizontalalignment='left',
                         verticalalignment='center',
                         transform=self.fig.transFigure)

        plt.show()

        self.tic = time.time()
        self.toc = self.tic

    def update_data(self, data, sampled_data):

        # Update waveform time and data samples
        self.strip0.update(sampled_data)
        self.strip1.update(sampled_data)

        hr = data.get('Heart Rate')
        spo2 = data.get('SpO2')
        qos = data.get('qos')

        alarms = data.get('alarms')
        alarm_source = None
        alarm_type = None
        if alarms:
            alarm_source = data.get('alarms').values()[0]['source']
            alarm_type = data.get('alarms').values()[0]['type']

        if hr:
            self.numerics.set_text("bpm:  {0}\nspo2: {1}".format(hr, spo2))
        if qos:
            self.qos.set_text("qos: {0}".format(qos))
        if alarm_source:
            self.alarms.set_text("source:  {0}\ncode: {1}".format(alarm_source, alarm_type))

    def redraw(self):
        self.toc = time.time()
        if (self.toc - self.tic) > self.redraw_interval:
            current_time = datetime.datetime.now()
            current_secs = (current_time - self.start_time).total_seconds()
            # self.ax[0].set_xlim(self.strip0.t[0] + 1, self.strip0.t[-1] - 1)
            self.ax[0].set_xlim(current_secs - self.dur + 1 - 4, current_secs - 1 - 4)
            self.fig.canvas.draw()
            self.tic = self.toc

