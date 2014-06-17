import util
import numpy as np
from pyrf.gui import colors
from pyrf.config import TriggerSettings, TRIGGER_TYPE_LEVEL, TRIGGER_TYPE_NONE
from pyrf.units import M

PLOT_YMIN = -160
PLOT_YMAX = 20

class PlotState(object):
    """
    Class to hold all the GUI's plot states
    """

    def __init__(self,
            device_properties,
            ):

        # plot paramaterss
        self.grid = False
        self.mhold = False
        self.mhold_fft = None
        self.block_mode = True
        self.peak = False
        self.freq_range = None
        self.enable_plot = True
        self.ref_level = PLOT_YMAX
        self.min_level = PLOT_YMIN
        self.device_properties = device_properties
        self.alt_colors = False