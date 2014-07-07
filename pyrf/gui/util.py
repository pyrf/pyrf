import numpy as np
from PySide import QtGui, QtCore
from pyrf.gui import colors

def frequency_text(hz):
    """
    return hz as readable text in Hz, kHz, MHz or GHz
    """
    if hz < 1e3:
        return "%.3f Hz" % hz
    elif hz < 1e6:
        return "%.3f kHz" % (hz / 1e3)
    elif hz < 1e9:
        return "%.3f MHz" % (hz / 1e6)
    return "%.3f GHz" % (hz / 1e9)

def find_nearest_index(value, array):
    """
    returns the index in the array of the nearest value      
    """
    idx = (np.abs(array-value)).argmin()
    return idx
    
def change_item_color(item, textColor, backgroundColor):
    """
    changes the color of the specified item with the specified text color/background color 
    """
    item.setStyleSheet("QPushButton{Background-color: %s; color: %s; } QToolButton{color: Black}" % (textColor, backgroundColor)) 


def clear_layout(layout):
    """
    Clear all the widgets from a layout
    """
    if layout is None:
        return
    while layout.count():
        layout.removeItem(layout.takeAt(0))

def hide_layout(layout):
    """
    Hide all widgets in a layout
    """
    while layout.count():
        w = layout.takeAt(0).widget()
        if w:
            w.hide()
