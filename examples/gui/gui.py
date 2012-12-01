
from PySide import QtGui, QtCore
from spectrum import SpectrumView
from powerdata import read_power_data

class MainPanel(QtGui.QWidget):

    def __init__(self, dut):
        super(MainPanel, self).__init__()
        self.dut = dut
        self.get_freq_mhz()
        self.screen = SpectrumView(read_power_data(dut), self.center_freq)
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

        y += 1
        grid.addWidget(QtGui.QLabel('Center Freq'), y, 1, 1, 1)
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

        self.setLayout(grid)
        self.setWindowTitle('ThinkRF WSA4000')
        self.show()

    def update_screen(self):
        self.screen.update_data(read_power_data(self.dut), self.center_freq)

    def get_freq_mhz(self):
        self.center_freq = self.dut.freq()
        return self.center_freq / 1e6

    def set_freq_mhz(self, f):
        self.center_freq = f * 1e6
        return self.dut.freq(self.center_freq)


