from pyrf.config import TriggerSettings
import pyqtgraph as pg
LEVELED_TRIGGER_TYPE = 'LEVEL'
NONE_TRIGGER_TYPE = 'NONE'
from hotkey_util import *

def frequency_text(hz):
    """
    return hz as readable text in Hz, kHz, MHz or GHz
    """
    if hz < 1e3:
        return "%.3f Hz" % hz
    elif hz < 1e6:
        return "%.3f kHz" % (hz / 1e3)
    elif hz < 1e9:
        return "%.3f MHz" % (hz / 1e6)
    return "%.3f GHz" % (hz / 1e9)
    
def hotkey_util(layout, key_pressed):
    """
    modify elements in the gui layout based on which key was pressed
    """
    
    key_pressed = key_pressed.upper()

    # 'g' enables/disables plot grid
    if key_pressed == 'G':
      hotkey_dict['G'](layout)
      

    # 'h' enables/disables max hold curve
    if key_pressed == 'h' or key_pressed == 'H':
        
        layout.mhold_enable = not(layout.mhold_enable)
        
        if layout.mhold_enable == True:
            layout.mhold_curve = layout.plot_window.plot(pen = 'y')
        
        elif layout.mhold_enable == False:
            layout.plot_window.removeItem(layout.mhold_curve)
            layout.mhold_curve = None
            layout.mhold_fft = None
     
     # 't' enables/disables trigger lines
    if key_pressed == 't' or key_pressed == 'T':
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

