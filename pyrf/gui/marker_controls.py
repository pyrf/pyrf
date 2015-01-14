from collections import namedtuple
from PySide import QtGui

from pyrf.units import M
from pyrf.gui import colors
from pyrf.gui.widgets import QComboBoxPlayback, QDoubleSpinBoxPlayback, QCheckBoxPlayback
from pyrf.gui.fonts import GROUP_BOX_FONT
from pyrf.gui.labels import MARKERS
class MarkerWidgets(namedtuple('MarkerWidgets', """
    marker_label
    add_marker
    remove_marker
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

    def __init__(self, controller):
        super(MarkerControls, self).__init__()

        self.controller = controller
        controller.device_change.connect(self.device_changed)
        controller.state_change.connect(self.state_changed)
        self._create_controls()
        self.setLayout(QtGui.QGridLayout())
        self._build_layout()
        self.resize_widget()

    def _create_controls(self):
        self._marker_widgets = {}

        for m in MARKERS:
            self._marker_widgets[m] = self._create_marker_widget(m)

    def _create_marker_widget(self, name):
        marker_label = QtGui.QLabel(name)
        add_marker = QtGui.QPushButton('+')
        add_marker.setMaximumWidth(20)
        remove_marker = QtGui.QPushButton('-')
        remove_marker.setMaximumWidth(20)
        freq_label = QtGui.QLabel('Frequency:')
        freq = QDoubleSpinBoxPlayback()
        freq.setSuffix(' MHz')
        
        power = QtGui.QLabel('dB')

        
        delta = QtGui.QPushButton('d')
        
        dfreq_label = QtGui.QLabel('Frequency:')
        dfreq = QDoubleSpinBoxPlayback()
        dfreq.setSuffix(' MHz')

        dpower_label = QtGui.QLabel('Power:')
        dpower = QtGui.QLabel('dB')


        return MarkerWidgets(marker_label, add_marker, remove_marker, freq, power, 
                            delta, dfreq_label, dfreq, dpower_label,
                            dpower)

    def _build_layout(self):
        grid = self.layout()
        for n, m in enumerate(sorted(self._marker_widgets)):
            w = self._marker_widgets[m]
            # grid.addWidget(w.marker_label, n, 0, 1, 1)
            # grid.addWidget(w.add_marker, n, 1, 1, 1)
            grid.addWidget(w.remove_marker, n, 2, 1, 1)
            grid.addWidget(w.freq, n, 3, 1, 1)
            grid.addWidget(w.power, n, 4, 1, 1)
            grid.addWidget(w.delta, n, 5, 1, 1)
            grid.addWidget( w.dfreq, n, 6, 1, 1)
            grid.addWidget(w.dpower, n, 7, 1, 1)
        
        # grid.setColumnStretch(0, 1)
        # grid.setColumnStretch(1, 1)
        # grid.setColumnStretch(2, 1)
        # grid.setColumnStretch(3, 1)
        # grid.setColumnStretch(4, 1)
        # grid.setColumnStretch(5, 1)
        # grid.setColumnStretch(6, 1) 
        self.resize_widget()
    def device_changed(self, dut):
        # to later calculate valid frequency values
        self.dut_prop = dut.properties

    def state_changed(self, state, changed):
        self.gui_state = state

    def resize_widget(self):
        self.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Maximum)

    def showEvent(self, event):
        self.activateWindow()