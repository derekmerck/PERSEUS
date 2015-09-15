"""
PERSEUS SimpleDisplay

[Derek Merck](derek_merck@brown.edu)
[Leo Kobayashi](lkobayashi@lifespan.org)
Spring 2015

<https://github.com/derekmerck/PERSEUS>

Dependencies: Numpy, matplotlib

See README.md for usage, notes, and license info.
"""

import logging
# import matplotlib
# matplotlib.use('TkAgg')
from matplotlib.lines import Line2D
import matplotlib.pyplot as plt
import time
import numpy as np

# import statsmodels.api as sm
# lowess = sm.nonparametric.lowess

class Stripchart(object):

    class Datastrip(object):
        def __init__(self, name, numeric, ylim, ax, striplen=7):

            self.name = name
            self.numeric = numeric
            self.ylim = ylim
            self.ax = ax
            self.striplen = striplen

            self.ax.set_ylabel(self.name)
            self.ax.set_ylim(self.ylim)

            self.tdata = np.array([0])
            self.ydata = np.array([0])
            self.tic = time.time()

            self.line = Line2D(self.tdata, self.ydata)
#            self.line = Line2D(self.tdata, self.ydata, marker='o')
            self.ax.add_line(self.line)
            self.ax.set_xlim(0, 20)

        def update_wave(self, *args):
            if not args[0]: return

            t = args[0][0]
            y = args[0][1]

            self.tdata = np.append(self.tdata, t)
            self.ydata = np.append(self.ydata, y)

            # Truncate out old values that are off the strip
            for i in range(len(self.tdata)):
                if self.tdata[i] > self.tdata[-1] - self.striplen:
                    break

            self.tdata = self.tdata[i:]
            self.ydata = self.ydata[i:]

            self.line.set_data(self.tdata, self.ydata)

    def update_numeric(self, value):
        if not value: return
        self.text.set_text("bpm:  {0}\nspo2: {1}".format(value[0], value[1]))

    def __init__(self):

        self.logger = logging.getLogger('Stripchart')

        plt.ion()
        self.fig, self.ax = plt.subplots(2, 1, sharex=True)
        # self.fig, self.ax = plt.subplots(2, 1)

        self.pleth = Stripchart.Datastrip('PLETH', 'SpO^2', (900, 3150), self.ax[0])
        self.ecg   = Stripchart.Datastrip('ECG',   'BPM',   (8050, 8400), self.ax[1])

        plt.show()

        self.tic = time.time()
        self.interval = 0.08

        self.text = self.fig.text(0.79, 0.95,
                         'bpm:  \nspo2: ',
                         horizontalalignment='left',
                         verticalalignment='center',
                         transform=self.fig.transFigure)


    def update(self, *args):
        if not args[0]: return

        channel = args[1]

        if channel == "pleth":
            self.pleth.update_wave(args[0])
        elif channel == "ecg":
            self.ecg.update_wave(args[0])
        elif channel == "numerics":
            self.update_numeric(args[0][1])

        self.toc = time.time()
        if (self.toc - self.tic) > self.interval:

            self.ax[0].set_xlim(self.pleth.tdata[-1] - self.pleth.striplen, self.pleth.tdata[-1] - 0.1)

            self.fig.canvas.draw()
            self.tic = self.toc

        return

