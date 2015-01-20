from collections import namedtuple
from PySide import QtGui

from pyrf.units import M
from pyrf.gui import colors, fonts
from pyrf.gui.widgets import QComboBoxPlayback, QDoubleSpinBoxPlayback, QCheckBoxPlayback
from pyrf.gui.fonts import GROUP_BOX_FONT
from pyrf.gui.labels import MARKERS, TRACES
from pyrf.gui.util import hide_layout

class MarkerWidgets(namedtuple('MarkerWidgets', """
    add_marker
    remove_marker
    trace_label
    trace
    freq
    power
    delta
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
        self._plot = plot
        self._create_controls()
        self.setLayout(QtGui.QGridLayout())
        self._build_layout()
        self.resize_widget()

    def _create_controls(self):
        self._marker_widgets = {}

        for m in MARKERS:
            self._marker_widgets[m] = self._create_marker_widget(m)

    def _create_marker_widget(self, name):
        add_marker = QtGui.QPushButton('+')
        add_marker.setMaximumWidth(50)
        def add_clicked():
            marker = self._plot.markers[int(name)]
            marker.enable()
            self._build_layout()

        add_marker.clicked.connect(add_clicked)

        remove_marker = QtGui.QPushButton('-')
        remove_marker.setMaximumWidth(50)
        def remove_clicked():
            marker = self._plot.markers[int(name)]
            marker.disable()
            self._build_layout()
        remove_marker.clicked.connect(remove_clicked)

        trace = QComboBoxPlayback()
        trace.quiet_update_pixel(colors.TRACE_COLORS, 0)
        def new_trace():
            self._marker_state[name]['trace'] = int(trace.currentIndex())
            self.controller.apply_marker_options(name, ['trace'], **self._marker_state)
        trace.currentIndexChanged.connect(new_trace)
        trace.setMaximumWidth(40)
        trace_label = QtGui.QLabel('Trace:')
        trace_label.setMaximumWidth(30)

        freq = QDoubleSpinBoxPlayback()
        freq.setSuffix('Hz')
        freq.setRange(0, 20e9)
        power = QtGui.QLabel('dB')

        delta = QtGui.QPushButton('d')
        
        dfreq_label = QtGui.QLabel('Frequency:')
        dfreq = QDoubleSpinBoxPlayback()
        dfreq.setSuffix(' MHz')

        dpower_label = QtGui.QLabel('Power:')
        dpower = QtGui.QLabel('dB')


        return MarkerWidgets(add_marker, remove_marker, trace_label, trace, freq, power, 
                            delta, dfreq_label, dfreq, dpower_label,
                            dpower)

    def _build_layout(self):
        grid = self.layout()
        hide_layout(grid)
        def show(widget, y, x, h, w):
            grid.addWidget(widget, y, x, h, w)
            widget.show()
        def add_marker(w, n):
            show(w.remove_marker, n, 1, 1, 1)
            show(w.trace_label, n, 2, 1, 1)
            show(w.trace, n, 3, 1, 1)
            show(w.freq, n, 4, 1, 1)
            show(w.power, n, 5, 1, 1)
            show(w.delta, n, 6, 1, 1)
            show( w.dfreq, n, 7, 1, 1)
            show(w.dpower, n, 8, 1, 1)

        def remove_marker(w, n):
            blank_label = QtGui.QLabel()
            blank_label.setMaximumHeight(5)
            show(blank_label, n, 1, 1, 7)
            show(w.add_marker, n, 1, 1, 1)
            

        for n, m in enumerate(sorted(self._marker_widgets)):
            w = self._marker_widgets[m]
            if self._plot.markers[n].enabled:
                add_marker(w, n)
            else:
                remove_marker(w, n)
        self.resize_widget()

    def device_changed(self, dut):
        # to later calculate valid frequency values
        self.dut_prop = dut.properties

    def state_changed(self, state, changed):
        self.gui_state = state
    
    def marker_changed(self, marker, state, changed):
        self._marker_state = state
        for m in marker:
            w = self._marker_widgets[m]
            if 'power' in changed:
                w.power.setText('%0.2f' % state[m]['power'])

            if 'freq' in changed:
                w.freq.setValue(state[m]['freq'])

            if 'hovering' in changed:
                if state[m]['hovering']:
                    w.freq.setStyleSheet('color: rgb(%s, %s, %s)' % colors.MARKER_HOVER)
                else:
                    w.freq.setStyleSheet('color: rgb(%s, %s, %s)' % colors.BLACK_NUM)







          
    def resize_widget(self):
        self.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Maximum)

    def showEvent(self, event):
        self.activateWindow()