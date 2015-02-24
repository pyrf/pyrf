from collections import namedtuple
from PySide import QtGui
import numpy as np

from pyrf.units import M
from pyrf.gui import colors, fonts
from pyrf.gui.widgets import QComboBoxPlayback, QDoubleSpinBoxPlayback, QCheckBoxPlayback
from pyrf.gui.fonts import GROUP_BOX_FONT, HIGHLIGHTED_MARKER_LABEL
from pyrf.gui.labels import MARKERS, TRACES
from pyrf.gui.util import hide_layout
from pyrf.gui.gui_config import markerState, traceState
BUTTON_WIDTH = 65

UNITS = ['GHz', 'MHz', 'kHz', 'Hz']
UNIT_MAGNITUDE = {'GHz': 1e9,
                  'MHz': 1e6,
                  'kHz': 1e3,
                  'Hz': 1}
UNIT_DECIMAL = {'GHz': 11,
                  'MHz': 8,
                  'kHz': 5,
                  'Hz': 2}

class MarkerWidget(QtGui.QWidget):
    def __init__(self, controller, name):
        super(MarkerWidget, self).__init__()
        self.name = name
        self.controller = controller
        controller.marker_change.connect(self.marker_changed)
        controller.trace_change.connect(self.trace_changed)
        controller.device_change.connect(self.device_changed)
        controller.state_change.connect(self.state_changed)

        self._marker_state = markerState
        self._trace_state = traceState
        self.create_controls()
        self.setLayout(QtGui.QGridLayout())
        self._build_layout()

    def create_controls(self):

        self.add_marker = QtGui.QPushButton('+ Marker')
        def add_clicked():
            self.controller.apply_marker_options(self.name, ['enabled', 'freq'], [True, self._gui_state.center])

            self._build_layout()
        self.add_marker.clicked.connect(add_clicked)
        self.add_marker.setMaximumWidth(60)

        self.remove_marker = QtGui.QPushButton('- Marker')

        def remove_clicked():
            self.controller.apply_marker_options(self.name, ['enabled', 'delta'], [False, False])
            self._build_layout()
        self.remove_marker.clicked.connect(remove_clicked)
        self.remove_marker.setMaximumWidth(60)

        self.trace = QComboBoxPlayback()
        self.trace.quiet_update_pixel(colors.TRACE_COLORS, TRACES)
        def new_trace():
            self.controller.apply_marker_options(self.name, ['trace'], [int(self.trace.currentText())])
        self.trace.currentIndexChanged.connect(new_trace)

        self.trace_label = QtGui.QLabel('Trace:')

        self.freq = QDoubleSpinBoxPlayback()
        self.freq.setSingleStep(1)
        def freq_change():
            factor = UNIT_MAGNITUDE[self._marker_state[self.name]['unit']]
            new_freq = self.freq.value() * factor
            fstart = self._gui_state.center - (self._gui_state.span / 2)
            fstop = self._gui_state.center + (self._gui_state.span / 2)
            if new_freq < fstart:
                new_freq = fstart
            elif new_freq > fstop:
                new_freq = fstop
            self.controller.apply_marker_options(self.name, ['freq'], [new_freq])
        self.freq.editingFinished.connect(freq_change)
        self.freq.setMaximumWidth(100)
        self.add_delta = QtGui.QPushButton('+ Delta')

        def add_delta_clicked():
            self.controller.apply_marker_options(self.name, ['delta', 'dfreq'], [True, self._gui_state.center])
            self._build_layout()
        self.add_delta.clicked.connect(add_delta_clicked)
        self.add_delta.setMaximumWidth(60)

        self.remove_delta = QtGui.QPushButton('- Delta')
        def remove_delta_clicked():
            self.controller.apply_marker_options(self.name, ['delta'], [False])
            self._build_layout()
        self.remove_delta.clicked.connect(remove_delta_clicked)
        self.remove_delta.setMaximumWidth(60)

        self.dtrace = QComboBoxPlayback()
        self.dtrace.quiet_update_pixel(colors.TRACE_COLORS, TRACES)
        def new_dtrace():
            self.controller.apply_marker_options(self.name, ['dtrace'], [int(self.dtrace.currentText())])
        self.dtrace.currentIndexChanged.connect(new_dtrace)
        self.dtrace_label = QtGui.QLabel(' Delta Trace:')

        self.dfreq = QDoubleSpinBoxPlayback()

        def dfreq_change():
            factor = UNIT_MAGNITUDE[self._marker_state[self.name]['unit']]
            new_freq = self._marker_state[self.name]['freq'] + (self.dfreq.value() * factor)
            fstart = self._gui_state.center - (self._gui_state.span / 2)
            fstop = self._gui_state.center + (self._gui_state.span / 2)
            if new_freq < fstart:
                new_freq = fstart
            elif new_freq > fstop:
                new_freq = fstop
            self.controller.apply_marker_options(self.name, ['dfreq'], [new_freq])
        self.dfreq.editingFinished.connect(dfreq_change)
        self.dfreq.setMaximumWidth(100)

        # control buttons to indicate actions to be taken by markers
        self.peak = QtGui.QPushButton('Peak')
        def find_peak():
            self.controller.apply_marker_options(self.name, ['peak'], [None])
        self.peak.clicked.connect(find_peak)
        self.peak.setMaximumWidth(100)

        self.peak_left = QtGui.QPushButton('Peak Left')
        def find_left_peak():
            self.controller.apply_marker_options(self.name, ['peak_left'], [None])
        self.peak_left.clicked.connect(find_left_peak)
        self.peak.setMaximumWidth(50)

        self.peak_right = QtGui.QPushButton('Peak Right')
        def find_right_peak():
            self.controller.apply_marker_options(self.name, ['peak_right'], [None])
        self.peak_right.clicked.connect(find_right_peak)
        self.peak_right.setMaximumWidth(60)

        self.center = QtGui.QPushButton('Center')
        def center_marker():
            self.controller.apply_settings(center = self.freq.value() * M)
        self.center.clicked.connect(center_marker)
        self.center.setMaximumWidth(50)

        self.unit = QComboBoxPlayback()
        self.unit.quiet_update(UNITS, 'MHz')
        def update_units():
            self.controller.apply_marker_options(self.name, ['unit'], [self.unit.currentText()])
        self.unit.currentIndexChanged.connect(update_units)

        self.dunit = QComboBoxPlayback()
        self.dunit.quiet_update(UNITS, 'MHz')
        def update_dunits():
            self.controller.apply_marker_options(self.name, ['unit'], [self.dunit.currentText()])
        self.dunit.currentIndexChanged.connect(update_dunits)

    def _build_layout(self):
        grid = self.layout()
        hide_layout(grid)

        def show(widget, y, x, h, w):
            grid.addWidget(widget, y, x, h, w)
            widget.show()

        def add_marker(d):
            show(self.remove_marker, 0, 0, 1, 1)
            show(self.trace, 0, 1, 1, 1)
            show(self.freq, 0, 2, 1, 2)
            show(self.unit, 0, 4, 1, 1)
            if d:
                show(self.remove_delta, 1, 0, 1, 1)
                show(self.dtrace, 1, 1, 1, 1)
                show(self.dfreq,  1, 2, 1, 2)
                show(self.dunit, 1, 4, 1, 1)
            else:
                show(self.add_delta, 1, 0, 1, 1)
            show(self.peak_left, 2, 0, 1, 1)
            show(self.peak, 2, 1, 1, 1)
            show(self.peak_right,  2, 2, 1, 1)
            show(self.center,  2, 3, 1, 1)

        def remove_marker():
            show(QtGui.QLabel(), 0, 1, 1, 8)
            show(self.add_marker, 0, 0, 1, 1)

        d = self._marker_state[self.name]['delta']
        if self._marker_state[self.name]['enabled']: 
            # if marker's current trace is disabled, assign marker to next trace
            if self._trace_state[self._marker_state[self.name]['trace']]['mode'] == 'Off':
                if w.trace.count() == 0:
                    # if no trace is enabled, disable marker
                    remove_marker()
                    self.controller.apply_marker_options(self.name, ['enabled', 'delta'], [False, False])
                else:
                    self.controller.apply_marker_options(self.name, ['trace', 'dtrace'], [int(self.dtrace.currentText()), int(self.dtrace.currentText())])
                    add_marker(d)
            else:
                add_marker(d)
        else:
            remove_marker()
        self.resize_widget()

    def device_changed(self, dut):
        self.dut_prop = dut.properties

    def state_changed(self, state, changed):
        self._gui_state = state
        if 'span' in changed or 'center' in changed:
            factor = UNIT_MAGNITUDE[self._marker_state[self.name]['unit']]
            fstart = state.center - (state.span / 2)
            fstop = state.center + (state.span / 2)
            self.freq.setRange(fstart / factor, fstop / factor)
            self.dfreq.setRange(-1 * state.span / factor, state.span / factor)

    def marker_changed(self, marker, state, changed):
        self._marker_state = state
        if marker == self.name:
            factor = UNIT_MAGNITUDE[state[marker]['unit']]
            if 'enabled' in changed or 'delta' in changed:
                self._build_layout()
                
            if 'freq' in changed:
                if state[marker]['freq'] is not None:
                    self.freq.quiet_update(value = (state[marker]['freq'] / factor))
                if state[marker]['delta']:
                    self.dfreq.quiet_update(value = ((state[marker]['dfreq'] - state[marker]['freq']) / factor))

            if 'dfreq' in changed:
                if state[marker]['delta']:
                    self.dfreq.quiet_update(value = ((state[marker]['dfreq'] - state[marker]['freq']) / factor))
            if 'unit' in changed:
                fstart = self._gui_state.center - (self._gui_state.span / 2)
                fstop = self._gui_state.center + (self._gui_state.span / 2)

                # update number of decimal places
                self.freq.setDecimals(UNIT_DECIMAL[state[marker]['unit']])
                self.dfreq.setDecimals(UNIT_DECIMAL[state[marker]['unit']])

                # update the range
                self.freq.setRange(fstart / factor, fstop / factor)
                self.dfreq.setRange(-1 * self._gui_state.span / factor, self._gui_state.span / factor)
                self.unit.quiet_update(UNITS, state[marker]['unit'])
                self.dunit.quiet_update(UNITS, state[marker]['unit'])
                if self._marker_state[self.name]['enabled']:
                    self.freq.quiet_update(value = (state[marker]['freq'] / factor))
                if state[marker]['delta']:
                    self.dfreq.quiet_update(value = ((state[marker]['dfreq'] - state[marker]['freq']) / factor))

    def trace_changed(self, trace, state, changed):
        self._trace_state = state

        for m in self._marker_state:
            if self._marker_state[m]['trace'] == trace:
                if 'mode' in changed:
                
                    # disable marker if trace is disabled
                    if state[trace]['mode'] == 'Off':
                        self.controller.apply_marker_options(m, ['enabled', 'delta'], [False, False])
        self._update_trace_combo()

    def resize_widget(self):
        self.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)

    def _update_trace_combo(self):
        available_colors = []
        trace_name = []
        for n, t in zip(TRACES, sorted(self._trace_state)):
            if not self._trace_state[t]['mode'] == 'Off':
                available_colors.append(self._trace_state[t]['color'])
                trace_name.append(n)
            index = self._marker_state[self.name]['trace']
            delta_index = self._marker_state[self.name]['dtrace']
            self.trace.quiet_update_pixel(available_colors, trace_name, index)
            self.dtrace.quiet_update_pixel(available_colors, trace_name,delta_index)
        self._build_layout()

class MarkerControls(QtGui.QWidget):

    def __init__(self, controller, plot):
        super(MarkerControls, self).__init__()

        self.controller = controller
        controller.marker_change.connect(self.marker_changed)
        controller.trace_change.connect(self.trace_changed)
        self._marker_state = markerState
        self._trace_state = traceState
        self.setLayout(QtGui.QGridLayout())
        self._create_controls()
        
        self.resize_widget()

    def _create_controls(self):
        self._marker_widgets = {}
        self._tab = QtGui.QTabWidget()
        
        for m in MARKERS:
            self._marker_widgets[m] = MarkerWidget(self.controller, m)
            self._tab.addTab(self._marker_widgets[m], str(m + 1))

        grid = self.layout()
        grid.addWidget(self._tab, 0, 0, 1, 1)
        self.resize_widget()

    def marker_changed(self, marker, state, changed):
        self._marker_state = state

    def trace_changed(self, trace, state, changed):
        self._trace_state = state

    def resize_widget(self):
        self.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Maximum)

    def showEvent(self, event):
        self.activateWindow()

class MarkerTableRow(namedtuple('MarkerTableRow', """
    name
    freq
    power
    delta_freq
    delta_power
    diff_freq
    diff_power
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

class MarkerTable(QtGui.QWidget):

    def __init__(self, controller):
        super(MarkerTable, self).__init__()
        self._create_controls()
        self.controller = controller
        controller.marker_change.connect(self.marker_changed)
        controller.trace_change.connect(self.trace_changed)
        controller.state_change.connect(self.state_changed)
        self._marker_state = markerState
        self._trace_state = traceState
        
        self.setLayout(QtGui.QGridLayout())
        self.resize_widget()

    def _create_controls(self):
        self._marker_rows = {}

        for m in MARKERS:
            self._marker_rows[m] = self._create_marker_row(m)

        self._marker_header = self._create_marker_header()

    def _create_marker_row(self, m):
        sizePolicy = QtGui.QSizePolicy()
        sizePolicy.setHorizontalPolicy(QtGui.QSizePolicy.Maximum)
        name = QtGui.QLabel('%d' % (m + 1))
        name.setSizePolicy(sizePolicy)

        freq = QtGui.QLabel()
        freq.setSizePolicy(sizePolicy)
        freq.setMinimumWidth(80)

        power = QtGui.QLabel()
        power.setSizePolicy(sizePolicy)
        power.setMinimumWidth(80)

        delta_freq = QtGui.QLabel()
        delta_freq.setSizePolicy(sizePolicy)
        delta_freq.setMinimumWidth(80)

        delta_power = QtGui.QLabel()
        delta_power.setSizePolicy(sizePolicy)
        delta_power.setMinimumWidth(80)

        diff_freq = QtGui.QLabel()
        diff_freq.setSizePolicy(sizePolicy)
        diff_freq.setMinimumWidth(80)

        diff_power = QtGui.QLabel()
        diff_power.setSizePolicy(sizePolicy)
        diff_power.setMinimumWidth(80)

        return MarkerTableRow(name, freq, power, delta_freq, delta_power, diff_freq, diff_power)

    def _create_marker_header(self):
        sizePolicy = QtGui.QSizePolicy()
        name = QtGui.QLabel('Marker')
        name.setSizePolicy(sizePolicy)
        name.setStyleSheet('color: %s' % colors.WHITE)
        freq = QtGui.QLabel('Frequency')
        freq.setSizePolicy(sizePolicy)
        freq.setStyleSheet('color: %s' % colors.WHITE)

        power = QtGui.QLabel('Power')
        power.setSizePolicy(sizePolicy)
        power.setStyleSheet('color: %s' % colors.WHITE)

        delta_freq = QtGui.QLabel('Delta Frequency Position')
        delta_freq.setSizePolicy(sizePolicy)
        delta_freq.setStyleSheet('color: %s' % colors.WHITE)

        delta_power = QtGui.QLabel('Delta Power Position')
        delta_power.setSizePolicy(sizePolicy)
        delta_power.setStyleSheet('color: %s' % colors.WHITE)

        diff_freq = QtGui.QLabel('Delta Frequency')
        diff_freq.setSizePolicy(sizePolicy)
        diff_freq.setStyleSheet('color: %s' % colors.WHITE)

        diff_power = QtGui.QLabel('Delta Power')
        diff_power.setSizePolicy(sizePolicy)
        diff_power.setStyleSheet('color: %s' % colors.WHITE)

        return MarkerTableRow(name, freq, power, delta_freq, delta_power, diff_freq, diff_power)

    def _build_layout(self):
        grid = self.layout()
        hide_layout(grid)
        header_shown = False
        def show(widget, y, x, h, w):
            grid.addWidget(widget, y, x, h, w)
            widget.show()

        def add_marker(w, h, n, d):
            if not header_shown:
                show(h.name, 0, 1, 1, 1)
                show(h.freq, 0, 2, 1, 1)
                show(h.power, 0, 3, 1, 1)
                show(h.delta_freq,  0, 4, 1, 1)
                show(h.delta_power, 0, 5, 1, 1)
                show(h.diff_freq, 0, 6, 1, 1)
                show(h.diff_power, 0, 7, 1, 1)

            show(w.name, n, 1, 1, 1)
            show(w.freq, n, 2, 1, 1)
            show(w.power, n, 3, 1, 1)
            show( w.delta_freq,  n, 4, 1, 1)
            show(w.delta_power, n, 5, 1, 1)
            show(w.diff_freq, n, 6, 1, 1)
            show(w.diff_power, n, 7, 1, 1)

        for n, m in enumerate(sorted(self._marker_rows)):
            w = self._marker_rows[m]
            d = self._marker_state[m]['delta']
            h = self._marker_header
            if self._marker_state[m]['enabled']: 
                add_marker(w, h, n + 1, d)
            else:
                continue
            
        self.resize_widget()

    def marker_changed(self, marker, state, changed):
        self._marker_state = state
        if  'enabled' in changed:
            self._build_layout()
            self._update_label_color(marker)

        if state[marker]['enabled']:
            unit = state[marker]['unit']
            factor = UNIT_MAGNITUDE[unit]

            if 'freq' in changed or 'power' in changed:
                self._marker_rows[marker].freq.setText('%0.2f %s' % (state[marker]['freq'] / factor, unit))
                if state[marker]['power'] is None:
                    self._marker_rows[marker].power.setText('---')
                else:
                    self._marker_rows[marker].power.setText('%0.2f dBm' % state[marker]['power'])

            if 'dfreq' in changed or 'dpower' in changed:
                if state[marker]['delta']:
                    freq_diff = state[marker]['dfreq'] - state[marker]['freq']
                    self._marker_rows[marker].delta_freq.setText('%0.2f %s' % (state[marker]['dfreq'] / factor, unit))
                    self._marker_rows[marker].diff_freq.setText('%0.2f %s' % (freq_diff / factor, unit))
                    if state[marker]['dpower'] is None:
                        self._marker_rows[marker].delta_power.setText('---')
                        self._marker_rows[marker].diff_power.setText('---')
                    else:
                        self._marker_rows[marker].delta_power.setText('%0.2f dBm' % state[marker]['dpower'])
                        if state[marker]['power'] is None:
                            self._marker_rows[marker].diff_power.setText('---')
                        else:
                            pow_diff = np.abs(state[marker]['dpower'] - state[marker]['power'])
                            self._marker_rows[marker].diff_power.setText('%0.2f dB' % pow_diff)

            if 'trace' in changed:
                self._update_label_color(marker)

            if 'dtrace' in changed:
                self._update_label_color(marker)

            if 'hovering' in changed:
                self._update_label_color(marker)

            if 'unit' in changed:
                self._marker_rows[marker].freq.setText('%0.2f %s' % (state[marker]['freq'] / factor, unit))
                if state[marker]['delta']:
                    freq_diff = np.abs(state[marker]['dfreq'] - state[marker]['freq'])
                    self._marker_rows[marker].delta_freq.setText('%0.2f %s' % (state[marker]['dfreq'] / factor, unit))
                    self._marker_rows[marker].diff_freq.setText('%0.2f %s' % (freq_diff / factor, unit))

    def state_changed(self, state, changed):
        if 'device_settings.iq_output_path' in changed:
            if state.device_settings['iq_output_path'] == 'CONNECTOR':
                self.setVisible(False)
            elif state.device_settings['iq_output_path'] == 'DIGITIZER':
                self.setVisible(True)

    def _update_label_color(self, marker):
            if self._marker_state[marker]['hovering']:
                color = self._trace_state[self._marker_state[marker]['trace']]['color']
                dcolor = self._trace_state[self._marker_state[marker]['dtrace']]['color']
            else:
                color = colors.WHITE_NUM
                dcolor = colors.WHITE_NUM
            color_str = 'rgb(%s, %s, %s)' % (color[0], color[1], color[2])
            dcolor_str = 'rgb(%s, %s, %s)' % (dcolor[0], dcolor[1], dcolor[2])
            self._marker_rows[marker].name.setStyleSheet('color: %s' % color_str)
            self._marker_rows[marker].freq.setStyleSheet('color: %s' % color_str)
            self._marker_rows[marker].power.setStyleSheet('color: %s' % color_str)
            self._marker_rows[marker].diff_freq.setStyleSheet('color: %s' % color_str)
            self._marker_rows[marker].diff_power.setStyleSheet('color: %s' % color_str)
            self._marker_rows[marker].delta_freq.setStyleSheet('color: %s' % dcolor_str)
            self._marker_rows[marker].delta_power.setStyleSheet('color: %s' % dcolor_str)

    def trace_changed(self, trace, state, changed):
        self._trace_state = state

    def resize_widget(self):
        self.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Maximum)