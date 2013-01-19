import sys
from PySide import QtGui
from gui import MainWindow

def main():
    app = QtGui.QApplication(sys.argv)
    ex = MainWindow()
    sys.exit(app.exec_())


