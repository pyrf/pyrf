
import sys
import socket
from PySide import QtGui
from util import frequency_text
from pyrf.devices.thinkrf import WSA4000
from pyrf.connectors.twisted_async import TwistedConnector
from pyrf import twisted_util

# define constants
MIN_FREQ = 0
MAX_FREQ = 10e9
MHZ = 1e6
try:
    from twisted.internet.defer import inlineCallbacks
except ImportError:
    def inlineCallbacks(fn):
        pass

# define the properties of the main window
class MainWindow(QtGui.QMainWindow):
    """
    The main window and menus
    """
    def __init__(self, name=None):
        super(MainWindow, self).__init__()
        self.initUI()
        # connect to the wsa device if the input was provided in console
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

    # initialize the the UI
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
        self.setWindowTitle('PyRF Receiver Controller')

    # connect to device after GUI loaded
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

    # connect to wsa 
    @inlineCallbacks
    def open_device(self, name):
        dut = WSA4000(connector=TwistedConnector(self._reactor))
        yield dut.connect(name)
        if '--reset' in sys.argv:
            yield dut.reset()

        self.dut = dut
        self.setCentralWidget(MainPanel(dut))

    def closeEvent(self, event):
        event.accept()
        self._reactor.stop()

# Panel that contains all the GUI items
class MainPanel(QtGui.QWidget):
    """
    The spectrum view and controls
    """
    def __init__(self, dut):
        super(MainPanel, self).__init__()
        self.dut = dut
        self.center_freq = None
        self.initUI()

    def initUI(self):
        grid = QtGui.QGridLayout()
        grid.setSpacing(10)
        grid.setColumnMinimumWidth(0,4)

        y = 0
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

        self.setLayout(grid)
        self.show()

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
            self.dut.gain(g)
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
            self.dut.ifgain(ifgain.value())
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
            self._freq_edit.setText("%0.1f" % (self.center_freq / MHZ))

    def _freq_controls(self):
        freq = QtGui.QLineEdit("")
        self._freq_edit = freq
        self._read_update_freq_edit()
        def write_freq():
            try:
                f = float(freq.text())
            except ValueError:
                return

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

    def set_freq_mhz(self, f):
        center_freq = f * MHZ
        if center_freq > MAX_FREQ or center_freq < MIN_FREQ:          
            self._freq_edit.setText(str((self.center_freq/MHZ)))
            return
            
        self.center_freq = center_freq
        self.dut.freq(self.center_freq)
