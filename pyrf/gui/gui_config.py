import constants
import numpy as np
class plot_state(object):
    """
    Class to hold all the GUI's plot states
    """

    def __init__(self):
        
        self.grid = False
        
        self.mhold = False
        self.mhold_fft = None
        self.trig = False
        
        self.marker = False
        self.marker_sel = False
        self.marker_ind = None
        
        self.delta = False
        self.delta_sel = False
        self.delta_ind = None
        self.peak = False
        
        self.pause_fft = None
        self.freq_range = None
        self.points = constants.STARTUP_POINTS
        
        self.center_freq = None
        self.bandwidth = None
        self.decimation_factor = None
        self.decimation_points = None
        self.start_freq = None
        self.stop_freq = None
        
        self.enable_plot = True
        
        self.freq_sel = 'CENT'
    
    
    def disable_marker(self):
        self.marker = False
        self.marker_sel = False
        
    def enable_marker(self):
        self.marker = True
        self.marker_sel = True
        
    def sel_marker(self):
        self.marker_sel = True
        self.delta_sel = False
        
    def disable_delta(self):
        self.delta = False
        self.delta_sel = False

    def enable_delta(self):
        self.delta = True
        self.delta_sel = True

    def sel_delta(self):
        self.delta_sel = True
        self.marker_sel = False
    
    def enable_trig(self):
        self.trig = True

    def disable_trig(self):
        self.trig = False
    
    def update_freq_range(self, start, stop, size):
        self.freq_range = np.linspace(start, stop, size)
        
    def update_freq(self,state):
        if state == 'CENT':
            self.start_freq = (self.center_freq) - (self.bandwidth / 2)
            self.stop_freq = (self.center_freq) + (self.bandwidth / 2)
        # TODO: UPDATE TO CHANGE FOR FSTART/FSTOP
    
    def reset_freq_bounds(self):
            self.start_freq = None
            self.stop_freq = None
def select_fstart(layout):
    layout._fstart.setStyleSheet('background-color: %s; color: white;' % constants.ORANGE)
    layout._cfreq.setStyleSheet("")
    layout._fstop.setStyleSheet("")

def select_center(layout):
    layout._cfreq.setStyleSheet('background-color: %s; color: white;' % constants.ORANGE)
    layout._fstart.setStyleSheet("")
    layout._fstop.setStyleSheet("")

def select_fstop(layout):
    layout._fstop.setStyleSheet('background-color: %s; color: white;' % constants.ORANGE)
    layout._fstart.setStyleSheet("")
    layout._cfreq.setStyleSheet("")

def change_item_color(item, textColor, backgroundColor, buttonStyle = None):
    if buttonStyle == None:
        item.setStyleSheet("Background-color: %s; color: %s; " % (textColor, backgroundColor)) 
    else:
        item.setStyleSheet("Background-color: %s; color: %s; border-style %s;border-width: 12px; border-radius: 2px; min-width: 5.8em; min-height: 1.5em" % (textColor, backgroundColor, buttonStyle)) 
    
    
    
