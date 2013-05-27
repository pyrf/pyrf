from pyrf.config import TriggerSettings
import pyqtgraph as pg

LEVELED_TRIGGER_TYPE = 'LEVEL'
NONE_TRIGGER_TYPE = 'NONE'
PLOT_YMIN = -130
PLOT_YMAX = 20

def _select_center_freq(layout):
    layout.hor_key_con = 'FREQ'
    layout.plot_state.marker_sel = False

def _up_arrow_key(layout):
    
    step = layout._fstep_box.currentIndex() + 1
    max_step = layout._fstep_box.count()
    if step > max_step - 1:
        step = max_step -1
    elif step < 0:
        step = 0
        layout._fstep_box.setCurrentIndex(step)
    layout._fstep_box.setCurrentIndex(step)

def _down_arrow_key(layout):

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
    # TODO: use a dict
    if layout.hor_key_con == 'FREQ':
        layout._freq_plus.click()
    elif layout.hor_key_con == 'MARK':
        step = (layout.fstep * 1e6) * (layout.points / layout.bandwidth)
        layout.marker_ind = layout.marker_ind + step

def _left_arrow_key(layout):
    """
    handle left arrow key action
    """
    # TODO: use a dict
    if layout.hor_key_con == 'FREQ':
        layout._freq_minus.click()
    elif layout.hor_key_con == 'MARK':
        step = (layout.fstep * 1e6) * (layout.points / layout.bandwidth)
        layout.marker_ind = layout.marker_ind - step
        
def _center_plot_view(layout):
    """
    move the view to the center of the current FFT displayed
    """
    layout._plot.center_view(layout.center_freq, layout.bandwidth)

def _update_grid(layout):
    """
    disable/enable plot grid in layout
    """
    layout.plot_state.grid = not(layout.plot_state.grid)
    layout._plot.grid(layout.plot_state.grid)

def _update_mhold(layout):
    """
    disable/enable max hold curve in the plot
    """
    layout.plot_state.mhold = not(layout.plot_state.mhold)
        
    if layout.plot_state.mhold:
        layout._plot.add_mhold()
        
    else:
        layout._plot.remove_mhold()
        
def _marker_control(layout):

    # if marker is on and selected, turn off
    if layout.plot_state.marker_sel:
        layout.plot_state.disable_marker()
        layout.hor_key_con = 'FREQ'
        layout._plot.remove_marker()

        layout.marker_label.setText('')
    
    # if marker is on and not selected, select
    elif not layout.plot_state.marker_sel and layout.plot_state.marker: 
        layout.plot_state.marker_sel = True
        layout.hor_key_con = 'MARK'
        
    # if marker is off, turn on and select
    elif not layout.plot_state.marker:
               
        layout._plot.add_marker()
        layout.hor_key_con = 'MARK'
        layout.marker_ind = layout.points / 2
        layout.plot_state.enable_marker()


def _find_peak(layout):
    if not layout.plot_state.marker:
        _marker_control(layout)
    layout.plot_state.peak = not(layout.plot_state.peak)
    
def _trigger_control(layout):
    """
    disable/enable triggers in the layout plot
    """
    layout.plot_state.trig = not(layout.plot_state.trig)
 
    if layout.plot_state.trig:
        _select_center_freq(layout)
        layout.trig_set = TriggerSettings(LEVELED_TRIGGER_TYPE,
                                                layout.center_freq - 10e6, 
                                                layout.center_freq + 10e6,-100) 
        layout.dut.trigger(layout.trig_set)
        layout._plot.add_trigger(layout.center_freq)
    
    else:
        layout._plot.remove_trigger()
        layout.trig_set = TriggerSettings(NONE_TRIGGER_TYPE,
                                                layout.center_freq - 10e6, 
                                                layout.center_freq + 10e6,-100) 
        layout.dut.trigger(layout.trig_set)
    
hotkey_dict = {'2': _select_center_freq,
                'UP KEY': _up_arrow_key, 
                'DOWN KEY': _down_arrow_key,
                'RIGHT KEY': _right_arrow_key,
                'LEFT KEY': _left_arrow_key,
                'C': _center_plot_view,
                #'D': _delta_control,
                'G': _update_grid,
                'H': _update_mhold,
                'M': _marker_control,
                'P': _find_peak,
                'T': _trigger_control
                } 
                
arrow_dict = {'16777235': 'UP KEY', 
                '16777237': 'DOWN KEY',
                '16777234': 'LEFT KEY', 
                '16777236': 'RIGHT KEY'}


