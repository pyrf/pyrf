#!/usr/bin/env python

from thinkrf.devices import WSA4000
from thinkrf.config import TriggerSettings

import sys
import time
import math

from numpy import fft, linspace

import sys, random
from PySide import QtGui, QtCore

REFRESH = 0.05

def logpower(i, q):
    return 20 * math.log10(math.sqrt((i*i) + (q*q)))

class WSA4000Connection(object):

    def __init__(self, host):
        # connect to wsa
        self.dut = WSA4000()
        self.dut.connect(host)

        # setup test conditions
        self.dut.request_read_perm()
        self.dut.ifgain(0)
        self.dut.freq(2450e6)
        self.dut.gain('high')
        self.dut.fshift(0)
        self.dut.decimation(0)
        trigger = TriggerSettings(
            trigtype="LEVEL",
            fstart=2400e6,
            fstop=2480e6,
            amplitude=-70)
        self.dut.trigger(trigger)

    def read_powdata(self):
        # capture 1 packet
        self.dut.capture(1024, 1)

        # read until I get 1 data packet
        while not self.dut.eof():
            pkt = self.dut.read()

            if pkt.is_data_packet():
                break

        # seperate data into i and q
        cdata = []
        for t in pkt.data:
            cdata.append( complex(t[0], t[1]) )

        # compute the fft of the complex data
        cfft = fft.fft(cdata)
        cfft = fft.fftshift(cfft)

        # compute power
        powdata = []
        for t in cfft:
            powdata.append(logpower(t.real, t.imag))
        return powdata


class Example(QtGui.QWidget):

    def __init__(self, powdata):
        super(Example, self).__init__()
        self.powdata = powdata

        self.initUI()

    def initUI(self):

        self.setWindowTitle('Points')
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Window, QtCore.Qt.black)
        self.setPalette(pal)
        self.show()

    def paintEvent(self, e):

        qp = QtGui.QPainter()
        qp.begin(self)
        self.drawLines(qp)
        qp.end()

    def drawLines(self, qp):

        qp.setPen(QtCore.Qt.green)
        size = self.size()

        prev_x = prev_y = None
        for x, y in zip(
                linspace(0, size.width() - 1, len(self.powdata)),
                self.powdata):

            y = size.height() - 1 - (y / 200 * size.height())
            if prev_x is not None:
                qp.drawLine(prev_x, prev_y, x, y)
            prev_x, prev_y = x, y

def update_powdata():
    ex.powdata = conn.read_powdata()
    ex.update()

conn = WSA4000Connection(sys.argv[1])
app = QtGui.QApplication(sys.argv)
ex = Example(conn.read_powdata())
timer = QtCore.QTimer(ex)
timer.timeout.connect(update_powdata)
timer.start(REFRESH)
sys.exit(app.exec_())



