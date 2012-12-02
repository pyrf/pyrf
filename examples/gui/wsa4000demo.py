#!/usr/bin/env python

import sys
from PySide import QtGui
from gui import MainWindow

app = QtGui.QApplication(sys.argv)
ex = MainWindow()
sys.exit(app.exec_())



