from collections import namedtuple
from PySide import QtGui
import numpy as np

from pyrf.units import M
from pyrf.gui import colors, fonts
from pyrf.gui.widgets import QComboBoxPlayback, QDoubleSpinBoxPlayback, QCheckBoxPlayback
from pyrf.gui.fonts import GROUP_BOX_FONT
from pyrf.gui.labels import MARKERS, TRACES
from pyrf.gui.util import hide_layout
from pyrf.gui.gui_config import markerState, traceState
BUTTON_WIDTH = 65
class MarkerWidgets(namedtuple('MarkerWidgets', """
    add_marker
    remove_marker
    trace_label
    trace
    freq
    power
    add_delta
    remove_delta
    dtrace
    dfreq_label
    dfreq
    dpower_label
    dpower
    """)):
    """
    :param icon: color icon
    :param color_button: trace color button
    :param draw: draw combobox, including 'Live', 'Max', 'Min' options
    :param hold: pause checkbox
    :param clear: clear trace button
    :param average_label: average captures label
    :param average: average captures spinbox
    :param add: "+ trace" button
    :param remove: "- trace" button
    """
    
class MarkerControls(QtGui.QWidget):

    def __init__(self, controller, plot):
        super(MarkerControls, self).__init__()

        self.controller = controller
        controller.device_change.connect(self.device_changed)
        controller.state_change.connect(self.state_changed)
        controller.marker_change.connect(self.marker_changed)
        controller.trace_change.connect(self.trace_changed)
        self._marker_state = markerState
        self._trace_state = traceState
        self._plot = plot
        self._create_controls()
        self.setLayout(QtGui.QGridLayout())
        self.resize_widget()

    def _create_controls(self):
        self._marker_widgets = {}

        for m in MARKERS:
            self._marker_widgets[m] = self._create_marker_widget(m)

    def _create_marker_widget(self, name):
        add_marker = QtGui.QPushButton('+')
        add_marker.setMaximumWidth(BUTTON_WIDTH)
        def add_clicked():
            self.controller.apply_marker_options(name, ['enabled'], [True])
            self._build_layout()
        add_marker.clicked.connect(add_clicked)

        remove_marker = QtGui.QPushButton('-')
        remove_marker.setMaximumWidth(BUTTON_WIDTH)
        def remove_clicked():
            self.controller.apply_marker_options(name, ['enabled', 'delta'], [False, False])
            self._build_layout()
        remove_marker.clicked.connect(remove_clicked)

        trace = QComboBoxPlayback()
        trace.quiet_update_pixel(colors.TRACE_COLORS, TRACES)
        def new_trace():
            self._marker_state[name]['trace'] = (trace.currentIndex())
            self.controller.apply_marker_options(name, ['trace'], [int(trace.currentText())])
        trace.currentIndexChanged.connect(new_trace)
        trace.setMaximumWidth(40)
        trace_label = QtGui.QLabel('Trace:')
        trace_label.setMaximumWidth(30)

        freq = QDoubleSpinBoxPlayback()
        freq.setSuffix(' Hz')
        freq.setRange(0, 20e12)
        freq.setMaximumWidth(120)
        def freq_change():
            self.controller.apply_marker_options(name, ['freq'], [freq.value()])
        freq.editingFinished.connect(freq_change)
        power = QtGui.QLabel('dB')
        power.setMaximumWidth(40)
        add_delta = QtGui.QPushButton('Add Delta')
        add_delta.setMaximumWidth(75)
        def add_delta_clicked():
            self.controller.apply_marker_options(name, ['delta'], [True])
        add_delta.clicked.connect(add_delta_clicked)

        remove_delta = QtGui.QPushButton('Remove Delta')
        remove_delta.setMaximumWidth(75)
        def remove_delta_clicked():
            self.controller.apply_marker_options(name, ['delta'], [False])
        remove_delta.clicked.connect(remove_delta_clicked)

        dtrace = QComboBoxPlayback()
        dtrace.quiet_update_pixel(colors.TRACE_COLORS, TRACES)
        def new_dtrace():
            self.controller.apply_marker_options(name, ['dtrace'], [int(dtrace.currentText())])
        dtrace.currentIndexChanged.connect(new_dtrace)
        dtrace.setMaximumWidth(40)
        dtrace_label = QtGui.QLabel(' Delta Trace:')
        dtrace_label.setMaximumWidth(30)

        
        dfreq = QDoubleSpinBoxPlayback()
        dfreq.setSuffix(' Hz')
        dfreq.setRange(0, 20e12)
        dfreq.setMaximumWidth(120)
        def dfreq_change():
            self.controller.apply_marker_options(name, ['dfreq'], [dfreq.value()])
        dfreq.editingFinished.connect(dfreq_change)
        
        dpower = QtGui.QLabel('dB')
        dpower.setMaximumWidth(50)
        dpower_label = QtGui.QLabel('Power:')

        dfreq_label = QtGui.QLabel('Frequency:')

        return MarkerWidgets(add_marker, remove_marker, trace_label, trace, freq, power, 
                            add_delta, remove_delta, dtrace, dfreq_label, dfreq, dpower_label,
                            dpower)

    def _build_layout(self):
        grid = self.layout()
        hide_layout(grid)

        def show(widget, y, x, h, w):
            grid.addWidget(widget, y, x, h, w)
            widget.show()

        def add_marker(w, n, d):
            show(w.remove_marker, n, 0, 1, 1)
            show(w.trace, n, 1, 1, 1)
            show(w.freq, n, 2, 1, 1)
            show(w.power, n, 3, 1, 1)
            if d:
                show(w.remove_delta, n, 4, 1, 1)
                show( w.dtrace,  n, 5, 1, 1)
                show( w.dfreq,  n, 6, 1, 1)
                show(w.dpower, n, 7, 1, 1)
                show(w.dfreq_label, n, 8, 1, 1)
                show(w.dpower_label, n, 9, 1, 1)
            else:
                show(w.add_delta, n, 4, 1, 1)

        def remove_marker(w, n):
            show(w.add_marker, n, 0, 1, 1)
            show(QtGui.QLabel(), n, 1, 1, 8)

        for n, m in enumerate(sorted(self._marker_widgets)):
            w = self._marker_widgets[m]
            d = self._marker_state[m]['delta']
            if self._marker_state[m]['enabled']: 
                # if marker's current trace is disabled, assign marker to next trace
                if not self._trace_state[self._marker_state[m]['trace']]['enabled']:
                    if w.trace.count() == 0:
                        # if no trace is enabled, disable marker
                        remove_marker(w, n)
                        self.controller.apply_marker_options(m, ['enabled', 'delta'], [False, False])
                    else:
                        self.controller.apply_marker_options(m, ['trace', 'dtrace'], [int(w.trace.currentText()), int(w.trace.currentText())])
                        add_marker(w, n, d)
                else:
                    add_marker(w, n, d)
            else:
                remove_marker(w, n)
            
        self.resize_widget()

    def _update_trace_combo(self):
        available_colors = []
        trace_name = []
        for n, t in zip(TRACES, sorted(self._trace_state)):
            if self._trace_state[t]['enabled']:
                available_colors.append(self._trace_state[t]['color'])
                trace_name.append(n)
        for m in self._marker_widgets:
            index = self._marker_state[m]['trace']
            self._marker_widgets[m].trace.quiet_update_pixel(available_colors, trace_name, index)
            self._marker_widgets[m].dtrace.quiet_update_pixel(available_colors, trace_name, index)
        self._build_layout()

    def device_changed(self, dut):

        self.dut_prop = dut.properties
        self._build_layout()

    def state_changed(self, state, changed):
        self.gui_state = state

    def marker_changed(self, marker, state, changed):
        self._marker_state = state
        w = self._marker_widgets[marker]
        if 'power' in changed:
            w.power.setText('%0.2f dB' % state[marker]['power'])
            self.update_diff(w, state[marker])

        if 'dpower' in changed:
            w.dpower.setText('%0.2f dB' % state[marker]['dpower'])
            self.update_diff(w, state[marker])

        if 'hovering' in changed:
            if state[marker]['hovering']:
                w.freq.setStyleSheet('color: rgb(%s, %s, %s)' % colors.MARKER_LABEL_HOVER)
                w.dfreq.setStyleSheet('color: rgb(%s, %s, %s)' % colors.MARKER_LABEL_HOVER)
            else:
                w.freq.setStyleSheet('color: rgb(%s, %s, %s)' % colors.BLACK_NUM)
                w.dfreq.setStyleSheet('color: rgb(%s, %s, %s)' % colors.BLACK_NUM)

        if 'enabled' in changed or 'delta' in changed:
            self._build_layout()

        if 'freq' in changed:
            w.freq.quiet_update(value = state[marker]['freq'])
            self.update_diff(w, state[marker])

        if 'dfreq' in changed:
            w.dfreq.quiet_update(value = state[marker]['dfreq'])
            self.update_diff(w, state[marker])

    def trace_changed(self, trace, state, changed):
        self._trace_state = state
        for m in self._marker_state:
            if self._marker_state[m]['trace'] == trace:
                if 'enabled' in changed:
                    # disable marker if trace is disabled
                    if not state[trace]['enabled']:
                        self.controller.apply_marker_options(m, ['enabled', 'delta'], [False, False])

        self._update_trace_combo()
    def update_diff(self, widget, state):
        if state['enabled'] and state['delta']:
            widget.dfreq_label.setText('Frequency Delta: %0.2f Hz' % (np.abs(state['freq'] - state['dfreq'])))
            widget.dpower_label.setText('Power Delta: %0.2f dB' % (np.abs(state['power'] - state['dpower'])))
    def resize_widget(self):
        self.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Minimum)

    def showEvent(self, event):
        self.activateWindow()
