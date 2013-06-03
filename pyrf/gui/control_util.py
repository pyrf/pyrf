from pyrf.config import TriggerSettings
import pyqtgraph as pg
import gui_state_util as gui_state
LEVELED_TRIGGER_TYPE = 'LEVEL'
NONE_TRIGGER_TYPE = 'NONE'
PLOT_YMIN = -130
PLOT_YMAX = 20
NORMAL_COLOR = 'NONE'
MARKER_COLOR =  'rgb(0,100,255)'
DELTA_COLOR = 'rgb(255,50,0)'
SELECTED_TEXT = 'Yellow'
NORMAL_TEXT = 'BLACK'      
def _center_plot_view(layout):
    """
    move the view to the center of the current FFT displayed
    """
    layout._plot.center_view(layout.center_freq, layout.bandwidth)
    
def _select_center_freq(layout):
    layout.hor_key_con = 'CENT FREQ'
    gui_state.select_center(layout)

def _select_fstart(layout):
    layout.hor_key_con = 'START FREQ'
    gui_state.select_fstart(layout)
    
def _select_fstop(layout):
    layout.hor_key_con = 'STOP FREQ'
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
    if layout.hor_key_con == 'CENT FREQ':
        if layout.enable_plot:
            layout._freq_plus.click()
            _center_plot_view(layout)


def _left_arrow_key(layout):
    """
    handle left arrow key action
    """
    # TODO: use a dict
    if layout.hor_key_con == 'CENT FREQ':
        if layout.enable_plot:
            layout._freq_minus.click()
            _center_plot_view(layout)
        
def _grid_control(layout):
    """
    disable/enable plot grid in layout
    """
    layout.plot_state.grid = not(layout.plot_state.grid)
    layout._plot.grid(layout.plot_state.grid)

def _mhold_control(layout):
    """
    disable/enable max hold curve in the plot
    """
    layout.plot_state.mhold = not(layout.plot_state.mhold)
        
    if layout.plot_state.mhold:
        gui_state.enable_mhold(layout)
        layout._plot.add_mhold()
        
    else:
        gui_state.disable_mhold(layout)
        layout._plot.remove_mhold()
        
def _marker_control(layout):
    """
    disable/enable marker
    """
    # if marker is on and selected, turn off
    if layout.plot_state.marker_sel:
        gui_state.change_item_color(layout._marker,  NORMAL_COLOR, NORMAL_TEXT)
        layout.plot_state.disable_marker()
        layout._plot.remove_marker()
        if layout.plot_state.delta:
            gui_state.change_item_color(layout._delta,  DELTA_COLOR, SELECTED_TEXT)
            layout.plot_state.sel_delta()

    
    # if marker is on and not selected, select
    elif not layout.plot_state.marker_sel and layout.plot_state.marker: 
        if layout.plot_state.delta_sel:
            gui_state.change_item_color(layout._delta,  DELTA_COLOR, NORMAL_TEXT)
        layout.plot_state.sel_marker()
        
        gui_state.change_item_color(layout._marker,  MARKER_COLOR, SELECTED_TEXT)

    # if marker is off, turn on and select
    elif not layout.plot_state.marker:
        gui_state.change_item_color(layout._marker,  MARKER_COLOR, SELECTED_TEXT)
        if layout.plot_state.delta_sel:
            gui_state.change_item_color(layout._delta,  DELTA_COLOR, NORMAL_TEXT)
        
        layout._plot.add_marker()
        layout.marker_ind = layout.points / 2
        layout.plot_state.enable_marker()
        layout.plot_state.sel_marker()
def _delta_control(layout):
    """
    disable/enable delta marker
    """

    # if delta is on and selected, turn off
    if layout.plot_state.delta_sel:
        gui_state.change_item_color(layout._delta, NORMAL_COLOR ,NORMAL_TEXT)
        layout.plot_state.disable_delta()
        layout._plot.remove_delta()
        if layout.plot_state.marker:
            layout.plot_state.sel_marker()
            gui_state.change_item_color(layout._marker,  MARKER_COLOR, SELECTED_TEXT)
    
    # if delta is on and not selected, select
    elif not layout.plot_state.delta_sel and layout.plot_state.delta: 
        gui_state.change_item_color(layout._delta, DELTA_COLOR, SELECTED_TEXT)
        if layout.plot_state.marker_sel:
            gui_state.change_item_color(layout._marker,  MARKER_COLOR, NORMAL_TEXT)
        layout.plot_state.sel_delta()

        
        
    # if delta is off, turn on and select
    elif not layout.plot_state.delta:
        gui_state.change_item_color(layout._delta, DELTA_COLOR, SELECTED_TEXT)
        if layout.plot_state.marker_sel:
            gui_state.change_item_color(layout._marker, MARKER_COLOR, NORMAL_TEXT)
        
        layout.plot_state.enable_delta() 
        layout.plot_state.sel_delta()        
        layout._plot.add_delta()


def _find_peak(layout):
    if not layout.plot_state.marker:
        _marker_control(layout)
    layout.plot_state.peak = not(layout.plot_state.peak)
def _enable_plot(layout):
    layout.enable_plot = not(layout.enable_plot)
    
def _trigger_control(layout):
    """
    disable/enable triggers in the layout plot
    """
    layout.plot_state.trig = not(layout.plot_state.trig)
 
    if layout.plot_state.trig:
        gui_state.change_item_color(layout._trigger,  'Green','Yellow')
        layout.trig_set = TriggerSettings(LEVELED_TRIGGER_TYPE,
                                                layout.center_freq - 10e6, 
                                                layout.center_freq + 10e6,-100) 
        layout.dut.trigger(layout.trig_set)
        layout._plot.add_trigger(layout.center_freq)
    
    else:
        gui_state.change_item_color(layout._trigger, 'None', 'Black',)
        layout._plot.remove_trigger()
        layout.trig_set = TriggerSettings(NONE_TRIGGER_TYPE,
                                                layout.center_freq - 10e6, 
                                                layout.center_freq + 10e6,-100) 
        layout.dut.trigger(layout.trig_set)
    
hotkey_dict = {'1': _select_fstart,
                '2': _select_center_freq,
                '3': _select_fstop,
                'UP KEY': _up_arrow_key, 
                'DOWN KEY': _down_arrow_key,
                'RIGHT KEY': _right_arrow_key,
                'LEFT KEY': _left_arrow_key,
                'C': _center_plot_view,
                'D': _delta_control,
                'G': _grid_control,
                'H': _mhold_control,
                'M': _marker_control,
                'P': _find_peak,
                'R': _enable_plot,
                'T': _trigger_control
                } 
                
arrow_dict = {'16777235': 'UP KEY', 
                '16777237': 'DOWN KEY',
                '16777234': 'LEFT KEY', 
                '16777236': 'RIGHT KEY'}


