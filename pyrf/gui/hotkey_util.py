from pyrf.config import TriggerSettings
import pyqtgraph as pg

LEVELED_TRIGGER_TYPE = 'LEVEL'
NONE_TRIGGER_TYPE = 'NONE'
PLOT_YMIN = -130
PLOT_YMAX = 20

def _select_if_gain(layout):
    """
    select if gain in arrow up/down controls
    """
    layout.vert_key_con = 'IF'
    
def _select_rf_gain(layout):
    """
    select rf gain in arrow up/down controls
    """
    layout.vert_key_con = 'RF'
    
def _select_center_freq(layout):
    """
    select center frequency in arrow right/left controls
    """
    layout.vert_key_con = 'FREQ'

def _arrow_key_up(layout):
    """
    handle arrow key up action
    """
    if layout.vert_key_con == 'IF':
        if_gain = layout._ifgain_box.value() + 1
        layout._ifgain_box.setValue(if_gain) 
    
    elif layout.vert_key_con == 'RF':
        gain = layout._gain_box.currentIndex() + 1
        max_gain = layout._gain_box.count()
        if gain > max_gain - 1:
            gain = max_gain -1
        layout._gain_box.setCurrentIndex(gain)

def _arrow_key_down(layout):
    """
    handle arrow key down action
    """
    
    if layout.vert_key_con == 'IF':
        if_gain = layout._ifgain_box.value() - 1 
        layout._ifgain_box.setValue(if_gain) 
    
    elif layout.vert_key_con == 'RF':
       gain = layout._gain_box.currentIndex() - 1
       if gain < 0:
        gain = 0
       layout._gain_box.setCurrentIndex(gain)
       
def _right_arrow_key(layout):
    """
    handle arrow key right action
    """
    if layout.hor_key_con == 'FREQ':
        layout._freq_plus.click()

def _left_arrow_key(layout):
    """
    handle left arrow key action
    """
    if layout.hor_key_con == 'FREQ':
        layout._freq_minus.click()

def _center_plot_view(layout):
    """
    disable/enable plot grid in layout
    """
    layout.plot_window.setXRange(layout.center_freq - (layout.bandwidth/2),
                                    layout.center_freq + (layout.bandwidth / 2))
   
    layout.plot_window.setYRange(PLOT_YMIN, PLOT_YMAX)
    
def _grid_control(layout):
    """
    disable/enable plot grid in layout
    """
    layout.grid_enable = not(layout.grid_enable)
    layout.grid_control(layout.grid_enable)

def _max_hold_control(layout):
    """
    disable/enable max hold curve in the plot
    """
    layout.mhold_enable = not(layout.mhold_enable)
        
    if layout.mhold_enable == True:
        layout.mhold_curve = layout.plot_window.plot(pen = 'y')
    
    elif layout.mhold_enable == False:
        layout.plot_window.removeItem(layout.mhold_curve)
        layout.mhold_curve = None
        layout.mhold_fft = None
        
def _marker_control(layout):
    
    if layout.marker_selected == True:
        layout.marker_enable = False
        layout.marker_selected = False
        layout.delta_enabled = False
        layout.delta_selected = False
    
    elif (layout.marker_selected == False and
           layout.marker_enable == True): 
        layout.marker_selected = True
        
    elif layout.marker_enable == True:
        layout.marker_enable = False
    
def _trigger_control(layout):
    """
    disable/enable triggers in the layout plot
    """
    layout.trig_enable = not(layout.trig_enable)
    
    if layout.trig_enable == True:
        layout.trig_set = TriggerSettings(LEVELED_TRIGGER_TYPE,
                                                layout.center_freq - 10e6, 
                                                layout.center_freq + 10e6,-100) 
        layout.dut.trigger(layout.trig_set)
        layout.amptrig_line = pg.InfiniteLine(pos = -100, angle = 0, movable = True)
        layout.amptrig_line.sigPositionChangeFinished.connect(layout.update_trig)
        layout.freqtrig_lines = pg.LinearRegionItem([layout.center_freq - 10e6,layout.center_freq + 10e6])
        layout.freqtrig_lines.sigRegionChangeFinished.connect(layout.update_trig)
        layout.plot_window.addItem(layout.amptrig_line)
        layout.plot_window.addItem(layout.freqtrig_lines)
    
    elif layout.trig_enable == False:
        layout.plot_window.removeItem(layout.amptrig_line)
        layout.plot_window.removeItem(layout.freqtrig_lines)
        layout.amptrig_line = None
        layout.freqtrig_lines = None
        layout.trig_set = TriggerSettings(NONE_TRIGGER_TYPE,
                                                layout.center_freq - 10e6, 
                                                layout.center_freq + 10e6,-100) 
        layout.dut.trigger(layout.trig_set)
    
hotkey_dict = {'2': _select_center_freq,
                '4': _select_if_gain,
                '5': _select_rf_gain,
                'UP KEY': _arrow_key_up, 
                'DOWN KEY': _arrow_key_down,
                'RIGHT KEY': _right_arrow_key,
                'LEFT KEY': _left_arrow_key,
                'C': _center_plot_view,
                #'D': _delta_control,
                'G': _grid_control,
                'H': _max_hold_control,
                'M': _marker_control,
                'T': _trigger_control
                } 
                
arrow_dict = {'16777235': 'UP KEY', 
                '16777237': 'DOWN KEY',
                '16777234': 'LEFT KEY', 
                '16777236': 'RIGHT KEY'}


