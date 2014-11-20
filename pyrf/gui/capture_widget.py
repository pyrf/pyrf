from PySide import QtGui, QtCore
from pyrf.gui.util import hide_layout
from pyrf.gui.fonts import GROUP_BOX_FONT
from pyrf.gui.widgets import QCheckBoxPlayback, QDoubleSpinBoxPlayback


class CaptureControls(QtGui.QWidget):
    """
    A widget with a layout containing widgets that
    can be used to control the amplitude configurations of the GUI
    :param name: A controller that emits/receives Qt signals from multiple widgets
    :param name: The name of the groupBox
    """

    def __init__(self, controller):
        super(CaptureControls, self).__init__()

        self.controller = controller
        controller.plot_change.connect(self.plot_changed)

        grid = QtGui.QGridLayout()
        self.setLayout(QtGui.QGridLayout())

        self._create_controls()
        self._build_layout()
        self._connect_capture_controls()

    def _create_controls(self):
        self._conts_box = QCheckBoxPlayback("Continuous")
        self._conts_box.setChecked(True)

        self._single_button = QtGui.QPushButton('Single')

    def _build_layout(self, dut_prop=None):

        grid = self.layout()

        grid.addWidget(self._conts_box, 0, 0, 1, 1)
        grid.addWidget(self._single_button, 0, 1, 1, 1)

        self.setLayout(grid)
        self.resize_widget()

    def _connect_capture_controls(self):

        def single_capture():
            self.controller.apply_plot_options(cont_cap_mode = False)
            self.controller.start_capture(single = True)
        def cont_capture():
            self.controller.apply_plot_options(cont_cap_mode = self._conts_box.isChecked())
            if self._conts_box.isChecked():
                self.controller.start_capture(single = True)
            

        self._single_button.clicked.connect(single_capture)
        self._conts_box.clicked.connect(cont_capture)

    def plot_changed(self, state, changed):
        if 'cont_cap_mode' in changed:
            if not state['cont_cap_mode']:
                if self._conts_box.isChecked():
                    self._conts_box.click()
                    
                

    def resize_widget(self):
        self.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Maximum)



