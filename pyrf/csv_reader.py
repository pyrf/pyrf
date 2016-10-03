import math
import random
from collections import namedtuple
import time

import numpy as np

from pyrf.numpy_util import compute_fft
from pyrf.config import SweepEntry
from pyrf.util import find_saturation


class CSVReader(object):
    """
    Object that reads, and parses ThinkRF RTSA CSV files

    :param filename: name of the file to be read
    :param callback: callback to use for async operation (not used if
                     file_name is using a :class:`PlainSocketConnector`)

    """
    _file = None
    device_id = ''
    def __init__(self, file_name, async_callback=None):
        self._file_name = file_name
        self.async_callback = async_callback

    def open_csv(self):
        self._file = open(self._file_name, 'r')
        
        # read first line, which is the comment line
        self._file_comment = self._file.readline()
        # read second line, which is the device ID line
        self.device_id = self._file.readline()
        # read the header of the data format
        self._file.readline()
        self._line_num = 3
    
    def close_csv(self):
        if self._file is not None:
            self._file.close()
            self._file = None
    def read_data(self):
        try:
            data_header = self._file.readline().split(',')
        except AttributeError:
            return (0,0,[0,0])

        # if we reached end of file, reset the file
        if data_header[0] == 'EOF':
            self._reset_file()
            data_header = self._file.readline().split(',')

        mode = data_header[1]
        start = float(data_header[2])
        stop = float(data_header[3])
        points = int(data_header[4])
        pow_data = []
        for p in range(points - 1):
            data = self._file.readline()
            pow_data.append(float(data))
        self.time_stamp = data_header[5]
        if self.async_callback is None:
            return (start, stop, pow_data)
        else:
            self.async_callback(start, stop, pow_data)

    def _reset_file(self):
        # reset the data file, and read first 3 lines
        self._file.seek(0)
        self._file.readline()
        self._file.readline()
        self._file.readline()