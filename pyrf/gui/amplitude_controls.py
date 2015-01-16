from PySide import QtGui, QtCore
from pyrf.gui.util import hide_layout
from pyrf.gui.fonts import GROUP_BOX_FONT
from pyrf.gui.widgets import QCheckBoxPlayback, QDoubleSpinBoxPlayback

import numpy as np

PLOT_YMIN = -5000
PLOT_YMAX = 5000
PLOT_TOP = 0
PLOT_BOTTOM = -160
PLOT_STEP = 1

class AmplitudeControls(QtGui.QWidget):
    """
    A widget with a layout containing widgets that
    can be used to control the amplitude configurations of the GUI
    :param name: A controller that emits/receives Qt signals from multiple widgets
    :param name: The name of the groupBox
    """

    def __init__(self, controller, plot):
        super(AmplitudeControls, self).__init__()

        self.controller = controller
        controller.device_change.connect(self.device_changed)
        controller.state_change.connect(self.state_changed)
        controller.plot_change.connect(self.plot_changed)
        self._plot = plot

        grid = QtGui.QGridLayout()
        self.setLayout(QtGui.QGridLayout())

        self._create_controls()
        self._connect_device_controls()
        self._connect_plot_controls()
        self.plot_state = None

    def _create_controls(self):
        attenuator_box = QCheckBoxPlayback("Attenuator")
        attenuator_box.setChecked(True)
        self._atten_box = attenuator_box

        hdr_gain_label = QtGui.QLabel("HDR Gain:")
        hdr_gain_box = QDoubleSpinBoxPlayback()
        hdr_gain_box.setRange(-10, 30)
        hdr_gain_box.setValue(-10)
        hdr_gain_box.setSuffix(" dB")
        self._hdr_gain_label = hdr_gain_label
        self._hdr_gain_box = hdr_gain_box

        self._max_level = QDoubleSpinBoxPlayback()
        self._max_level.setRange(PLOT_YMIN, PLOT_YMAX)
        self._max_level.setValue(PLOT_TOP)
        self._max_level.setSuffix(" dBm")
        self._max_level.setSingleStep(PLOT_STEP)
        self._max_label = QtGui.QLabel('Maximum: ')

        self._db_div = QDoubleSpinBoxPlayback()
        self._db_div.setRange(PLOT_YMIN, PLOT_YMAX)
        self._db_div.setValue(PLOT_BOTTOM)
        self._db_div.setSuffix(" dBm")
        self._db_div.setSingleStep(PLOT_STEP)
        self._div_label = QtGui.QLabel('dB/Div: ')

        self._reference_offset = QtGui.QLabel("Offset")
        self._reference_offset.setToolTip("Add a reference offset to all plots")

        self._reference_offset_spinbox = QDoubleSpinBoxPlayback()
        self._reference_offset_spinbox.setRange(-200, 200)

    def _build_layout(self, dut_prop=None):
        features = dut_prop.SWEEP_SETTINGS if dut_prop else []
        grid = self.layout()

        grid.addWidget(self._max_label, 0, 0, 1, 1)
        grid.addWidget(self._max_level, 0, 1, 1, 1)
        grid.addWidget(self._div_label, 0, 3, 1, 1)
        grid.addWidget(self._db_div, 0, 4, 1, 1)
        grid.addWidget(self._reference_offset, 1, 0, 1,1)
        grid.addWidget(self._reference_offset_spinbox, 1, 1, 1,1)

        if 'attenuator' in features:
            grid.addWidget(self._atten_box, 1, 3, 1, 2)
        if 'hdr_gain' in features:
            grid.addWidget(self._hdr_gain_label, 2, 0, 1, 1)
            grid.addWidget(self._hdr_gain_box, 2, 1, 1, 1)
            self._hdr_gain_box.quiet_update(value=dut_prop.SPECA_DEFAULTS['device_settings']['hdr_gain'])
        grid.setColumnStretch(0, 3)
        grid.setColumnStretch(1, 6)
        grid.setColumnStretch(2, 1)
        grid.setColumnStretch(3, 4)
        grid.setColumnStretch(4, 6)

        grid.setRowStretch(3, 1) # expand empty space at the bottom
        self.setLayout(grid)
        self.resize_widget()

    def device_changed(self, dut):
        self.dut_prop = dut.properties
        self._build_layout(self.dut_prop)

    def state_changed(self, state, changed):
        if state.playback:
            self._atten_box.playback_value(
                state.device_settings.get('attenuator', False))
        elif 'playback' in changed:
            self._atten_box.setEnabled(True)

        if 'mode' in changed:
            if state.mode == 'HDR':
                self._hdr_gain_box.show()
                self._hdr_gain_label.show()
                self.resize_widget()
            else:
                self._hdr_gain_box.hide()
                self._hdr_gain_label.hide()
                self.resize_widget()

        if 'device_settings.iq_output_path' in changed:
            if state.device_settings['iq_output_path'] == 'CONNECTOR':
                self._max_level.setEnabled(False)
                self._db_div.setEnabled(False)
            elif state.device_settings['iq_output_path'] == 'CONNECTOR':
                self._max_level.setEnabled(True)
                self._db_div.setEnabled(True)

    def plot_changed(self, state, changed):
        self.plot_state = state
        if 'ref_level' in changed:
            self._max_level.quiet_update(value = state['ref_level'])
        if 'db_div' in changed:
            self._db_div.quiet_update(value = state['db_div'])

    def resize_widget(self):
        self.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Maximum)

    def _connect_device_controls(self):
        def new_hdr_gain():
            self.controller.apply_device_settings(hdr_gain = self._hdr_gain_box.value())
        def new_attenuator():
            self.controller.apply_device_settings(attenuator = self._atten_box.isChecked())

        def change_reference_offset_value():
            self.controller.apply_plot_options(reference_offset_value = self._reference_offset_spinbox.value())

        self._hdr_gain_box.valueChanged.connect(new_hdr_gain)
        self._atten_box.clicked.connect(new_attenuator)
        self._reference_offset_spinbox.editingFinished.connect(change_reference_offset_value)

    def _connect_plot_controls(self):
        def update_db_div():
            self.controller.apply_plot_options(db_div =  self._db_div.value())

        def update_plot_max():
                self.controller.apply_plot_options(ref_level = self._max_level.value())

        self._db_div.editingFinished.connect(update_db_div)
        self._max_level.editingFinished.connect(update_plot_max)

    def get_max_level(self):
        return self._max_level.value()

    def get_db_div(self):
        return self._db_div.value()

    def showEvent(self, event):
        self.activateWindow()