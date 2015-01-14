from PySide import QtGui

from pyrf.units import M
from pyrf.gui import colors
from pyrf.gui.widgets import QComboBoxPlayback, QDoubleSpinBoxPlayback, QCheckBoxPlayback
from pyrf.gui.fonts import GROUP_BOX_FONT
from pyrf.gui.labels import MARKERS
class MarkerWidgets(namedtuple('MarkerWidgets', """
    name_label
    add
    remove
    freq
    power
    delta
    delta_freq
    delta_power
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
        self._build_layout()
        
    def _create_controls(self):
        self._marker_controls = {}
        
        for m in MARKERS:
            self._marker_controls
    def _create_marker_widget(self, name):
            marker_label = QtGui.QLabel(m)
            add_marker = QtGui.QPushButton('+')
            remove_marker = QtGui.QPushButton('+')
            freq_label = 
            freq = QDoubleSpinBoxPlayback()
            freq.setSuffix(' MHz')
    name_label
    add
    remove
    freq
    power
    delta
    delta_freq
    delta_power
    return TraceWidgets(icon, color_button, draw, hold, clear,
                average_label, average_edit,
                add_trace, remove_trace)
    def _build_layout(self):

    def device_changed(self, dut):
        # to later calculate valid frequency values
        self.dut_prop = dut.properties

    def state_changed(self, state, changed):
        self.gui_state = state


    def resize_widget(self):
        self.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Maximum)

    def showEvent(self, event):
        self.activateWindow()