
"""
The main application window and GUI controls

``MainWindow`` creates and handles the ``File | Open Device`` menu and
wraps the ``MainPanel`` widget responsible for most of the interface.

All the buttons and controls and their callback functions are built in
``MainPanel`` and arranged on a grid.  A ``SpectrumView`` is created
and placed to left of the controls.
"""

import sys
import socket
from contextlib import contextmanager

from PySide import QtGui

from pyrf.gui.spectrum import SpectrumView
from pyrf.gui.util import frequency_text
from pyrf.devices.thinkrf import WSA4000
from pyrf.connectors.twisted_async import TwistedConnector
from pyrf.util import read_data_and_context
from pyrf.numpy_util import compute_fft

try:
    from twisted.internet.defer import inlineCallbacks
except ImportError:
    def inlineCallbacks(fn):
        pass

DEVICE_FULL_SPAN = 125e6


class MainWindow(QtGui.QMainWindow):
    """
    The main window and menus
    """
    def __init__(self, name=None):
        super(MainWindow, self).__init__()
        self.initUI()

        self.dut = None
        self._reactor = self._get_reactor()
        if len(sys.argv) > 1:
            self.open_device(sys.argv[1])
        else:
            self.open_device_dialog()
        self.show()

    def _get_reactor(self):
        # late import because installReactor is being used
        from twisted.internet import reactor
        return reactor

    def initUI(self):
        openAction = QtGui.QAction('&Open Device', self)
        openAction.triggered.connect(self.open_device_dialog)
        exitAction = QtGui.QAction('&Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.triggered.connect(self.close)
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(openAction)
        fileMenu.addAction(exitAction)

        self.setWindowTitle('PyRF')

    def open_device_dialog(self):
        name, ok = QtGui.QInputDialog.getText(self, 'Open Device',
            'Enter a hostname or IP address:')
        while True:
            if not ok:
                return

            try:
                self.open_device(name)
                break
            except socket.error:
                name, ok = QtGui.QInputDialog.getText(self, 'Open Device',
                    'Connection Failed, please try again\n\n'
                    'Enter a hostname or IP address:')

    @inlineCallbacks
    def open_device(self, name):
        dut = WSA4000(connector=TwistedConnector(self._reactor))
        yield dut.connect(name)
        if '--reset' in sys.argv:
            yield dut.reset()
        else:
            yield dut.flush()

        self.dut = dut
        self.setCentralWidget(MainPanel(dut))
        self.setWindowTitle('PyRF: %s' % name)

    def closeEvent(self, event):
        event.accept()
        self._reactor.stop()


class MainPanel(QtGui.QWidget):
    """
    The spectrum view and controls
    """
    def __init__(self, dut):
        super(MainPanel, self).__init__()
        self.dut = dut
        self.mhz_bottom, self.mhz_top = (f/10**6 for f in dut.SWEEP_FREQ_RANGE)
        self.center_freq = None
        self.decimation_factor = None
        self.decimation_points = None
        self._vrt_context = {}
        self.screen = SpectrumView()
        self.initDUT()
        self.initUI()

    @inlineCallbacks
    def initDUT(self):
        yield self.dut.request_read_perm()
        self.center_freq = yield self.dut.freq()
        self.decimation_factor = yield self.dut.decimation()

        yield self.dut.flush()
        yield self.dut.request_read_perm()
        self.dut.connector.vrt_callback = self.receive_vrt
        yield self.dut.capture(self.points, 1)

    def receive_vrt(self, packet):
        if packet.is_data_packet():
            if any(x not in self._vrt_context for x in (
                    'reflevel', 'rffreq')):
                return
            # queue up the next capture while we update
            self.dut.capture(self.points, 1)
            self.screen.update_data(
                compute_fft(self.dut, packet, self._vrt_context),
                self.center_freq,
                self.decimation_factor)
        else:
            self._vrt_context.update(packet.fields)

    def initUI(self):
        grid = QtGui.QGridLayout()
        grid.setSpacing(10)
        grid.addWidget(self.screen, 0, 0, 8, 1)
        grid.setColumnMinimumWidth(0, 400)

        y = 0
        grid.addWidget(self._antenna_control(), y, 1, 1, 2)
        grid.addWidget(self._bpf_control(), y, 3, 1, 2)
        y += 1
        grid.addWidget(self._gain_control(), y, 1, 1, 2)
        grid.addWidget(QtGui.QLabel('IF Gain:'), y, 3, 1, 1)
        grid.addWidget(self._ifgain_control(), y, 4, 1, 1)
        y += 1
        freq, steps, freq_plus, freq_minus = self._freq_controls()
        grid.addWidget(QtGui.QLabel('Center Freq:'), y, 1, 1, 1)
        grid.addWidget(freq, y, 2, 1, 2)
        grid.addWidget(QtGui.QLabel('MHz'), y, 4, 1, 1)
        y += 1
        grid.addWidget(steps, y, 2, 1, 2)
        grid.addWidget(freq_minus, y, 1, 1, 1)
        grid.addWidget(freq_plus, y, 4, 1, 1)
        y += 1
        span, rbw = self._span_rbw_controls()
        grid.addWidget(span, y, 1, 1, 2)
        grid.addWidget(rbw, y, 3, 1, 2)

        self.setLayout(grid)
        self.show()

    @inlineCallbacks
    def _read_update_antenna_box(self):
        ant = yield self.dut.antenna()
        self._antenna_box.setCurrentIndex(ant - 1)

    def _antenna_control(self):
        antenna = QtGui.QComboBox(self)
        antenna.addItem("Antenna 1")
        antenna.addItem("Antenna 2")
        self._antenna_box = antenna
        self._read_update_antenna_box()
        def new_antenna():
            with self.paused_stream() as dut:
                dut.antenna(int(antenna.currentText().split()[-1]))
        antenna.currentIndexChanged.connect(new_antenna)
        return antenna

    @inlineCallbacks
    def _read_update_bpf_box(self):
        bpf = yield self.dut.preselect_filter()
        self._bpf_box.setCurrentIndex(0 if bpf else 1)

    def _bpf_control(self):
        bpf = QtGui.QComboBox(self)
        bpf.addItem("BPF On")
        bpf.addItem("BPF Off")
        self._bpf_box = bpf
        self._read_update_bpf_box()
        def new_bpf():
            with self.paused_stream() as dut:
                dut.preselect_filter("On" in bpf.currentText())
        bpf.currentIndexChanged.connect(new_bpf)
        return bpf

    @inlineCallbacks
    def _read_update_gain_box(self):
        gain = yield self.dut.gain()
        self._gain_box.setCurrentIndex(self._gain_values.index(gain))

    def _gain_control(self):
        gain = QtGui.QComboBox(self)
        gain_values = ['High', 'Med', 'Low', 'VLow']
        for g in gain_values:
            gain.addItem("RF Gain: %s" % g)
        self._gain_values = [g.lower() for g in gain_values]
        self._gain_box = gain
        self._read_update_gain_box()
        def new_gain():
            g = gain.currentText().split()[-1].lower().encode('ascii')
            with self.paused_stream() as dut:
                dut.gain(g)
        gain.currentIndexChanged.connect(new_gain)
        return gain

    @inlineCallbacks
    def _read_update_ifgain_box(self):
        ifgain = yield self.dut.ifgain()
        self._ifgain_box.setValue(int(ifgain))

    def _ifgain_control(self):
        ifgain = QtGui.QSpinBox(self)
        ifgain.setRange(-10, 34)
        ifgain.setSuffix(" dB")
        self._ifgain_box = ifgain
        self._read_update_ifgain_box()
        def new_ifgain():
            with self.paused_stream() as dut:
                dut.ifgain(ifgain.value())
        ifgain.valueChanged.connect(new_ifgain)
        return ifgain

    @inlineCallbacks
    def _read_update_freq_edit(self):
        "Get current frequency from self.dut and update the edit box"
        self._update_freq_edit() # once immediately in case of long delay
        self.center_freq = yield self.dut.freq()
        self._update_freq_edit()

    def _update_freq_edit(self):
        "Update the frequency edit box from self.center_freq"
        if self.center_freq is None:
            self._freq_edit.setText("---")
        else:
            self._freq_edit.setText("%0.1f" % (self.center_freq / 1e6))

    def _freq_controls(self):
        freq = QtGui.QLineEdit("")
        self._freq_edit = freq
        self._read_update_freq_edit()
        def write_freq():
            try:
                f = float(freq.text())
            except ValueError:
                return
            if f < self.mhz_bottom:
                f = self.mhz_bottom
                self.set_freq_mhz(f)
                self._update_freq_edit()
            elif self.mhz_top < f:
                f = self.mhz_top
                self.set_freq_mhz(f)
                self._update_freq_edit()
            else:
                self.set_freq_mhz(f)
        freq.editingFinished.connect(write_freq)

        steps = QtGui.QComboBox(self)
        steps.addItem("Adjust: 1 MHz")
        steps.addItem("Adjust: 2.5 MHz")
        steps.addItem("Adjust: 10 MHz")
        steps.addItem("Adjust: 25 MHz")
        steps.addItem("Adjust: 100 MHz")
        steps.setCurrentIndex(2)
        def freq_step(factor):
            try:
                f = float(freq.text())
            except ValueError:
                self._update_freq_edit()
                return
            delta = float(steps.currentText().split()[1]) * factor
            freq.setText("%0.1f" % (f + delta))
            write_freq()
        freq_minus = QtGui.QPushButton('-')
        freq_minus.clicked.connect(lambda: freq_step(-1))
        freq_plus = QtGui.QPushButton('+')
        freq_plus.clicked.connect(lambda: freq_step(1))

        return freq, steps, freq_plus, freq_minus

    @inlineCallbacks
    def _read_update_span_rbw_boxes(self):
        self.decimation_factor = yield self.dut.decimation()
        self._span_box.setCurrentIndex(
            self._decimation_values.index(self.decimation_factor))
        self._update_rbw_box()

    def _update_rbw_box(self):
        d = self.decimation_factor
        for i, p in enumerate(self._points_values):
            r = DEVICE_FULL_SPAN / d / p
            self._rbw_box.setItemText(i, "RBW: %s" % frequency_text(r))
            if self.decimation_points and self.decimation_points == d * p:
                self._rbw_box.setCurrentIndex(i)
        self.points = self._points_values[self._rbw_box.currentIndex()]

    def _span_rbw_controls(self):
        span = QtGui.QComboBox(self)
        decimation_values = [1] + [2 ** x for x in range(2, 10)]
        for d in decimation_values:
            span.addItem("Span: %s" % frequency_text(DEVICE_FULL_SPAN / d))
        self._decimation_values = decimation_values
        self._span_box = span
        def new_span():
            self.set_decimation(decimation_values[span.currentIndex()])
            self._update_rbw_box()
        span.currentIndexChanged.connect(new_span)

        rbw = QtGui.QComboBox(self)
        self._points_values = [2 ** x for x in range(8, 16)]
        self._rbw_box = rbw
        rbw.addItems([str(p) for p in self._points_values])
        self._read_update_span_rbw_boxes()

        def new_rbw():
            self.points = self._points_values[rbw.currentIndex()]
            self.decimation_points = self.decimation_factor * self.points
            with self.paused_stream() as dut:
                dut.spp(self.points)
        rbw.setCurrentIndex(self._points_values.index(1024))
        rbw.currentIndexChanged.connect(new_rbw)

        return span, rbw


    def set_freq_mhz(self, f):
        self.center_freq = f * 1e6
        with self.paused_stream() as dut:
            dut.freq(self.center_freq)

    def set_decimation(self, d):
        self.decimation_factor = 1 if d == 0 else d
        with self.paused_stream() as dut:
            dut.decimation(d)

    @contextmanager
    def paused_stream(self):
        yield self.dut


