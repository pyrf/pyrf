import pyqtgraph as pg

class plot_state(object):
    
    """
    Class to hold all the GUI's plotitem states
    """

    def __init__(self):
        
        # grid state
        self.grid = True
        
        # max hold state
        self.mhold = False
        
        # trigger state
        self.trig = False

        # marker state
        self.marker = False
        self.marker_sel = False

        # peak enable/disable
        self.peak = False
        
        #delta enable/ disables
        self.delta = False
        self.delta_sel= False

    
    
    
