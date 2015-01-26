import util
import numpy as np
from pyrf.gui import colors, labels


markerState = {}
for m in labels.MARKERS:
    markerState[m] =  { 'enabled': False,
                          'freq': None,
                          'power': -60,
                          'trace': labels.TRACES[0],
                          'hovering': False}

def init_trace_state():
    traceState = {}
    for t ,c  in zip(labels.TRACES, colors.TRACE_COLORS): 
        if t == labels.TRACES[0]:
            enable = True
        else:
            enable = False
        traceState[t] = {'enabled': enable,
                        'color': c}
    return traceState

plotState =  {'cont_cap_mode': True,
              'mouse_tune': True}


