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

        self.grid = False

        self.mhold = False
        self.mhold_fft = None

        self.trig = False
        self.block_mode = True
        self.peak = False

        self.freq_range = None
        self.center_freq = device_properties.SPECA_DEFAULTS['center']
        self.bandwidth = device_properties.FULL_BW[
            device_properties.SPECA_DEFAULTS['mode']]
        self.fstart = self.center_freq - self.bandwidth / 2
        self.fstop = self.center_freq + self.bandwidth / 2
        self.rbw = device_properties.SPECA_DEFAULTS['rbw']
        self.enable_plot = True

        self.ref_level = PLOT_YMAX
        self.min_level = PLOT_YMIN
        self.trig = False
        self.trig_set = TriggerSettings(TRIGGER_TYPE_NONE,
                                        self.center_freq + 10e6,
                                        self.center_freq - 10e6,-100)
        self.device_properties = device_properties
        self.dev_set = {}

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

