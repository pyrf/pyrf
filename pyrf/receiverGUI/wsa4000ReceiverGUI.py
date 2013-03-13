import sys
from PySide import QtGui
from pyrf.receiverGUI.gui import MainWindow

import qt4reactor

def main():
    app = QtGui.QApplication(sys.argv)
    qt4reactor.install() # requires QApplication to exist
    ex = MainWindow() # requires qt4reactor to be installed
    #late import because installReactor is being used
    from twisted.internet import reactor
    reactor.run()



