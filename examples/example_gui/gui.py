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

from pyrf.numpy_util import compute_fft, _decode_data_pkts
from pyrf.devices.thinkrf import WSA
from pyrf.vrt import (I_ONLY, VRT_IFDATA_I14Q14, VRT_IFDATA_I14,
    VRT_IFDATA_I24, VRT_IFDATA_PSD8)
SAMPLE_VALUES = [128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768]
RBW_VALUES = [244.141e3 * 2 , 
            244.141e3, 
            122.070e3, 
            61.035e3, 
            30.518e3, 
            15.259e3, 
            7.62939e3, 
            3.815e3, 
            3.815e3 / 2]

HDR_RBW_VALUES = [1271.56, 635.78, 317.890, 158.94, 79.475, 39.736, 19.868, 9.934]
MODES = ['ZIF', 'SH', 'SHN', 'HDR', 'DD']
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
        WINDOW_WIDTH = screen.width() * 0.8
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
        self.setMinimumWidth(screen.width() * 0.8)
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
            'rfe_mode': 'SH',
            'iq_output_path': 'DIGITIZER'}
        self.rbw = RBW_VALUES[4]
        self.enable_mhold = False
        self.mhold = []
        self.dut = dut
        self.dut_prop = self.dut.properties
        self.cap_dut = CaptureDevice(dut, async_callback=self.receive_capture,
            device_settings=self.dev_set)
        self.initUI()
        self.enable_controls()
        self.read_block()

    def read_block(self):
        rbw = self.rbw 
        if self.dev_set['rfe_mode'] == 'ZIF':
            rbw = self.rbw * 2
        self.cap_dut.capture_time_domain(self.dev_set['rfe_mode'],
                                    self.dev_set['freq'],
                                    rbw)

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
        grid.setSpacing(5)
        plot_width = 8
        for x in range(plot_width):
            grid.setColumnMinimumWidth(x, 250)
        grid.setColumnMinimumWidth(plot_width + 1, 260)
        
        grid.addWidget(self._plot_layout(), 0,0,5,plot_width)
        
        controls_layout = QtGui.QVBoxLayout()
        controls_layout.setSpacing(1)
        controls_layout.addWidget(self._if_attenuator())
        controls_layout.addWidget(self._hdr_gain())
        controls_layout.addWidget(self._center_freq())
        controls_layout.addWidget(self._rbw_controls())
        
        controls_layout.addWidget(self._mode_controls())
        controls_layout.addWidget(self._maxh_controls())
        controls_layout.addStretch()
        grid.addLayout(controls_layout, 0, plot_width + 1, 0, 5)

        self._grid = grid
        self.setLayout(grid)
    def _plot_layout(self):

        # create spectral plot
        self.window = pg.PlotWidget(name='pyrf_plot')
        self.window.showGrid(True, True)
        self.window.setYRange(PLOT_YMIN ,PLOT_YMAX)
        self.fft_curve = self.window.plot(pen = 'g')
        self.mhold_curve = self.window.plot(pen = 'y')
       
        # create IQ plot widget
        self.iq_window = pg.PlotWidget(name='IQ Plot')
        self.i_curve = self.iq_window.plot(pen = 'r')
        self.q_curve = self.iq_window.plot(pen = 'g')
        
        # create split
        vsplit = QtGui.QSplitter()
        vsplit.setOrientation(QtCore.Qt.Vertical)
        vsplit.addWidget(self.window)
        vsplit.addWidget(self.iq_window)
        self._plot_layout = vsplit
        return self._plot_layout
        
    def _center_freq(self):
        grid, widget = self.create_grid_and_widget('Freq')
        freq_edit = QtGui.QLineEdit(str(self.dev_set['freq'] / float(M)))
        self._freq_edit = freq_edit
        self.control_widgets.append(self._freq_edit)
        
        def freq_change():
            self.dev_set['freq'] = float(freq_edit.text()) * M
            self.cap_dut.configure_device(self.dev_set)
        freq_edit.returnPressed.connect(lambda: freq_change())
        grid.addWidget(freq_edit, 0,1,0,1)
        widget.setLayout(grid)
        return widget

    def _if_attenuator(self):
        grid, widget = self.create_grid_and_widget('IF Attenuator')
        if_attenuator = QtGui.QLineEdit('25')

        self.control_widgets.append(if_attenuator)
        
        def atten_change():
            self.dut.var_attenuator(int(if_attenuator.text()))
        if_attenuator.returnPressed.connect(lambda: atten_change())
        grid.addWidget(if_attenuator, 0,1,0,1)
        widget.setLayout(grid)
        return widget

    def _hdr_gain(self):
        grid, widget = self.create_grid_and_widget('hdr Attenuator')
        hdr_attenuator = QtGui.QLineEdit('25')

        self.control_widgets.append(hdr_attenuator)
        
        def atten_change():
            self.dut.hdr_gain(int(hdr_attenuator.text()))
        hdr_attenuator.returnPressed.connect(lambda: atten_change())
        grid.addWidget(hdr_attenuator, 0,1,0,1)
        widget.setLayout(grid)
        return widget

    def _mode_controls(self):
        grid, widget = self.create_grid_and_widget('Mode')
        mode = QtGui.QComboBox(self)
        mode.addItems(MODES)

        def new_mode():
            self.dev_set['rfe_mode'] = MODES[mode.currentIndex()]
            self.dut.rfe_mode(self.dev_set['rfe_mode'])
        mode.setCurrentIndex(1)
        mode.currentIndexChanged.connect(new_mode)
        grid.addWidget(mode, 0,1,0,1)
        widget.setLayout(grid)
        self.control_widgets.append(mode)
        return widget

    def _rbw_controls(self):
        grid, widget = self.create_grid_and_widget('Sample Size')
        rbw = QtGui.QComboBox(self)
        rbw.setToolTip("Change the RBW of the FFT plot")

        self._hdr_points_values = HDR_RBW_VALUES
        self._rbw_box = rbw
        rbw.addItems([str(p) + ' ' for p in SAMPLE_VALUES])

        def new_rbw():
            self.rbw = RBW_VALUES[rbw.currentIndex()]
            if self.dev_set['rfe_mode'] == 'HDR':
                self.rbw = HDR_RBW_VALUES[rbw.currentIndex()]
        rbw.setCurrentIndex(3)
        rbw.currentIndexChanged.connect(new_rbw)
        grid.addWidget(rbw, 0,1,0,1)
        widget.setLayout(grid)
        self.control_widgets.append(self._rbw_box)
        return widget
        
    def _maxh_controls(self):
        grid, widget = self.create_grid_and_widget('Max Hold')
        max_hold = QtGui.QCheckBox(self)

        def change_max_hold():
            self.enable_mhold = max_hold.isChecked()

        max_hold.clicked.connect(change_max_hold)
        grid.addWidget(max_hold, 0,1,0,1)
        widget.setLayout(grid)
        return widget
            
    def create_grid_and_widget(self, name):
            grid = QtGui.QGridLayout()
            widget = QtGui.QWidget()
            if name is not None:
                grid.addWidget(QtGui.QLabel(name), 0,0,0,1)
            widget.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred)
            return grid, widget
    
    def update_plot(self):
        self.update_trace()
        
    def update_trace(self):
        freq_range = np.linspace(self.dev_set['freq'] -62.5, 
                                self.dev_set['freq'] + 62.5, 
                                len(self.pow_data)) 
        self.fft_curve.setData(freq_range, self.pow_data)
        if self.enable_mhold:
            if len(self.mhold) != len(self.pow_data):
                self.mhold = self.pow_data
            else:
                self.mhold = np.maximum(self.mhold, self.pow_data)
            self.mhold_curve.setData(freq_range, self.mhold)
        else:
            self.mhold_curve.setData([], [])
            self.mhold = []
            
        i_data, q_data, stream_id, spec_inv = _decode_data_pkts(self.raw_data)
        self.i_curve.setData(i_data)
        if q_data is not None:
            self.q_curve.setData(q_data)
        else:
            self.q_curve.setData([])
    def enable_controls(self):
        for item in self.control_widgets:
            item.setEnabled(True)
    

    def disable_controls(self):
        for item in self.control_widgets:
            item.setEnabled(False)
