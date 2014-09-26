from PySide import QtGui

from pyrf.units import M
from pyrf.gui import colors
from pyrf.gui.fonts import GROUP_BOX_FONT
from pyrf.gui.util import clear_layout
from pyrf.gui.widgets import QCheckBoxPlayback, QDoubleSpinBoxPlayback

class MeasurementControls(QtGui.QGroupBox):

    def __init__(self, controller, name="Measurement Control"):
        super(MeasurementControls, self).__init__()

        self.controller = controller
        controller.device_change.connect(self.device_changed)
        controller.state_change.connect(self.state_changed)
        controller.plot_change.connect(self.plot_changed)

        self.setStyleSheet(GROUP_BOX_FONT)
        self.setTitle(name)

        self._create_controls()
        self.setLayout(QtGui.QGridLayout())
        self._build_layout()
        self._connect_controls()

    def _create_controls(self):
        self._channel_power = QCheckBoxPlayback("Channel Power")
        self._channel_power.setToolTip("Enable Channel Power Measurement")

        self._horizontal_cursor = QCheckBoxPlayback("Horizontal Cursor")
        self._horizontal_cursor.setToolTip("Enable Horizontal Cursor on reference Plot")

        self._cursor_spinbox = QDoubleSpinBoxPlayback()
        self._cursor_spinbox.setRange(-2000, 2000)
        self._cursor_spinbox.setEnabled(False)
        self._cursor_spinbox.quiet_update(value = -100)

    def _build_layout(self):
        grid = self.layout()
        clear_layout(grid)
        grid.addWidget(self._channel_power, 0, 0, 1, 1)

        grid.addWidget(self._horizontal_cursor, 0, 1, 1,1)
        grid.addWidget(self._cursor_spinbox, 0, 2, 1,1)


    def _connect_controls(self):
        def enable_channel_power():
            self.controller.apply_plot_options(channel_power = self._channel_power.isChecked())

        def enable_cursor():
            self.controller.apply_plot_options(horizontal_cursor = self._horizontal_cursor.isChecked())

        def change_cursor_value():
            self.controller.apply_plot_options(horizontal_cursor_value = self._cursor_spinbox.value())

        self._channel_power.clicked.connect(enable_channel_power)
        self._horizontal_cursor.clicked.connect(enable_cursor)
        self._cursor_spinbox.editingFinished.connect(change_cursor_value)

    def device_changed(self, dut):
        self.dut_prop = dut.properties

    def state_changed(self, state, changed):
        self.gui_state = state

    def plot_changed(self, state, changed):
        self.plot_state = state
        if 'horizontal_cursor_value' in changed:
                self._cursor_spinbox.quiet_update(value = float(state['horizontal_cursor_value']))

        if 'horizontal_cursor' in changed:
           if state['horizontal_cursor']:
                    self._cursor_spinbox.setEnabled(True)
           else:
                self._cursor_spinbox.setEnabled(False)
