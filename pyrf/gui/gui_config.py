
class plot_state(object):
    
    """
    Class to hold all the GUI's plotitem states
    """

    def __init__(self):
        

        self.grid = True
        self.mhold = False
        self.trig = False
        self.marker = False
        self.marker_sel = False
        self.peak = False
        self.delta = False
        self.delta_sel= False
        
    def disable_marker(self):
        self.marker = False
        self.marker_sel = False
        
    def enable_marker(self):
        self.marker = True
        self.marker_sel = True
        
    def sel_marker(self):
        self.marker_sel = True
        


    
    
    
