
import sys
import socket

from PySide import QtGui, QtCore
from spectrum import SpectrumView
from powerdata import read_power_data

from thinkrf.devices import WSA4000

REFRESH_CHARTS = 0.05

class MainWindow(QtGui.QMainWindow):
    def __init__(self, name=None):
        super(MainWindow, self).__init__()
        self.initUI()

        self.dut = None
        if len(sys.argv) > 1:
            self.open_device(sys.argv[1])
        else:
            self.open_device_dialog()
        self.show()

        timer = QtCore.QTimer(self)
        timer.timeout.connect(self.update_charts)
        timer.start(REFRESH_CHARTS)

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

        self.setWindowTitle('ThinkRF WSA4000')

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

    def open_device(self, name):
        dut = WSA4000()
        dut.connect(name)
        dut.request_read_perm()
        if '--reset' in sys.argv:
            dut.reset()

        self.dut = dut
        self.setCentralWidget(MainPanel(dut))
        self.setWindowTitle('ThinkRF WSA4000: %s' % name)

    def update_charts(self):
        if self.dut is None:
            return
        self.centralWidget().update_screen()


class MainPanel(QtGui.QWidget):

    def __init__(self, dut):
        super(MainPanel, self).__init__()
        self.dut = dut
        self.get_freq_mhz()
        powdata, self.reference_level = read_power_data(dut)
        self.screen = SpectrumView(powdata, self.center_freq)
        self.initUI()

    def initUI(self):
        grid = QtGui.QGridLayout()
        grid.setSpacing(10)
        grid.addWidget(self.screen, 0, 0, 8, 1)
        grid.setColumnMinimumWidth(0, 400)

        y = 0
        antenna = QtGui.QComboBox(self)
        antenna.addItem("Antenna 1")
        antenna.addItem("Antenna 2")
        antenna.setCurrentIndex(self.dut.antenna() - 1)
        def new_antenna():
            self.dut.antenna(int(antenna.currentText().split()[-1]))
        antenna.currentIndexChanged.connect(new_antenna)
        grid.addWidget(antenna, y, 1, 1, 2)
        bpf = QtGui.QComboBox(self)
        bpf.addItem("BPF On")
        bpf.addItem("BPF Off")
        bpf.setCurrentIndex(0 if self.dut.preselect_filter() else 1)
        def new_bpf():
            self.dut.preselect_filter("On" in bpf.currentText())
        bpf.currentIndexChanged.connect(new_bpf)
        grid.addWidget(bpf, y, 3, 1, 2)

        y += 1
        gain = QtGui.QComboBox(self)
        gain_values = ['High', 'Med', 'Low', 'VLow']
        for g in gain_values:
            gain.addItem("RF Gain: %s" % g)
        gain_index = [g.lower() for g in gain_values].index(self.dut.gain())
        gain.setCurrentIndex(gain_index)
        def new_gain():
            self.dut.gain(gain.currentText().split()[-1].lower())
        gain.currentIndexChanged.connect(new_gain)
        grid.addWidget(gain, y, 1, 1, 2)
        grid.addWidget(QtGui.QLabel('IF Gain:'), y, 3, 1, 1)
        ifgain = QtGui.QSpinBox(self)
        ifgain.setRange(-10, 34)
        ifgain.setSuffix(" dB")
        ifgain.setValue(int(self.dut.ifgain()))
        def new_ifgain():
            self.dut.ifgain(ifgain.value())
        ifgain.valueChanged.connect(new_ifgain)
        grid.addWidget(ifgain, y, 4, 1, 1)

        y += 1
        grid.addWidget(QtGui.QLabel('Center Freq:'), y, 1, 1, 1)
        freq = QtGui.QLineEdit("")
        def read_freq():
            freq.setText("%0.1f" % self.get_freq_mhz())
        read_freq()
        def write_freq():
            try:
                f = float(freq.text())
            except ValueError:
                return
            self.set_freq_mhz(f)
        freq.textEdited.connect(write_freq)
        grid.addWidget(freq, y, 2, 1, 2)
        grid.addWidget(QtGui.QLabel('MHz'), y, 4, 1, 1)

        y += 1
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
                return read_freq()
            delta = float(steps.currentText().split()[1]) * factor
            freq.setText("%0.1f" % (f + delta))
            write_freq()
        grid.addWidget(steps, y, 2, 1, 2)
        freq_minus = QtGui.QPushButton('-')
        freq_minus.clicked.connect(lambda: freq_step(-1))
        grid.addWidget(freq_minus, y, 1, 1, 1)
        freq_plus = QtGui.QPushButton('+')
        freq_plus.clicked.connect(lambda: freq_step(1))
        grid.addWidget(freq_plus, y, 4, 1, 1)

        y += 1
        rbw = QtGui.QComboBox(self)
        rbw.addItem("RBW: 122kHz")
        rbw.setEnabled(False)
        grid.addWidget(rbw, y, 2, 1, 2)

        self.setLayout(grid)
        self.show()

    def update_screen(self):
        powdata, self.reference_level = read_power_data(self.dut,
            self.reference_level)
        self.screen.update_data(powdata, self.center_freq)

    def get_freq_mhz(self):
        self.center_freq = self.dut.freq()
        return self.center_freq / 1e6

    def set_freq_mhz(self, f):
        self.center_freq = f * 1e6
        return self.dut.freq(self.center_freq)


