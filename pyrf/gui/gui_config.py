import util
import numpy as np
from pyrf.gui import colors, labels


marker_config = { 'enabled': False,
                  'freq': 0,
                  'power': -60,
                  'trace': 1,
                  'hovering': False}

markerState = {}
for m in labels.MARKERS:
    markerState[m] = marker_config

plotState =  {'cont_cap_mode': True,
              'mouse_tune': True}


