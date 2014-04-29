from PySide import QtGui, QtCore
import util
import pyqtgraph as pg
from pyrf.config import TriggerSettings

AXIS_OFFSET = 7
IQ_PLOT_YMIN = {'ZIF': -1, 'HDR': 431000, 'SH': -1, 'SHN': -1, 'IQIN': -1, 'DD': -1}
IQ_PLOT_YMAX = {'ZIF': 1, 'HDR': 432800, 'SH': -1, 'SHN': -1, 'IQIN': 1, 'DD': 1}
def _center_plot_view(layout):
    """
    move the view to the center of the current FFT displayed
    """
    layout._plot.center_view(layout.plot_state.center_freq, layout.plot_state.bandwidth,
                            layout.plot_state.min_level, layout.plot_state.ref_level)
    layout._plot.iq_window.setYRange(IQ_PLOT_YMIN[layout.plot_state.dev_set['rfe_mode']],
                                    IQ_PLOT_YMAX[layout.plot_state.dev_set['rfe_mode']])

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
    trace.clear()
    trace.data = None

    count = 0
    for marker in layout._plot.markers:
        if marker.enabled and marker.trace_index ==  layout._trace_tab.currentIndex():
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
    if layout._trace_attr['store'].checkState() is QtCore.Qt.CheckState.Checked:
        layout._plot.traces[layout._trace_tab.currentIndex()].store = True
    else:
        layout._plot.traces[layout._trace_tab.currentIndex()].store = False
        
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
    
    if marker.enabled:
        trace = layout._plot.traces[marker.trace_index]
        peak_index = util.find_max_index(trace.data) 
        marker.data_index = peak_index

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

def _trigger_control(layout):
    """
    enable/disable triggers in the layout plot
    """

    if layout._dev_group._trigger.checkState() is QtCore.Qt.CheckState.Checked:
        layout.plot_state.enable_triggers(layout)
        layout.plot_state.enable_block_mode(layout)
        _select_center_freq(layout)
        layout.update_trig()
  
    else:
        if layout._iq_plot_checkbox.checkState() is QtCore.Qt.CheckState.Checked:
            layout.plot_state.disable_triggers(layout)
        else:
            layout.plot_state.disable_block_mode(layout)
        layout.update_trig()
        
def _update_rbw_values(layout):
    """
    update the RBW values depending on the current mode of operation
    """
    for index in range(layout._rbw_box.count()):
        layout._rbw_box.removeItem(0)
        
    if not layout.plot_state.dev_set['rfe_mode'] == 'HDR':
        layout._rbw_box.addItems([str(p) + ' KHz' for p in layout._points_values])
    
    else:
        layout._rbw_box.addItems([str(p) + ' Hz' for p in layout._hdr_points_values])
            
def _external_digitizer_mode(layout):
    """
    Disable all controls/plots that are irrelavant in external digitizer mode
    """

    # remove plots
    layout._plot_group.hide()
    layout._trace_group.hide()
    layout._plot_layout.hide()

    # resize window
    for x in range(8):
        layout._grid.setColumnMinimumWidth(x, 0)
    screen = QtGui.QDesktopWidget().screenGeometry()
    layout.setMinimumWidth(0)
    layout.setMinimumHeight(0)
    layout._main_window.setMinimumWidth(0)
    layout._main_window.setMinimumHeight(0)
    layout.resize(0,0)
    layout._main_window.resize(0,0)

    # remove sweep capture modes
    c = layout._dev_group._mode.count()
    layout._dev_group._mode.removeItem(c - 1)

    # remove all digitizer controls
    layout._dev_group._dec_box.hide()
    layout._dev_group._freq_shift_edit.hide()
    layout._dev_group._fshift_label.hide()
    layout._dev_group._fshift_unit.hide()

def _internal_digitizer_mode(layout):
    """
    Enable all controls/plots that are irrelavant in internal digitizer mode
    """

    # show plots
    layout._plot_group.show()
    layout._trace_group.show()
    layout._plot_layout.show()

    # resize window
    for x in range(8):
        layout._grid.setColumnMinimumWidth(x, 300)
    screen = QtGui.QDesktopWidget().screenGeometry()
    layout.setMinimumWidth(screen.width() * 0.7)
    layout.setMinimumHeight(screen.height() * 0.6)

    # add sweep commands
    layout._dev_group._mode.addItem('Sweep SH')

    # show digitizer controls
    layout._dev_group._dec_box.show()
    layout._dev_group._freq_shift_edit.show()
    layout._dev_group._fshift_label.show()
    layout._dev_group._fshift_unit.show()


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
                } 
                
arrow_dict = {'32': 'SPACE', 
                '16777235': 'UP KEY', 
                '16777237': 'DOWN KEY',
                '16777234': 'LEFT KEY', 
                '16777236': 'RIGHT KEY'}


