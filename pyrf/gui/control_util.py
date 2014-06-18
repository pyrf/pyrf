from PySide import QtGui, QtCore
import numpy as np
import util
import pyqtgraph as pg
from pyrf.config import TriggerSettings

from frequency_controls import FrequencyControls

AXIS_OFFSET = 7

def _up_arrow_key(layout):
    """
    increase the step size of the +/- buttons
    """
    step = layout._fstep_box.currentIndex() + 1
    max_step = layout._fstep_box.count()
    if step > max_step - 1:
        step = max_step -1
    elif step < 0:
        step = 0
        layout._fstep_box.setCurrentIndex(step)
    layout._fstep_box.setCurrentIndex(step)

def _down_arrow_key(layout):
    """
    decrease the step size of the +/- buttons
    """
    step = layout._fstep_box.currentIndex() - 1
    max_step = layout._fstep_box.count()
    if step > max_step - 1:
        step = max_step -1
    elif step < 0:
        step = 0
        layout._fstep_box.setCurrentIndex(step)
    layout._fstep_box.setCurrentIndex(step)

def _right_arrow_key(layout):
    """
    handle arrow key right action
    """
    layout._freq_group._freq_plus.click()

def _left_arrow_key(layout):
    """
    handle left arrow key action
    """
    layout._freq_group._freq_minus.click()
        
def _trace_tab_change(layout):
    """
    change the selected trace
    """
    trace = layout._plot.traces[layout.trace_group.trace_tab.currentIndex()]

    if trace.write:
        layout.trace_group.trace_attr['write'].click()
    elif trace.max_hold:
        layout.trace_group.trace_attr['max_hold'].click()
    elif trace.min_hold:
        layout.trace_group.trace_attr['min_hold'].click()
    elif trace.blank:
        layout.trace_group.trace_attr['blank'].click()
    
    if layout._plot.traces[layout.trace_group.trace_tab.currentIndex()].store:
        state =  QtCore.Qt.CheckState.Checked
    else:
        state =  QtCore.Qt.CheckState.Unchecked
    layout.trace_group.trace_attr['store'].setCheckState(state) 
        
def max_hold(layout):
    """
    disable/enable max hold on a trace
    """
    trace = layout._plot.traces[layout.trace_group.trace_tab.currentIndex()]
    trace.write = False
    trace.max_hold = True
    trace.min_hold = False
    trace.blank = False
    layout.trace_group.trace_attr['store'].setEnabled(True)
    util.update_marker_traces(layout._marker_trace, layout._plot.traces)    
    
def min_hold(layout):
    """
    disable/enable min hold on a trace
    """
    trace = layout._plot.traces[layout.trace_group.trace_tab.currentIndex()]
    trace.write = False
    trace.max_hold = False
    trace.min_hold = True
    trace.blank = False
    layout.trace_group.trace_attr['store'].setEnabled(True)   
    util.update_marker_traces(layout._marker_trace, layout._plot.traces) 
    
def trace_write(layout):
    """
    disable/enable running FFT mode the selected trace
    """        
    trace = layout._plot.traces[layout.trace_group.trace_tab.currentIndex()]
    trace.write = True
    trace.max_hold = False
    trace.min_hold = False
    trace.blank = False
    layout.trace_group.trace_attr['store'].setEnabled(True)
    
    if layout._marker_trace is not None:
        util.update_marker_traces(layout._marker_trace, layout._plot.traces) 
    
def blank_trace(layout):
    """
    disable/enable the selected trace
    """
    if layout.trace_group.trace_attr['store'].checkState() is QtCore.Qt.CheckState.Checked:
        layout._trace_attr['store'].click()
    
    layout.trace_group.trace_attr['store'].setEnabled(False)
    trace = layout._plot.traces[layout.trace_group.trace_tab.currentIndex()]
    trace.write = False
    trace.max_hold = False
    trace.min_hold = False
    trace.blank = True
    trace.clear()
    trace.data = None

    count = 0
    for marker in layout._plot.markers:
        if marker.enabled and marker.trace_index ==  layout.trace_group.trace_tab.currentIndex():
            marker.disable(layout._plot)
            if count == layout._marker_tab.currentIndex():
                layout._marker_check.click()
                layout._marker_tab.setCurrentIndex(0)
        count += 1
    util.update_marker_traces(layout._marker_trace, layout._plot.traces) 
    
def _store_trace(layout):
    """
    store the current trace's data
    """
    if layout.trace_group.trace_attr['store'].checkState() is QtCore.Qt.CheckState.Checked:
        layout._plot.traces[layout.trace_group.trace_tab.currentIndex()].store = True
    else:
        layout._plot.traces[layout.trace_group.trace_tab.currentIndex()].store = False
        
def _marker_control(layout):
    """
    disable/enable marker
    """
    marker = layout._plot.markers[layout._marker_tab.currentIndex()]
    if layout._marker_check.checkState() is QtCore.Qt.CheckState.Checked:
        
        layout._marker_trace.setEnabled(True)
        if layout._marker_trace.currentIndex() < 0:
            layout._marker_trace.setCurrentIndex(0)
        marker.trace_index = int(layout._marker_trace.currentText()) - 1
        marker.enable(layout._plot)
    else:
        layout._marker_trace.setEnabled(False)  
        layout._plot.markers[layout._marker_tab.currentIndex()].disable(layout._plot)

        layout.marker_labels[layout._marker_tab.currentIndex()].setText('')

def _marker_trace_control(layout):
    """
    change the trace that is currently associated with the marker
    """

    if layout._marker_trace is not None:
        marker = layout._plot.markers[layout._marker_tab.currentIndex()]
        if not layout._marker_trace.currentText() == '':
            marker.trace_index = int(layout._marker_trace.currentText()) - 1


def _marker_tab_change(layout):
    """
    change the current selected marker
    """
    
    for marker in layout._plot.markers:
        marker.selected = False
    marker = layout._plot.markers[layout._marker_tab.currentIndex()]
    if marker.enabled:
        if marker.trace_index == 2:
            if layout._marker_trace.count() == 2:
                index = 1
            else:
                index = 2
            layout._marker_trace.setCurrentIndex(index) 
        else:
            layout._marker_trace.setCurrentIndex(marker.trace_index) 
        layout._marker_trace.setEnabled(True)
        layout._marker_check.setCheckState(QtCore.Qt.CheckState.Checked)
    else:
        layout._marker_trace.setEnabled(False)
        
        layout._marker_trace.setCurrentIndex(marker.trace_index)
        layout._marker_check.setCheckState(QtCore.Qt.CheckState.Unchecked)
    marker.selected = True

def _find_peak(layout):
    """
    move the selected marker to the maximum point of the spectrum
    """
    marker = layout._plot.markers[layout._marker_tab.currentIndex()]

    # enable the marker if it is not already enabled
    if not marker.enabled:
        layout._marker_check.click()

    # retrieve the min/max x-axis of the current window
    window_freq = layout._plot.view_box.viewRange()[0]
    indexes_of_window = []

    for freq in layout.xdata:
        if freq < max(window_freq) and freq > min(window_freq):
            indexes_of_window.append(np.where(layout.xdata == freq)[0])

    if len(indexes_of_window) > 0:
        trace = layout._plot.traces[marker.trace_index]
        peak_index = util.find_max_index(trace.data[min(indexes_of_window):max(indexes_of_window)])
        marker.data_index = min(indexes_of_window) + peak_index

def _change_ref_level(layout):
    """
    change the ref level (maximum of the y-axis) of the fft plot
    """
    try:
        ref = float(layout._ref_level.text())
    except ValueError:
        layout.ref_level.setText(str(layout.plot_state.ref_level))
        return
    layout.plot_state.ref_level = ref
    
    _center_plot_view(layout)
    
def _change_min_level(layout):
    """
    change the min level of the fft plot
    """
    try:
        min = float(layout._min_level.text())
    except ValueError:
        layout.min_level.setText(str(layout.plot_state.min_level))
        return
    layout.plot_state.min_level = min
    _center_plot_view(layout)

hotkey_dict = {'1': FrequencyControls.select_fstart,
                '2': FrequencyControls.select_center,
                '3': FrequencyControls.select_bw,
                '4': FrequencyControls.select_fstop,
                'UP KEY': _up_arrow_key,
                'DOWN KEY': _down_arrow_key,
                'RIGHT KEY': _right_arrow_key,
                'LEFT KEY': _left_arrow_key,
                'M': _marker_control,
                'P': _find_peak,
                } 
                
arrow_dict = {'32': 'SPACE', 
                '16777235': 'UP KEY', 
                '16777237': 'DOWN KEY',
                '16777234': 'LEFT KEY', 
                '16777236': 'RIGHT KEY'}


