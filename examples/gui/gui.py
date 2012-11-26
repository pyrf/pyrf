
from numpy import fft, linspace

from PySide import QtGui, QtCore

class MainPanel(QtGui.QWidget):

    def __init__(self, device):
        super(MainPanel, self).__init__()
        self.device = device
        self.screen = SpectrumView(device.read_powdata())
        self.initUI()

    def initUI(self):
        grid = QtGui.QGridLayout()
        grid.setSpacing(10)
        grid.addWidget(self.screen, 0, 0, 8, 8)
        grid.setColumnMinimumWidth(0, 300)
        antenna = QtGui.QComboBox(self)
        antenna.addItem("Antenna 1")
        antenna.addItem("Antenna 2")
        antenna.setEnabled(False)
        grid.addWidget(antenna, 0, 9, 1, 2)
        bpf = QtGui.QComboBox(self)
        bpf.addItem("BPF On")
        bpf.addItem("BPF Off")
        bpf.setEnabled(False)
        grid.addWidget(bpf, 0, 11, 1, 2)

        grid.addWidget(QtGui.QLabel('Center Freq'), 1, 9, 1, 1)
        freq = QtGui.QLineEdit("")
        def read_freq():
            freq.setText("%0.1f" % self.get_freq_mhz())
        read_freq()
        def write_freq():
            try:
                f = float(freq.text())
            except ValueError:
                pass
            self.set_freq_mhz(f)
        freq.textEdited.connect(write_freq)
        grid.addWidget(freq, 1, 10, 1, 2)
        grid.addWidget(QtGui.QLabel('MHz'), 1, 12, 1, 1)

        freq_plus = QtGui.QPushButton('+')
        grid.addWidget(freq_plus, 2, 9, 1, 1)
        steps = QtGui.QComboBox(self)
        steps.addItem("Adjust: 10 MHz")
        steps.addItem("Adjust: 100 MHz")
        def freq_step(factor):
            try:
                f = float(freq.text())
            except ValueError:
                return read_freq()
            delta = int(steps.currentText().split()[1]) * factor
            freq.setText("%0.1f" % (f + delta))
            write_freq()
        grid.addWidget(steps, 2, 10, 1, 2)
        freq_minus = QtGui.QPushButton('-')
        freq_plus.clicked.connect(lambda: freq_step(1))
        freq_minus.clicked.connect(lambda: freq_step(-1))
        grid.addWidget(freq_minus, 2, 12, 1, 1)

        gain_plus = QtGui.QPushButton('+')
        gain_plus.setEnabled(False)
        grid.addWidget(gain_plus, 3, 9, 1, 1)
        gain = QtGui.QComboBox(self)
        gain.addItem("RF Gain: High")
        gain.addItem("RF Gain: Low")
        def new_gain():
            self.update_gain(gain.currentText().split()[-1].lower())
        gain.currentIndexChanged.connect(new_gain)
        grid.addWidget(gain, 3, 10, 1, 2)
        gain_minus = QtGui.QPushButton('-')
        gain_minus.setEnabled(False)
        grid.addWidget(gain_minus, 3, 12, 1, 1)

        self.setLayout(grid)
        self.setWindowTitle('ThinkRF WSA4000')
        self.show()

    def update_screen(self):
        self.screen.update_powdata(self.device.read_powdata())

    def update_gain(self, value):
        self.device.dut.gain(value)

    def get_freq_mhz(self):
        return self.device.dut.freq() / 10 ** 6

    def set_freq_mhz(self, f):
        return self.device.dut.freq(f * 10 ** 6)


class SpectrumView(QtGui.QWidget):

    def __init__(self, powdata):
        super(SpectrumView, self).__init__()
        self.powdata = powdata
        self.setGeometry(0, 0, 300, 200)

    def update_powdata(self, powdata):
        self.powdata = powdata
        self.update()

    def paintEvent(self, e):
        qp = QtGui.QPainter()
        qp.begin(self)
        self.drawLines(qp)
        qp.end()

    def drawLines(self, qp):
        size = self.size()
        width = size.width()
        height = size.height()
        qp.fillRect(0, 0, width, height, QtCore.Qt.black)
        qp.setPen(QtCore.Qt.green)

        prev_x = prev_y = None
        for x, y in zip(
                linspace(0, width - 1, len(self.powdata)),
                self.powdata):

            y = height - 1 - (y / 200 * height)
            if prev_x is not None:
                qp.drawLine(prev_x, prev_y, x, y)
            prev_x, prev_y = x, y
