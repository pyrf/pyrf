from PySide import QtGui, QtCore
import numpy as np
import util
from pyrf.units import M

AXIS_OFFSET = 7

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
        layout.trace_group.trace_attr['store'].click()
    
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
    data_range = layout.xdata
    if window_freq[-1] < data_range[0] or window_freq[0] > data_range[-1]:
        return

    min_index, max_index = np.searchsorted(data_range, (window_freq[0], window_freq[-1]))

    trace = layout._plot.traces[marker.trace_index]
    peak_value = np.max(trace.data[min_index:max_index])
    marker.data_index = np.where(trace.data==peak_value)[0]

def _find_right_peak(layout):
    """
    move the selected marker to the next peak on the right
    """
    marker = layout._plot.markers[layout._marker_tab.currentIndex()]
    trace = layout._plot.traces[marker.trace_index]
    pow_data = trace.data
    # enable the marker if it is not already enabled
    if not marker.enabled:
        layout._marker_check.click()

    # retrieve the min/max x-axis of the current window
    window_freq = layout._plot.view_box.viewRange()[0]
    if marker.data_index is None:
        marker.data_index = len(pow_data) / 2
    data_range = layout.xdata[marker.data_index:-1]

    if len(data_range) == 0:
        return

    if window_freq[-1] < data_range[0] or window_freq[0] > data_range[-1]:
        return
    min_index, max_index = np.searchsorted(data_range, (window_freq[0], window_freq[-1])) + marker.data_index

    right_pow = pow_data[min_index:max_index]

    # calculate noise floor level by averaging the maximum 80% of the fft
    noise_floor = np.mean(np.sort(right_pow)[int(len(right_pow) * ( 0.8)):-1])

    peak_values = np.ma.masked_less(right_pow, noise_floor + layout.plot_state.peak_threshold).compressed()
    if len(peak_values) == 0:
        return
    marker.data_index = np.where(pow_data==(peak_values[1 if len(peak_values) > 1 else 0]))[0]

def _find_left_peak(layout):
    """
    move the selected marker to the next peak on the left
    """
    marker = layout._plot.markers[layout._marker_tab.currentIndex()]
    trace = layout._plot.traces[marker.trace_index]
    pow_data = trace.data
    # enable the marker if it is not already enabled
    if not marker.enabled:
        layout._marker_check.click()

    # retrieve the min/max x-axis of the current window
    window_freq = layout._plot.view_box.viewRange()[0]
    if marker.data_index is None:
        marker.data_index = len(pow_data) / 2
    data_range = layout.xdata[0:marker.data_index]

    if len(data_range) == 0:
        return
    if window_freq[-1] < data_range[0] or window_freq[0] > data_range[-1]:
        return

    min_index, max_index = np.searchsorted(data_range, (window_freq[0], window_freq[-1]))
    left_pow = pow_data[min_index:max_index]

    # calculate noise floor level by averaging the maximum 80% of the fft
    noise_floor = np.mean(np.sort(left_pow)[int(len(left_pow) * ( 0.8)):-1])

    peak_values = np.ma.masked_less(left_pow, noise_floor + layout.plot_state.peak_threshold).compressed()
    if len(peak_values) == 0:
        return
    marker.data_index = np.where(pow_data==(peak_values[-2 if len(peak_values) > 1 else -1]))[0]

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

hotkey_dict = { 'M': _marker_control,
                'P': _find_peak,
                } 
                
arrow_dict = {'32': 'SPACE', 
                '16777235': 'UP KEY', 
                '16777237': 'DOWN KEY',
                '16777234': 'LEFT KEY', 
                '16777236': 'RIGHT KEY'}


