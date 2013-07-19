#!/usr/bin/env python

# workaround for py2exe not including some files in zip
from scipy.sparse.csgraph import _validation

from pyrf.gui.spectrum_analyzer import main
main()
