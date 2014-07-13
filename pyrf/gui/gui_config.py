import util
import numpy as np
from pyrf.gui import colors
from pyrf.config import TriggerSettings, TRIGGER_TYPE_LEVEL, TRIGGER_TYPE_NONE
from pyrf.units import M

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
        self.peak_threshold = 2
