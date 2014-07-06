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

def update_marker_traces(combo_box, traces):
    """
    update the available traces in a combo box   
    """

    index = combo_box.currentIndex()
    if index < 0:
        index = 0
    combo_box.clear()
    count = 0
    for (trace,(r,g,b)) in zip(traces, colors.TRACE_COLORS):
        if not trace.blank:
            combo_box.addItem(trace.name)
            color = QtGui.QColor()
            color.setRgb(r, g,b)
            pixmap = QtGui.QPixmap(10,10)
            pixmap.fill(color)
            icon = QtGui.QIcon(pixmap)
            combo_box.setItemIcon(count,icon)
            count += 1
            
    combo_box.setCurrentIndex(index)


def clear_layout(layout):
    """
    Clear all the widgets from a layout
    """
    if layout is None:
        return
    while layout.count():
        layout.removeItem(layout.takeAt(0))
