"""
PERSEUS SimpleDisplay

[Derek Merck](derek_merck@brown.edu)
[Leo Kobayashi](lkobayashi@lifespan.org)
Spring 2015

<https://github.com/derekmerck/PERSEUS>Spring 2015

Dependencies: Numpy, matplotlib

Cribbed in part from matplotlib's [strip_chart example](http://matplotlib.org/1.4.0/examples/animation/strip_chart_demo.html)

See README.md for usage, notes, and license info.
"""

import numpy as np
import matplotlib
matplotlib.use('TkAgg')  # There is a problem with the default renderer under OSX
from matplotlib.lines import Line2D
import matplotlib.pyplot as plt
import matplotlib.animation as animation


class Stripchart:
    def __init__(self, emitter, maxt=2, dt=0.02):

        fig, ax = plt.subplots()

        self.ax = ax
        self.dt = dt
        self.maxt = maxt
        self.tdata = [0]
        self.ydata = [0]
        self.line = Line2D(self.tdata, self.ydata)
        self.ax.add_line(self.line)
        self.ax.set_ylim(-.1, 1.1)
        self.ax.set_xlim(0, self.maxt)

        self.emitter = emitter()

        # pass a generator in "emitter" to produce data for the update func
        self.ani = animation.FuncAnimation(fig, self.update, emitter, interval=10, blit=True)

        plt.show()


    def update(self, y):
        lastt = self.tdata[-1]
        if lastt > self.tdata[0] + self.maxt: # reset the arrays
            self.tdata = [self.tdata[-1]]
            self.ydata = [self.ydata[-1]]
            self.ax.set_xlim(self.tdata[0], self.tdata[0] + self.maxt)
            self.ax.figure.canvas.draw()

        t = self.tdata[-1] + self.dt
        self.tdata.append(t)
        self.ydata.append(y)
        self.line.set_data(self.tdata, self.ydata)
        return self.line,


if __name__ == "__main__":

    def emitter(p=0.03):
        """return a random value with probability p, else 0"""
        while True:
            v = np.random.rand(1)
            if v > p:
                yield 0.
            else:
                yield np.random.rand(1)

    Stripchart(emitter)
