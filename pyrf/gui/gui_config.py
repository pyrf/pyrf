
from pyrf.gui import colors
from pyrf.gui import labels
import util
from pyrf.gui import colors, labels
PERSISTENCE_GRADIENT = [(0.00, ( 0, 0, 0, 255)),
                                  (0.15, (  0,   0, 255, 255)),
                                  (0.33, (  0, 255, 255, 255)),
                                  (0.66, (255, 255,   0, 255)),
                                  (1.00, (255,   0,   0, 255))]

WATERFALL_GRADIENT = [(0, ( 0, 0, 0, 255)),
                                  (0.3, (  0,   0, 255, 255)),
                                  (0.55, (  0, 255, 255, 255)),
                                  (0.66, (255, 255,   0, 255)),
                                  (0.75, (255,   0,   0, 255))]
                        
plotState = {'cont_cap_mode': True,
              'mouse_tune': True,
              'horizontal_cursor': False,
              'horizontal_cursor_value': -100,
              'channel_power': False,
              'channel_power_region': (0.0, 0.0),
              'ref_level': 0.0,
              'db_div': 15.0,
              'persist_ticks': PERSISTENCE_GRADIENT,
              'waterfall_ticks': WATERFALL_GRADIENT
              }

windowOptions = {'frequency_control': True,
              'measurement_control': True,
              'capture_control': True,
              'amplitude_control': True,
              'device_control': False,
              'trace_control': True}

markerState = {}
for m in labels.MARKERS:
    markerState[m] =  { 'enabled': False,
                          'freq': 2450000000.0,
                          'power': -60.0,
                          'trace': labels.TRACES[0],
                          'delta': False,
                          'dtrace': labels.TRACES[0],
                          'dfreq': 2450000000.0,
                          'dpower': 0.0,
                          'hovering': False,
                          'tab': True,
                          'center': None,
                          'peak': None,
                          'peak_left': None,
                          'peak_right': None,
                          'unit': 'MHz'}

traceState = {}
for t ,c  in zip(labels.TRACES, colors.TRACE_COLORS): 
    if t == labels.TRACES[0]:
        mode = 'Live'
    else:
        mode = 'Off'
    traceState[t] = {'color': c,
                    'pause': False,
                    'mode': mode,
                    'clear': 'None',
                    'average': 5}

