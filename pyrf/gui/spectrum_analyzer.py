import sys
from PySide import QtGui
from pyrf.gui.gui import MainWindow

# pyinstaller + qt4reactor workaround:
sys.modules.pop('twisted.internet.reactor', None)

import qt4reactor
import logging

def main():
    dut_address = None
    playback_filename = None
    developer_menu = False
    if '-p' in sys.argv:
        f_index = sys.argv.index('-p')
        playback_filename = sys.argv[f_index + 1]
        del sys.argv[f_index:f_index + 2]
    if '-v' in sys.argv:
        sys.argv.remove('-v')
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig()
    if '-d' in sys.argv:
        developer_menu = True
        sys.argv.remove('-d')
    if len(sys.argv) > 1:
        dut_address = sys.argv[1]
    app = QtGui.QApplication(sys.argv)
    qt4reactor.install() # requires QApplication to exist
    # requires qt4reactor to be installed
    ex = MainWindow(dut_address, playback_filename, developer_menu)
    # late import because installReactor is being used
    from twisted.internet import reactor
    reactor.run()

if __name__ == "__main__":
    main()
