import sys
from PySide import QtGui
from pyrf.gui.gui import MainWindow

import qt4reactor
import logging
logging.basicConfig(level=logging.DEBUG)

def main():
    app = QtGui.QApplication(sys.argv)
    qt4reactor.install() # requires QApplication to exist
    ex = MainWindow() # requires qt4reactor to be installed
    # late import because installReactor is being used
    from twisted.internet import reactor
    reactor.run()



