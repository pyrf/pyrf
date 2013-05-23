from pyrf.config import TriggerSettings
import pyqtgraph as pg

LEVELED_TRIGGER_TYPE = 'LEVEL'
NONE_TRIGGER_TYPE = 'NONE'
PLOT_YMIN = -130
PLOT_YMAX = 20

def _select_center_freq(layout):
    layout.hor_key_con = 'FREQ'
    layout.marker_selected = False

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
        step = (layout.fstep * 1e6) * (layout.data_size / layout.bandwidth)
        layout.marker_ind = layout.marker_ind + step


def _left_arrow_key(layout):
    """
    handle left arrow key action
    """
    # TODO: use a dict
    if layout.hor_key_con == 'FREQ':
        layout._freq_minus.click()
    elif layout.hor_key_con == 'MARK':
        step = (layout.fstep * 1e6) * (layout.data_size / layout.bandwidth)
        layout.marker_ind = layout.marker_ind - step
        
def _center_plot_view(layout):
    """
    move the view to the center of the current FFT displayed
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

    # if marker is on and selected, turn off
    if layout.marker_selected == True:
        layout.marker_enable = False
        layout.marker_selected = False
        layout.hor_key_con = 'FREQ'
        layout.delta_enabled = False
        layout.delta_selected = False
        layout.plot_window.removeItem(layout.marker_point)
        layout.marker_point = None
        layout.marker_label.setText('')
    
    # if marker is on and not selected, select
    elif (layout.marker_selected == False and
           layout.marker_enable == True): 
        layout.marker_selected = True
        layout.hor_key_con = 'MARK'
    # if marker is off, turn on and select
    elif layout.marker_enable == False:
        
        if layout.marker_point != None:
            layout.plot_window.removeItem(layout.marker_point)
            layout.marker_point = None
        layout.marker_point = pg.CurvePoint(layout.fft_curve)
        layout.plot_window.addItem(layout.marker_point)  
        layout.arrow =  pg.ArrowItem(pos=(0, 0), angle=-90, tailLen = 10, headLen = 30)
        layout.arrow.setParentItem(layout.marker_point)
        layout.hor_key_con = 'MARK'
        layout.marker_ind = layout.data_size / 2
        layout.marker_enable = True
        layout.marker_selected = True
        layout.peak_enable = False


def _enable_peak(layout):
  
    layout.peak_enable = not(layout.peak_enable)
    
    if layout.peak_enable:
        if layout.marker_point != None:
            layout.plot_window.removeItem(layout.marker_point)
            layout.marker_point = None
        layout.marker_point = pg.CurvePoint(layout.fft_curve)
        layout.plot_window.addItem(layout.marker_point)  
        layout.arrow =  pg.ArrowItem(pos=(0, 0), angle=-90)
        layout.arrow.setParentItem(layout.marker_point)
        layout.marker_enable = False
        layout.marker_selected = False
    else:
        layout.plot_window.removeItem(layout.marker_point)
        layout.marker_label.setText('')
    
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
                'UP KEY': _up_arrow_key, 
                'DOWN KEY': _down_arrow_key,
                'RIGHT KEY': _right_arrow_key,
                'LEFT KEY': _left_arrow_key,
                'C': _center_plot_view,
                #'D': _delta_control,
                'G': _grid_control,
                'H': _max_hold_control,
                'M': _marker_control,
                'P': _enable_peak,
                'T': _trigger_control
                } 
                
arrow_dict = {'16777235': 'UP KEY', 
                '16777237': 'DOWN KEY',
                '16777234': 'LEFT KEY', 
                '16777236': 'RIGHT KEY'}


