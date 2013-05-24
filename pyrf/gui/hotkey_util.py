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
    layout.plot_window.setXRange(layout.center_freq - (layout.bandwidth/2),
                                    layout.center_freq + (layout.bandwidth / 2))
   
    layout.plot_window.setYRange(PLOT_YMIN, PLOT_YMAX)
    
def _update_grid(layout):
    """
    disable/enable plot grid in layout
    """
    layout.plot_state.grid = not(layout.plot_state.grid)
    layout.update_grid()

def _update_mhold(layout):
    """
    disable/enable max hold curve in the plot
    """
    layout.plot_state.mhold = not(layout.plot_state.mhold)
        
    if layout.plot_state.mhold:
        layout.mhold_curve = layout.plot_window.plot(pen = 'y')
    
    else:
        layout.plot_window.removeItem(layout.mhold_curve)
        layout.mhold_curve = None
        layout.mhold_fft = None
        
def _marker_control(layout):

    # if marker is on and selected, turn off
    if layout.plot_state.marker_sel:
        layout.plot_state.marker = False
        layout.plot_state.marker_sel= False
        layout.hor_key_con = 'FREQ'
        layout.delta_enabled = False
        layout.delta_selected = False
        layout.plot_window.removeItem(layout.marker_point)
        layout.marker_point = None
        layout.marker_label.setText('')
    
    # if marker is on and not selected, select
    elif layout.plot_state.marker_sel == False and layout.plot_state.marker: 
        layout.layout.plot_state.marker_sel = True
        layout.hor_key_con = 'MARK'
        
    # if marker is off, turn on and select
    elif not layout.plot_state.marker:
        
        if layout.marker_point != None:
            layout.plot_window.removeItem(layout.marker_point)
            layout.marker_point = None
        layout.marker_point = pg.CurvePoint(layout.fft_curve)
        layout.plot_window.addItem(layout.marker_point)  
        layout.arrow =  pg.ArrowItem(pos=(0, 0), angle=-90, tailLen = 10, headLen = 30)
        layout.arrow.setParentItem(layout.marker_point)
        layout.hor_key_con = 'MARK'
        layout.marker_ind = layout.points / 2
        layout.plot_state.marker = True
        layout.plot_state.marker_sel = True
        layout.peak_enable = False



def _enable_peak(layout):
  
    layout.plot_state.peak = not(layout.plot_state.peak)
    
    if layout.plot_state.peak:
        if layout.marker_point != None:
            layout.plot_window.removeItem(layout.marker_point)
            layout.marker_point = None
        layout.marker_point = pg.CurvePoint(layout.fft_curve)
        layout.plot_window.addItem(layout.marker_point)  
        layout.arrow =  pg.ArrowItem(pos=(0, 0), angle=-90)
        layout.arrow.setParentItem(layout.marker_point)
        layout.plot_state.marker = False
        layout.plot_state.marker_sel = False
    else:
        layout.plot_window.removeItem(layout.marker_point)
        layout.marker_label.setText('')
    
def _trigger_control(layout):
    """
    disable/enable triggers in the layout plot
    """
    layout.plot_state.trig = not(layout.plot_state.trig)
 
    if layout.plot_state.trig:
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
    
    else:
        layout.plot_window.removeItem(layout.amptrig_line)
        layout.plot_window.removeItem(layout.freqtrig_lines)
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
                'P': _enable_peak,
                'T': _trigger_control
                } 
                
arrow_dict = {'16777235': 'UP KEY', 
                '16777237': 'DOWN KEY',
                '16777234': 'LEFT KEY', 
                '16777236': 'RIGHT KEY'}


