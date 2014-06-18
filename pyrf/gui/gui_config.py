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
        self.freq_range = None
        self.ref_level = PLOT_YMAX
        self.min_level = PLOT_YMIN
        self.alt_colors = False