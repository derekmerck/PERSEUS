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
from matplotlib.lines import Line2D
import matplotlib.pyplot as plt
import time
import numpy as np


class Stripchart(object):

    class Datastrip(object):
        def __init__(self, ylim, ax, striplen=7):

            self.ylim = ylim
            self.ax = ax
            self.striplen = striplen

            self.ax.set_ylim(self.ylim)

            self.tdata = np.array([0])
            self.ydata = np.array([0])
            self.tic = time.time()

            self.line = Line2D(self.tdata, self.ydata)
#            self.line = Line2D(self.tdata, self.ydata, marker='o')
            self.ax.add_line(self.line)
            self.ax.set_xlim(0, 20)

        def update(self, *args):
            if not args[0]: return

            t = args[0][0]
            y = args[0][1]

            if t < self.tdata[-1] - 1:
                self.tdata = np.array([0])
                self.ydata = np.array([0])

            self.tdata = np.append(self.tdata, t)
            self.ydata = np.append(self.ydata, y)

            # Can't assume that t is monotonic
            s = np.argsort(self.tdata)
            self.tdata = self.tdata[s]
            self.ydata = self.ydata[s]

            # Truncate out old values that are off the strip
            for i in range(len(self.tdata)):
                if self.tdata[i] > self.tdata[-1] - self.striplen:
                    break

            self.tdata = self.tdata[i:]
            self.ydata = self.ydata[i:]

            self.ax.set_xlim(self.tdata[-1] - self.striplen, self.tdata[-1] - 0.1)

            self.line.set_data(self.tdata, self.ydata)


    def __init__(self):

        self.logger = logging.getLogger('Stripchart')

        plt.ion()
        self.fig, self.ax = plt.subplots(2, 1, sharex=True)
        #self.fig, self.ax = plt.subplots(2, 1)

        self.d0 = Stripchart.Datastrip((1000, 3000), self.ax[0])
        self.d1 = Stripchart.Datastrip((8100, 8300), self.ax[1])

        plt.show()

        self.tic = time.time()
        self.interval = 0.1


    def update(self, *args):

        channel = args[1]

        if channel == 0:
            self.d0.update(args[0])
        else:
            self.d1.update(args[0])

        self.toc = time.time()
        if (self.toc - self.tic) > self.interval:
            self.fig.canvas.draw()
            self.tic = self.toc

        return

        # t = args[0][0]
        # y = args[0][1]
        #
        # # TODO: Add throttle for t less than my update interval
        # #self.logger.debug(t)
        #
        # if t < self.tdata[-1] - 1:
        #     self.tdata = [0]
        #     self.ydata = [0]
        #
        # self.tdata.append(t)
        # self.ydata.append(y)
        #
        # # Truncate out old values that are off the strip
        # for i in range(len(self.tdata)):
        #     if self.tdata[i] > self.tdata[-1] - self.striplen:
        #         break
        #
        # self.tdata = self.tdata[i:]
        # self.ydata = self.ydata[i:]
        #
        # self.ax[channel].set_xlim(self.tdata[-1] - self.striplen, self.tdata[-1] + 0.1)
        #
        # self.line.set_data(self.tdata, self.ydata)
        # self.fig.canvas.draw()

