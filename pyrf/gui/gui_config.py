from pyrf.gui import colors
from pyrf.gui import labels

traces = {}
for t, c  in zip(labels.TRACES, colors.TRACE_COLORS):
    traces['trace' + t] = c

PlotOptions = {'cont_cap_mode': True,
              'mouse_tune': True,
              'horizontal_cursor': False,
              'horizontal_cursor_value': -100,
              'y_axis': (-160.0, 0.0),
              'mouse_tune': True,
              'traces': traces}