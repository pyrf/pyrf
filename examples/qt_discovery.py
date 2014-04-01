#!/usr/bin/env python

import sys

from PySide import QtGui
from pyrf.gui.discovery_widget import DiscoveryWidget

def main():
    app = QtGui.QApplication(sys.argv)
    ex = DiscoveryWidget()
    ex.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
