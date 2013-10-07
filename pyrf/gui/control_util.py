from PySide import QtCore
import util
import pyqtgraph as pg
from pyrf.config import TriggerSettings
import gui_config as gui_state
import constants
from pyrf.util import read_data_and_context

def _center_plot_view(layout):
    """
    move the view to the center of the current FFT displayed
    """
    layout._plot.center_view(layout.plot_state.center_freq, layout.plot_state.bandwidth)
    
def _select_center_freq(layout):
    """
    select the center freq for arrow control
    """
    layout.plot_state.freq_sel = 'CENT'
    util.select_center(layout)
    
def _select_bw(layout):
    """
    select the bw for arrow control
    """
    layout.plot_state.freq_sel = 'BW'
    util.select_bw(layout)

def _select_fstart(layout):
    """
    select the fstart for arrow control
    """
    layout.plot_state.freq_sel = 'FSTART'
    util.select_fstart(layout)
    
def _select_fstop(layout):
    """
    select the fstop for arrow control
    """
    layout.plot_state.freq_sel = 'FSTOP'
    util.select_fstop(layout)
    
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

    if layout.plot_state.enable_plot:
        layout._freq_plus.click()
        layout.plot_state.max_hold_fft = None

def _left_arrow_key(layout):
    """
    handle left arrow key action
    """
    if layout.plot_state.enable_plot:
        layout._freq_minus.click()
        layout.plot_state.max_hold_fft = None
        
def _trace_tab_change(layout):
    """
    change the selected trace
    """
    trace = layout._plot.traces[layout._trace_tab.currentIndex()]

    if trace.write:
        layout._trace_attr['write'].click()
    elif trace.max_hold:
        layout._trace_attr['max_hold'].click()
    elif trace.min_hold:
        layout._trace_attr['min_hold'].click()
    elif trace.blank:
        layout._trace_attr['blank'].click()
    
    if layout._plot.traces[layout._trace_tab.currentIndex()].store:
        state =  QtCore.Qt.CheckState.Checked
    else:
        state =  QtCore.Qt.CheckState.Unchecked
    layout._trace_attr['store'].setCheckState(state) 
    
    layout._trace_attr['ref'].setText(str(trace.ref))
    
def _max_hold(layout):
    """
    disable/enable max hold on a trace
    """
    trace = layout._plot.traces[layout._trace_tab.currentIndex()]
    trace.write = False
    trace.max_hold = True
    trace.min_hold = False
    trace.blank = False
    layout._trace_attr['store'].setEnabled(True)
    util.update_marker_traces(layout._marker_trace, layout._plot.traces)    
    
def _min_hold(layout):
    """
    disable/enable min hold on a trace
    """
    trace = layout._plot.traces[layout._trace_tab.currentIndex()]
    trace.write = False
    trace.max_hold = False
    trace.min_hold = True
    trace.blank = False
    layout._trace_attr['store'].setEnabled(True)   
    util.update_marker_traces(layout._marker_trace, layout._plot.traces) 
    
def _trace_write(layout):
    """
    disable/enable running FFT mode the selected trace
    """        
    trace = layout._plot.traces[layout._trace_tab.currentIndex()]
    trace.write = True
    trace.max_hold = False
    trace.min_hold = False
    trace.blank = False
    layout._trace_attr['store'].setEnabled(True)
    
    if layout._marker_trace is not None:
        util.update_marker_traces(layout._marker_trace, layout._plot.traces) 
    
def _blank_trace(layout):
    """
    disable/enable the selected trace
    """
    if layout._trace_attr['store'].checkState() is QtCore.Qt.CheckState.Checked:
        layout._trace_attr['store'].click()
    
    layout._trace_attr['store'].setEnabled(False)
    trace = layout._plot.traces[layout._trace_tab.currentIndex()]
    trace.write = False
    trace.max_hold = False
    trace.min_hold = False
    trace.blank = True
    trace.curve.clear()
    trace.data = None

    
    for marker in layout._plot.markers:
        if marker.enabled and marker.trace_index ==  layout._trace_tab.currentIndex():
            marker.disable(layout._plot)
            layout._marker_check.click() 
    util.update_marker_traces(layout._marker_trace, layout._plot.traces) 
    
def _store_trace(layout):
    """
    store the current trace's data
    """
    if layout._trace_attr['store'].checkState() is QtCore.Qt.CheckState.Checked:
        layout._plot.traces[layout._trace_tab.currentIndex()].store = True
    else:
        layout._plot.traces[layout._trace_tab.currentIndex()].store = False
        
def _ref_trace(layout):
    """
    adjust the reference level
    """

    trace = layout._plot.traces[layout._trace_tab.currentIndex()]
    try:
        ref = int(layout._trace_attr['ref'].text()) 
    except ValueError:
        return
    trace = layout._plot.traces[layout._trace_tab.currentIndex()]
    trace.ref = ref

def _marker_control(layout):
    """
    disable/enable marker
    """

    if layout._marker_check.checkState() is QtCore.Qt.CheckState.Checked:
        
        layout._marker_trace.setEnabled(True)
        if layout._marker_trace.currentIndex() < 0:
            layout._marker_trace.setCurrentIndex(0)
        layout._plot.markers[layout._marker_tab.currentIndex()].enable(layout._plot)
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
        layout._marker_trace.setCurrentIndex(marker.trace_index)
        layout._marker_trace.setEnabled(True)

        layout._marker_check.setCheckState(QtCore.Qt.CheckState.Checked)
    else:
        layout._marker_trace.setEnabled(False)

        layout._marker_check.setCheckState(QtCore.Qt.CheckState.Unchecked)
    marker.selected = True

    
    
def _find_peak(layout):
    """
    move the selected marker to the maximum point of the spectrum
    """
    marker = layout._plot.markers[layout._marker_tab.currentIndex()]
    
    if marker.enabled:
        trace = layout._plot.traces[marker.trace_index]
        peak_index = util.find_max_index(trace.data) 
        marker.data_index = peak_index


def _trigger_control(layout):
    """
    disable/enable triggers in the layout plot
    """

    if layout.plot_state.trig:
        layout.plot_state.disable_trig(layout)
           
    else:
        layout.plot_state.enable_trig(layout)
        _select_center_freq(layout)
        
hotkey_dict = {'1': _select_fstart,
                '2': _select_center_freq,
                '3': _select_bw,
                '4': _select_fstop,
                'UP KEY': _up_arrow_key, 
                'DOWN KEY': _down_arrow_key,
                'RIGHT KEY': _right_arrow_key,
                'LEFT KEY': _left_arrow_key,
                'C': _center_plot_view,
                'M': _marker_control,
                'P': _find_peak,
                'T': _trigger_control
                } 
                
arrow_dict = {'32': 'SPACE', 
                '16777235': 'UP KEY', 
                '16777237': 'DOWN KEY',
                '16777234': 'LEFT KEY', 
                '16777236': 'RIGHT KEY'}


