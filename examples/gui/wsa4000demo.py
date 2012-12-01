#!/usr/bin/env python

from thinkrf.devices import WSA4000
from thinkrf.config import TriggerSettings

import sys
import time
import math

import sys

from gui import MainPanel
from PySide import QtGui, QtCore

REFRESH = 0.05

def setup_defaults(dut):
    dut.ifgain(0)
    dut.freq(2450e6)
    dut.gain('high')
    dut.fshift(0)
    dut.decimation(0)

dut = WSA4000()
dut.connect(sys.argv[1])
dut.request_read_perm()
if '--reset' in sys.argv[2:]:
    setup_defaults(dut)

app = QtGui.QApplication(sys.argv)
ex = MainPanel(dut)
timer = QtCore.QTimer(ex)
timer.timeout.connect(ex.update_screen)
timer.start(REFRESH)
sys.exit(app.exec_())



