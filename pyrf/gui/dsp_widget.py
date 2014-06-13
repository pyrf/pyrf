from PySide import QtGui

class DSPWidget(QtGui.QGroupBox):
    """
    A widget based from the Qt QGroupBox widget with a layout containing widgets that
    can be used to control DSP functions of a GUI
    :param name: The name of the groupBox
    :open_device_callback: A function that is called which returns the IP selected

    """
    def __init__(self, open_device_callback=None, name="DSP Controls"):
        super(DSPWidget, self).__init__()

        self._open_device_callback = open_device_callback

        self.setMinimumWidth(400)
        self.setTitle(name)
        layout = QtGui.QVBoxLayout(self)
        
        # First row
        row = QtGui.QHBoxLayout()
        row.addWidget(QtGui.QLabel("Correct IQ Offset"))
        row.addWidget(self._iq_offset())
        row.addWidget(QtGui.QLabel("Correct DC Offset"))
        row.addWidget(self._dc_offset())
        row.addWidget(QtGui.QLabel("Convert to dBm"))
        row.addWidget(self._convert_dbm())
        layout.addLayout(row)

        # second row
        row = QtGui.QHBoxLayout()
        row.addWidget(QtGui.QLabel("Apply Reference Level"))
        row.addWidget(self._apply_ref())
        row.addWidget(QtGui.QLabel("Correct Spectral Inversion"))
        row.addWidget(self._spec_inv())
        row.addWidget(QtGui.QLabel("Apply Window"))
        row.addWidget(self._apply_window())
        layout.addLayout(row)
        self.setLayout(layout)

    def _iq_offset(self):
        self._iq_offset = QtGui.QCheckBox()
        return self._iq_offset
        
    def _dc_offset(self):
        self._dc_offset = QtGui.QCheckBox()
        return self._dc_offset
        
    def _convert_dbm(self):
        self._convert_dbm = QtGui.QCheckBox()
        return self._convert_dbm
        
    def _apply_ref(self):
        self._apply_ref = QtGui.QCheckBox()
        return self._apply_ref
        
    def _spec_inv(self):
        self._spec_inv = QtGui.QCheckBox()
        return self._spec_inv
        
    def _apply_window(self):
        self._apply_window = QtGui.QCheckBox()
        return self._apply_window
        
        