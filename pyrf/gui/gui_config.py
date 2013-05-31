
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
        print 'disabled marker'
        
    def enable_marker(self):
        self.marker = True
        self.marker_sel = True
        print 'enabled marker'
        
    def sel_marker(self):
        self.marker_sel = True
        self.delta_sel = False
        
    def disable_delta(self):
        self.delta = False
        self.delta_sel = False
        print 'disable d'
    def enable_delta(self):
        self.delta = True
        self.delta_sel = True
        print 'enabled d'
    def sel_delta(self):
        self.delta_sel = True
        self.marker_sel = False
        


    
    
    
