import numpy as np
from PySide import QtGui, QtCore
import  control_util 
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
    
def hotkey_util(layout,event):
    """
    modify elements in the gui layout based on which key was pressed
    """
    if control_util.arrow_dict.has_key(str(event.key())):
        hotkey =  control_util.arrow_dict[str(event.key())]
    else:
        hotkey = str(event.text()).upper()
    if control_util.hotkey_dict.has_key(hotkey):
        control_util.hotkey_dict[hotkey](layout)
        
def find_max_index(array):
    """
    returns the maximum index of an array         
    """
    # keep track of max index
    index = 0
    
    array_size = len(array)
    
    max_value = 0
    for i in range(array_size):
        
        if i == 0:
            max_value = array[i]
            index = i
        elif array[i] > max_value:
            max_value = array[i]
            index = i
    return index

def find_nearest_index(value, array):
    """
    returns the index in the array of the nearest value      
    """
    idx = (np.abs(array-value)).argmin()
    return idx
    
def select_fstart(layout):
    """
    changes the color of the fstart button to orange and all others to default    
    """
    layout._fstart.setStyleSheet(
        'background-color: %s; color: white;' % colors.ORANGE)
    layout._cfreq.setStyleSheet("")
    layout._fstop.setStyleSheet("")
    layout._bw.setStyleSheet("")
    
def select_center(layout):
    """
    changes the color of the fcenter button to orange and all others to default    
    """
    layout._cfreq.setStyleSheet(
        'background-color: %s; color: white;' % colors.ORANGE)
    layout._fstart.setStyleSheet("")
    layout._fstop.setStyleSheet("")
    layout._bw.setStyleSheet("")
    
def select_bw(layout):
    """
    changes the color of the span button to orange and all others to default    
    """
    layout._bw.setStyleSheet(
        'background-color: %s; color: white;' % colors.ORANGE)
    layout._fstart.setStyleSheet("")
    layout._cfreq.setStyleSheet("")
    layout._fstop.setStyleSheet("")

def select_fstop(layout):
    """
    changes the color of the fstop button to orange and all others to default    
    """
    layout._fstop.setStyleSheet(
        'background-color: %s; color: white;' % colors.ORANGE)
    layout._fstart.setStyleSheet("")
    layout._cfreq.setStyleSheet("")
    layout._bw.setStyleSheet("")
    
def change_item_color(item, textColor, backgroundColor):
    """
    changes the color of the specified item with the specified text color/background color 
    """
    item.setStyleSheet("QPushButton{Background-color: %s; color: %s; } QToolButton{color: Black}" % (textColor, backgroundColor)) 

def enable_freq_cont(layout):
    layout._bw.setEnabled(True)
    layout._bw_edit.setEnabled(True)
    layout._fstart.setEnabled(True)
    layout._fstart_edit.setEnabled(True)
    layout._fstop.setEnabled(True)
    layout._fstop_edit.setEnabled(True)
    
def disable_freq_cont(layout):
    layout._bw.setEnabled(False)
    layout._bw_edit.setEnabled(False)
    layout._fstart.setEnabled(False)
    layout._fstart_edit.setEnabled(False)
    layout._fstop.setEnabled(False)
    layout._fstop_edit.setEnabled(False)

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

