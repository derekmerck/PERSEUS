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


class Stripchart:
    def __init__(self, interval=0.01, maxt=2, dt=0.02):

        self.logger = logging.getLogger('Stripchart')

        self.striplen = 5
        plt.ion()
        self.fig, self.ax = plt.subplots()
        self.tdata = [0]
        self.ydata = [0]
        self.line = Line2D(self.tdata, self.ydata, marker='o')
        self.ax.add_line(self.line)

        self.ax.set_ylim(1000, 3000)
        self.ax.set_xlim(0, 20)

        plt.show()


    def update(self, *args):

        t = args[0][0]
        y = args[0][1]

        # TODO: Add throttle for t less than my update interval

        if t < self.tdata[-1]:
            self.tdata = [0]
            self.ydata = [0]

        self.tdata.append(t)
        self.ydata.append(y)

        # Truncate out old values that are off the strip
        for i in range(len(self.tdata)):
            if self.tdata[i] > self.tdata[-1] - self.striplen:
                break

        self.tdata = self.tdata[i:]
        self.ydata = self.ydata[i:]

        self.ax.set_xlim(self.tdata[-1] - self.striplen, self.tdata[-1] + 0.1)

        self.line.set_data(self.tdata, self.ydata)
        self.fig.canvas.draw()

