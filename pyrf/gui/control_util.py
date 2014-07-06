from PySide import QtGui, QtCore
import numpy as np
import util
from pyrf.units import M
from pyrf.gui.gui import MainPanel

hotkey_dict = { 'M': MainPanel._marker_control,
                'P': MainPanel._find_peak,
                } 
                
arrow_dict = {'32': 'SPACE', 
                '16777235': 'UP KEY', 
                '16777237': 'DOWN KEY',
                '16777234': 'LEFT KEY', 
                '16777236': 'RIGHT KEY'}


