
class plot_state(object):
    """
    Class to hold all the GUI's plotitem states
    """

    def __init__(self):
        self.grid = True
        self.mhold = False
        self.trig = False
        self.trig_sel = False
        self.marker = False
        self.marker_sel = False
        self.peak = False
        self.delta = False
        self.delta_sel= False
        self.mhold_fft = None
        self.center_freq = None
        self.bandwidth = None
        self.decimation_factor = None
        self.decimation_points = None
        self._pow = None
        self.marker_ind  = None
        self.delta_ind = None
        self.freq_range = None
        self.enable_plot = True
        self.points = 1024
        self.hor_key_con = 'CENT FREQ'
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

def select_fstart(layout):
    layout._fstart.setStyleSheet('background-color: rgb(255,84,0); color: white;')
    layout._cfreq.setStyleSheet("")
    layout._fstop.setStyleSheet("")

def select_center(layout):
    layout._cfreq.setStyleSheet('background-color: rgb(255,84,0); color: white')
    layout._fstart.setStyleSheet("")
    layout._fstop.setStyleSheet("")

def select_fstop(layout):
    layout._fstop.setStyleSheet('background-color: rgb(255,84,0); color: white')
    layout._fstart.setStyleSheet("")
    layout._cfreq.setStyleSheet("")

def change_item_color(item, textColor, backgroundColor, buttonStyle = None):
    if buttonStyle == None:
        item.setStyleSheet("Background-color: %s; color: %s; " % (textColor, backgroundColor)) 

    else:
        item.setStyleSheet("Background-color: %s; color: %s; border-style %s;border-width: 12px; border-radius: 2px; min-width: 5.8em; min-height: 1.5em" % (textColor, backgroundColor, buttonStyle)) 
    
    
    
