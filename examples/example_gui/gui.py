"""
The main application window and GUI controls

``MainWindow`` creates and handles the ``File | Open Device`` menu and
wraps the ``MainPanel`` widget responsible for most of the interface.

All the buttons and controls and their callback functions are built in
``MainPanel`` and arranged on a grid.  A ``Pyqtgraph Window`` is created
and placed to left of the controls.
"""

import sys
from PySide import QtGui, QtCore
import pyqtgraph as pg
import numpy as np
import math

from contextlib import contextmanager
from pkg_resources import parse_version


from pyrf.connectors.twisted_async import TwistedConnector
from pyrf.capture_device import CaptureDevice

from pyrf.numpy_util import compute_fft
from pyrf.devices.thinkrf import WSA
from pyrf.vrt import (I_ONLY, VRT_IFDATA_I14Q14, VRT_IFDATA_I14,
    VRT_IFDATA_I24, VRT_IFDATA_PSD8)

RBW_VALUES = [976.562, 488.281, 244.141, 122.070, 61.035, 30.518, 15.259, 7.62939, 3.815]

HDR_RBW_VALUES = [1271.56, 635.78, 317.890, 158.94, 79.475, 39.736, 19.868, 9.934]

PLOT_YMIN = -140
PLOT_YMAX = 0
M = 1e6
ZIF_BITS = 2**13
CONST_POINTS = 512
try:
    from twisted.internet.defer import inlineCallbacks
except ImportError:
    def inlineCallbacks(fn):
        pass


class MainWindow(QtGui.QMainWindow):
    """
    The main window and menus
    """
    def __init__(self, output_file=None):
        super(MainWindow, self).__init__()
        screen = QtGui.QDesktopWidget().screenGeometry()
        WINDOW_WIDTH = screen.width() * 0.7
        WINDOW_HEIGHT = screen.height() * 0.6
        self.resize(WINDOW_WIDTH,WINDOW_HEIGHT)
        self.initUI()

    def initUI(self):
        name = None
        if len(sys.argv) > 1:
            name = sys.argv[1]
        self.mainPanel = MainPanel(self)

        self.setWindowTitle('Spectrum Analyzer')
        self.setCentralWidget(self.mainPanel)
        if name:
            self.mainPanel.open_device(name, True)

    def closeEvent(self, event):
        if self.mainPanel.dut:
            self.mainPanel.dut.abort()
            self.mainPanel.dut.flush()
            self.mainPanel.dut.reset()
        event.accept()
        self.mainPanel._reactor.stop()

class MainPanel(QtGui.QWidget):
    """
    The spectrum view and controls
    """
    def __init__(self, main_window):
        self._main_window = main_window
        self.ref_level = 0
        self.dut = None
        self.control_widgets = []
        super(MainPanel, self).__init__()
        screen = QtGui.QDesktopWidget().screenGeometry()
        self.setMinimumWidth(screen.width() * 0.7)
        self.setMinimumHeight(screen.height() * 0.6)
        self._vrt_context = {}
        self._reactor = self._get_reactor()

    def _get_reactor(self):
        # late import because installReactor is being used
        from twisted.internet import reactor
        return reactor

    @inlineCallbacks
    def open_device(self, name, ok):
        if not ok:
            self._main_window.show()
            return

        if self.dut:
            self.dut.disconnect()
        self._main_window.show()
        dut = WSA(connector=TwistedConnector(self._reactor))
        yield dut.connect(name)
        self.dev_set = {
            'attenuator': 1,
            'freq':2450e6,
            'decimation': 1,
            'fshift': 0,
            'rfe_mode': 'ZIF',
            'iq_output_path': 'DIGITIZER'}
        self.rbw = RBW_VALUES[4]
        self.dut = dut
        self.dut_prop = self.dut.properties
        self.cap_dut = CaptureDevice(dut, async_callback=self.receive_capture,
            device_settings=self.dev_set)
        self.initUI()
        self.enable_controls()
        self.read_block()

    def read_block(self):
        self.cap_dut.capture_time_domain(self.rbw * 1e3)

        
    def receive_capture(self, fstart, fstop, data):
        # store usable bins before next call to capture_time_domain
        self.usable_bins = list(self.cap_dut.usable_bins)
        self.sweep_segments = None

        self.read_block()
        if 'reflevel' in data['context_pkt']:
            self.ref_level = data['context_pkt']['reflevel']
        self.pow_data = compute_fft(self.dut, data['data_pkt'], data['context_pkt'], ref = self.ref_level)
        self.raw_data = data['data_pkt']
        self.update_plot()

    def initUI(self):
        grid = QtGui.QGridLayout()
        grid.setSpacing(10)
        for x in range(8):
            grid.setColumnMinimumWidth(x, 300)

        # add plot widget
        plot_width = 8
        y = 0
        x = plot_width
        self.window = pg.PlotWidget(name='pyrf_plot')
        self.fft_curve = self.window.plot(pen = 'g')
        grid.addWidget(self.window, 0,0,0,8)
        
        controls_layout = QtGui.QVBoxLayout()
        controls_layout.addWidget(self._rbw_controls())
        controls_layout.addWidget(self._center_freq())
        controls_layout.addWidget(self._attenuator_control())
        controls_layout.addStretch()
        grid.addLayout(controls_layout, y, x, 13, 1)

        self._grid = grid
        self.setLayout(grid)

    def _attenuator_control(self):
        attenuator = QtGui.QCheckBox("Attenuator")
        attenuator.setChecked(True)
        
        def new_attenuator():
            self.dev_set['attenuator'] = attenuator.isChecked()
            self.cap_dut.configure_device(self.dev_set)
            
        attenuator.clicked.connect(new_attenuator)
        self._attenuator_box = attenuator
        self.control_widgets.append(attenuator)
        return attenuator

    def _center_freq(self):
        freq_edit = QtGui.QLineEdit(str(self.dev_set['freq'] / float(M)))
        self._freq_edit = freq_edit
        self.control_widgets.append(self._freq_edit)
        
        def freq_change():
            self.dev_set['freq'] = float(freq_edit.text()) * M
            self.cap_dut.configure_device(self.dev_set)
        freq_edit.returnPressed.connect(lambda: freq_change())
        return freq_edit
  

    def _rbw_controls(self):
        rbw = QtGui.QComboBox(self)
        rbw.setToolTip("Change the RBW of the FFT plot")
        self._points_values = RBW_VALUES
        self._hdr_points_values = HDR_RBW_VALUES
        self._rbw_box = rbw
        rbw.addItems([str(p) + ' KHz' for p in self._points_values])

        def new_rbw():
            self.rbw = self._points_values[rbw.currentIndex()]
        rbw.setCurrentIndex(0)
        rbw.currentIndexChanged.connect(new_rbw)
        self.control_widgets.append(self._rbw_box)
        return rbw

       
    def update_plot(self):
        self.update_trace()

    def update_trace(self):
        freq_range = np.linspace(self.dev_set['freq'] -62.5, 
                                self.dev_set['freq'] + 62.5, 
                                len(self.pow_data)) 
        self.fft_curve.setData(freq_range, self.pow_data)
        
    def enable_controls(self):
        for item in self.control_widgets:
            item.setEnabled(True)
    

    def disable_controls(self):
        for item in self.control_widgets:
            item.setEnabled(False)
