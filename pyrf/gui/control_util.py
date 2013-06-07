from pyrf.config import TriggerSettings
import pyqtgraph as pg
import gui_config as gui_state
import constants
def _center_plot_view(layout):
    """
    move the view to the center of the current FFT displayed
    """
    layout._plot.center_view(layout.center_freq, layout.bandwidth)
    
def _center_plot_view(layout):
    """
    move the view to the center of the current FFT displayed
    """
    layout._plot.center_view(layout.plot_state.center_freq, layout.plot_state.bandwidth)
    
def _select_center_freq(layout):
    layout.freq_sel = 'CENT'
    gui_state.select_center(layout)

def _select_fstart(layout):
    layout.freq_sel = 'START'
    gui_state.select_fstart(layout)
    
def _select_fstop(layout):
    layout.freq_sel = 'STOP'
    gui_state.select_fstop(layout)
    
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
    if layout.plot_state.freq_sel == 'CENT':
        if layout.plot_state.enable_plot:
            layout._freq_plus.click()
        if layout.plot_state.mhold:
            layout.plot_state.mhold_fft = None
            

def _left_arrow_key(layout):
    """
    handle left arrow key action
    """
    # TODO: use a dict
    if layout.plot_state.freq_sel == 'CENT':
        if layout.plot_state.enable_plot:
            layout._freq_minus.click()
        if layout.plot_state.mhold:
            layout.plot_state.mhold_fft = None

def _grid_control(layout):
    """
    disable/enable plot grid in layout
    """
    
    layout.plot_state.grid = not(layout.plot_state.grid)
    layout._plot.grid(layout.plot_state.grid)
    if layout.plot_state.grid:
        gui_state.change_item_color(layout._grid,  constants.ORANGE, constants.WHITE)
    else:
        gui_state.change_item_color(layout._grid,  constants.NORMAL_COLOR, constants.BLACK)

def _mhold_control(layout):
    """
    disable/enable max hold curve in the plot
    """
    layout.plot_state.mhold = not(layout.plot_state.mhold)
        
    if layout.plot_state.mhold:
        gui_state.change_item_color(layout._mhold,  constants.ORANGE, constants.WHITE)
        layout._plot.add_mhold()
        
    else:  
        gui_state.change_item_color(layout._mhold,  constants.NORMAL_COLOR, constants.BLACK)
        layout._plot.remove_mhold()
        layout.plot_state.mhold_fft = None
        
def _marker_control(layout):
    """
    disable/enable marker
    """
    # if marker is on and selected, turn off
    if layout.plot_state.marker_sel:
        gui_state.change_item_color(layout._marker, constants.NORMAL_COLOR, constants.BLACK)
        layout.plot_state.disable_marker()
        layout._plot.remove_marker()
        if layout.plot_state.delta:
            gui_state.change_item_color(layout._delta,  constants.ORANGE, constants.WHITE, constants.PRESSED_BUTTON)
            layout.plot_state.sel_delta()

    
    # if marker is on and not selected, select
    elif not layout.plot_state.marker_sel and layout.plot_state.marker: 
        if layout.plot_state.delta_sel:
            gui_state.change_item_color(layout._delta,  constants.ORANGE, constants.WHITE)
        layout.plot_state.sel_marker()
        
        gui_state.change_item_color(layout._marker,  constants.ORANGE, constants.WHITE, constants.PRESSED_BUTTON)

    # if marker is off, turn on and select
    elif not layout.plot_state.marker:
        gui_state.change_item_color(layout._marker,  constants.ORANGE, constants.WHITE, constants.PRESSED_BUTTON)
        if layout.plot_state.delta_sel:
            gui_state.change_item_color(layout._delta,  constants.ORANGE, constants.WHITE)
        
        layout._plot.add_marker()
        layout.plot_state.enable_marker()
        
def _delta_control(layout):
    """
    disable/enable delta marker
    """

    # if delta is on and selected, turn off
    if layout.plot_state.delta_sel:
        gui_state.change_item_color(layout._delta, constants.NORMAL_COLOR ,constants.BLACK)
        layout.plot_state.disable_delta()
        layout._plot.remove_delta()
        if layout.plot_state.marker:
            layout.plot_state.sel_marker()
            gui_state.change_item_color(layout._marker, constants.ORANGE, constants.WHITE, constants.PRESSED_BUTTON)
    
    # if delta is on and not selected, select
    elif not layout.plot_state.delta_sel and layout.plot_state.delta: 
        gui_state.change_item_color(layout._delta, constants.ORANGE, constants.WHITE, constants.PRESSED_BUTTON)
        if layout.plot_state.marker_sel:
            gui_state.change_item_color(layout._marker, constants.ORANGE, constants.WHITE)
        layout.plot_state.sel_delta()

    # if delta is off, turn on and select
    elif not layout.plot_state.delta:
        gui_state.change_item_color(layout._delta, constants.ORANGE, constants.WHITE, constants.PRESSED_BUTTON)
        if layout.plot_state.marker_sel:
            gui_state.change_item_color(layout._marker, constants.ORANGE, constants.WHITE)
        
        layout.plot_state.enable_delta() 
        layout.plot_state.sel_delta()        
        layout._plot.add_delta()


def _find_peak(layout):
    if not layout.plot_state.marker:
        _marker_control(layout)
    layout.plot_state.peak = not(layout.plot_state.peak)
    
def _enable_plot(layout):
    
    layout.plot_state.enable_plot = not(layout.plot_state.enable_plot)
    if not layout.plot_state.enable_plot:
        gui_state.change_item_color(layout._pause,  constants.ORANGE, constants.WHITE)
    else:
        gui_state.change_item_color(layout._pause,  constants.NORMAL_COLOR, constants.BLACK)
        layout.dut.capture(layout.plot_state.points, 1)
def _trigger_control(layout):
    """
    disable/enable triggers in the layout plot
    """
    layout.plot_state.trig = not(layout.plot_state.trig)
 
    if layout.plot_state.trig:
        gui_state.change_item_color(layout._trigger, constants.ORANGE,constants.WHITE)
        layout.plot_state.trig_set = TriggerSettings(constants.LEVELED_TRIGGER_TYPE,
                                                layout.plot_state.center_freq - 10e6, 
                                                layout.plot_state.center_freq + 10e6,-100) 
        layout.dut.trigger(layout.plot_state.trig_set)
        layout._plot.add_trigger(layout.plot_state.center_freq)
    
    else:
        gui_state.change_item_color(layout._trigger, constants.NORMAL_COLOR, constants.BLACK)
        layout._plot.remove_trigger()
        layout.plot_state.trig_set = TriggerSettings(constants.NONE_TRIGGER_TYPE,
                                                layout.plot_state.center_freq - 10e6, 
                                                layout.plot_state.center_freq + 10e6,-100) 
        layout.dut.trigger(layout.plot_state.trig_set)
    
hotkey_dict = {'1': _select_fstart,
                '2': _select_center_freq,
                '3': _select_fstop,
                'UP KEY': _up_arrow_key, 
                'DOWN KEY': _down_arrow_key,
                'RIGHT KEY': _right_arrow_key,
                'LEFT KEY': _left_arrow_key,
                'C': _center_plot_view,
                'K': _delta_control,
                'G': _grid_control,
                'H': _mhold_control,
                'M': _marker_control,
                'P': _find_peak,
                'SPACE': _enable_plot,
                'T': _trigger_control
                } 
                
arrow_dict = {'32': 'SPACE', 
                '16777235': 'UP KEY', 
                '16777237': 'DOWN KEY',
                '16777234': 'LEFT KEY', 
                '16777236': 'RIGHT KEY'}


