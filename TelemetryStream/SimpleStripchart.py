"""
SimpleStripchart

[Derek Merck](derek_merck@brown.edu)
Spring 2015

<https://github.com/derekmerck/PERSEUS>

Dependencies: Numpy, matplotlib

See README.md for usage, notes, and license info.
"""

import logging
from matplotlib.lines import Line2D
import matplotlib.pyplot as plt
import time
import numpy as np
import datetime
import dateutil.parser

class Stripchart(object):

    class Datastrip(object):
        def __init__(self, name, ylim, ax, striplen=7):

            self.name = name
            self.ylim = ylim
            self.ax = ax
            self.striplen = striplen

            self.ax.set_ylabel(self.name)
            self.ax.set_ylim(self.ylim)

            self.tdata = np.array([0])
            self.ydata = np.array([0])

            self.line = Line2D(self.tdata, self.ydata)
            self.ax.add_line(self.line)

            self.start_time = datetime.datetime.now()

        def update(self, data):

            # Convert t into seconds since start
            t = (dateutil.parser.parse(data['timestamp']) - self.start_time).total_seconds()
            y = data[self.name]

            self.tdata = np.append(self.tdata, t)
            self.ydata = np.append(self.ydata, y)

            # Truncate out old values that are off the strip
            for i in range(len(self.tdata)):
                if (self.tdata[-1] - self.tdata[i]) < self.striplen:
                    break
            self.tdata = self.tdata[i:]
            self.ydata = self.ydata[i:]

            self.line.set_data(self.tdata, self.ydata)


    def __init__(self):

        self.logger = logging.getLogger(__name__)

        plt.ion()

        # Create two regions
        self.fig, self.ax = plt.subplots(2, 1, sharex=True)

        self.pleth = Stripchart.Datastrip('pleth', (-1.2, 1.2), self.ax[0])
        self.ecg   = Stripchart.Datastrip('ecg',   (-1.2, 1.2), self.ax[1])

        plt.show()

        self.tic = time.time()
        self.animation_interval = 0.1

        self.numerics = self.fig.text(0.79, 0.95,
                         'bpm:  \nspo2: ',
                         horizontalalignment='left',
                         verticalalignment='center',
                         transform=self.fig.transFigure)

        self.alarms = self.fig.text(0.13, 0.95,
                         'source:  \ncode: ',
                         horizontalalignment='left',
                         verticalalignment='center',
                         transform=self.fig.transFigure)

    def update(self, data):

        self.logger.info(data)

        # Update numerics
        self.numerics.set_text("bpm:  {0}\nspo2: {1}".format(data['bpm'], data['spo2']))

        # Update alarms
        self.alarms.set_text("source:  {0}\ncode: {1}".format(data['alarm_source'], data['alarm_type']))

        # Update waveform time and data samples
        self.pleth.update(data)
        self.ecg.update(data)

        # Animation update rate can be different than polling rate
        self.toc = time.time()
        if (self.toc - self.tic) > self.animation_interval:
            self.ax[0].set_xlim(self.pleth.tdata[-1] - self.pleth.striplen, self.pleth.tdata[-1] - 0.1)
            self.fig.canvas.draw()
            self.tic = self.toc

        return

