import sys
from PySide import QtGui, QtCore
from pyrf.gui.gui import MainWindow

REFRESH_CHARTS = 0.05

def main():
    app = QtGui.QApplication(sys.argv)
    ex = MainWindow()
    timer = QtCore.QTimer(ex)
    timer.timeout.connect(ex.update_charts)
    timer.start(REFRESH_CHARTS)
    sys.exit(app.exec_())


