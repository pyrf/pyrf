from pyrf.gui import colors
from pyrf.gui import labels

traces = {}
for t, c  in zip(labels.TRACES, colors.TRACE_COLORS):
    traces['trace' + t] = c

PlotOptions = {'cont_cap_mode': True,
              'mouse_tune': True,
              'horizontal_cursor': False,
              'horizontal_cursor_value': -100,
              'mouse_tune': True,
              'ref_level': 0,
              'db_div': 15,
              'traces': traces}

WindowOptions = {'frequency_control': True,
              'measurement_control': True,
              'capture_control': True,
              'amplitude_control': True,
              'device_control': False,
              'trace_control': True}
