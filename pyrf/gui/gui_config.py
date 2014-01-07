import util
import numpy as np
from pyrf.gui import colors
from pyrf.config import TriggerSettings, TRIGGER_TYPE_LEVEL, TRIGGER_TYPE_NONE
from pyrf.units import M

INIT_CENTER_FREQ = 2450 * M
INIT_BANDWIDTH = 500 * M
INIT_RBW = 244141

PLOT_YMIN = -160
PLOT_YMAX = 20

class PlotState(object):
    """
    Class to hold all the GUI's plot states
    """

    def __init__(self,
            device_properties,
            center_freq=INIT_CENTER_FREQ,
            bandwidth=INIT_BANDWIDTH,
            rbw=INIT_RBW,
            ):

        self.grid = False

        self.dev_set = {
            'attenuator': 1,
            'rfe_mode': 'ZIF'}
        self.mhold = False
        self.mhold_fft = None
        
        self.trig = False
        self.block_mode = True
        self.peak = False
 
        self.freq_range = None        
        self.center_freq = center_freq
        self.bandwidth = 100
        self.fstart = self.center_freq - self.bandwidth / 2
        self.fstop = self.center_freq + self.bandwidth / 2
        self.rbw = rbw
        self.enable_plot = True
        self.freq_sel = 'CENT'
        
        self.ref_level = PLOT_YMAX
        self.min_level = PLOT_YMIN 
        self.trig = False
        self.trig_set = TriggerSettings(TRIGGER_TYPE_NONE,
                                        self.center_freq + 10e6, 
                                        self.center_freq - 10e6,-100)
        self.device_properties = device_properties
    
    def disable_block_mode(self, layout):
        self.disable_triggers(layout)
        self.block_mode = False
        self.trig_set = TriggerSettings(TRIGGER_TYPE_NONE,
                                        self.center_freq + 10e6,
                                        self.center_freq - 10e6,-100)
        util.enable_freq_cont(layout)
        
    def enable_block_mode(self, layout):
        self.block_mode = True
        layout._cfreq.click()
        layout._bw_edit.setText('100.0')
        layout.update_freq()
        layout.update_freq_edit()
        util.disable_freq_cont(layout)

    def disable_triggers(self, layout): 
        layout._plot.amptrig_line.setValue(-100)
        layout._plot.remove_trigger()

        self.trig_set = TriggerSettings(TRIGGER_TYPE_NONE,
                                        self.center_freq + 10e6, 
                                        self.center_freq - 10e6,-100) 
        layout.update_trig()
        self.trig = False
    def enable_triggers(self, layout):
        self.trig = True
        self.trig_set = TriggerSettings(TRIGGER_TYPE_LEVEL,
                                        self.center_freq + 10e6, 
                                        self.center_freq - 10e6,-100)
        layout._plot.add_trigger(self.trig_set.fstart, self.trig_set.fstop)                                 
    
    def update_freq_range(self, start, stop, size):
        self.freq_range = np.linspace(start, stop, size)
        


    def update_freq_set(self,
                          fstart = None, 
                          fstop = None, 
                          fcenter = None, 
                          rbw = None, 
                          bw = None):
        prop = self.device_properties
        
        if fcenter != None:
            self.fstart = fcenter - (self.bandwidth / 2)
            if self.fstart < prop.MIN_TUNABLE:
                self.fstart = prop.MIN_TUNABLE
            self.fstop = fcenter + (self.bandwidth / 2)
            if self.fstop > prop.MAX_TUNABLE:
                self.fstop = prop.MAX_TUNABLE
            self.bandwidth = self.fstop - self.fstart
            self.center_freq = self.fstart + (self.bandwidth / 2)
            self.bin_size = int((self.bandwidth) / self.rbw)
            if self.bin_size < 1:
                self.bin_size = 1
        
        elif fstart != None:
            if fstart >= self.fstop - prop.TUNING_RESOLUTION:
                fstart = self.fstop - prop.TUNING_RESOLUTION
            self.fstart = fstart
            self.bandwidth = self.fstop - fstart
            self.center_freq = fstart + (self.bandwidth / 2)
            self.bin_size = int((self.bandwidth) / self.rbw)
            if self.bin_size < 1:
                self.bin_size = 1
                
        elif fstop != None:
            if fstop <= self.fstart + prop.TUNING_RESOLUTION:
                fstop = self.fstart + prop.TUNING_RESOLUTION
            self.fstop = fstop
            self.bandwidth = fstop - self.fstart
            self.center_freq = fstop - (self.bandwidth / 2)
            self.bin_size = int((self.bandwidth) / self.rbw)
            if self.bin_size < 1:
                self.bin_size = 1
                
        elif rbw != None:
            self.rbw = rbw * 1e3
            self.bin_size = int((self.bandwidth) / self.rbw)
            if self.bin_size < 1:
                self.bin_size = 1
        
        elif bw != None:
            if bw < prop.TUNING_RESOLUTION:
                bw = prop.TUNING_RESOLUTION
            self.fstart = (self.center_freq - (bw / 2))
            self.fstop = (self.center_freq + (bw / 2))
            if self.fstart < prop.MIN_TUNABLE:
                self.fstart = prop.MIN_TUNABLE
            if self.fstop > prop.MAX_TUNABLE:
                self.fstop = prop.MAX_TUNABLE
            self.bandwidth = self.fstop - self.fstart
            self.center_freq = self.fstart + (self.bandwidth / 2)
            self.bin_size = int((self.bandwidth) / self.rbw)
            if self.bin_size < 1:
                self.bin_size = 1
                
    def reset_freq_bounds(self):
            self.start_freq = None
            self.stop_freq = None

    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
