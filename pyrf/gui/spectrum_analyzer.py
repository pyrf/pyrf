import sys
from PySide import QtGui
from pyrf.gui.gui import MainWindow

# pyinstaller + qt4reactor workaround:
sys.modules.pop('twisted.internet.reactor', None)

import qt4reactor
import logging

def main():
    name = None
    if '-v' in sys.argv:
        sys.argv.remove('-v')
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig()
    if '-d' in sys.argv:
        d_index = sys.argv.index('-d')
        name = sys.argv[d_index + 1]
        del sys.argv[d_index:d_index + 2]
    app = QtGui.QApplication(sys.argv)
    qt4reactor.install() # requires QApplication to exist
    # requires qt4reactor to be installed
    if name:
        ex = MainWindow(open(name, 'wb'))
    else:
        ex = MainWindow()
    # late import because installReactor is being used
    from twisted.internet import reactor
    reactor.run()


