Manual
======

.. image:: pyrf_logo.png
   :alt: PyRF logo

Installation
------------


Windows Dependencies
~~~~~~~~~~~~~~~~~~~~

Download and install, in the order as listed, the latest version of:

* `32-bit version of Python 2.7 <http://www.python.org/ftp/python/2.7/python-2.7.msi>`_
* `setuptools <https://bitbucket.org/pypa/setuptools/downloads/ez_setup.py>`_

Add ``Python27`` and ``Python27\Scripts`` directories to your PATH environment
variable.  e.g. if using the default install path, add::

  ;C:\Python27;C:\Python27\Scripts

Next install:

* `pywin32 for 32-bit Python 2.7 <http://sourceforge.net/projects/pywin32/files/pywin32/>`_
  (e.g. "pywin32-218.win32-py2.7.exe")
* `NumPy <http://sourceforge.net/projects/numpy/files/NumPy/>`_
  (e.g. "numpy-1.x.x-win32-superpack-python2.7.exe")
* `PySide <http://qt-project.org/wiki/PySide_Binaries_Windows>`_
  (e.g. "PySide-1.x.x.win32-py2.7.exe")
* `zope.interface <http://pypi.python.org/pypi/zope.interface#download>`_
  (e.g. "zope.interface-x.x.x.win32-py2.7.exe")
* `Twisted <http://twistedmatrix.com/trac/>`_
  (e.g. "Twisted-x.x.x.win32-py2.7.msi")
* `pywin32 <http://sourceforge.net/projects/pywin32/files/pywin32/>`_
  (e.g. "pywin32-xxx.win32-py2.7.exe")
* `qtreactor <https://github.com/pyrf/qtreactor/releases>`_,
  extract it then switch to the qtreactor directory and run::

    python setup.py install

Continue from :ref:`pyrf-installation` below.


Debian/Ubuntu Dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~

Use packaged requirements::

   apt-get install python-pyside python-twisted python-numpy \
   	python-zope.interface python-pip python-scipy
   pip install -e git://github.com/pyrf/qtreactor.git#egg=qtreactor
   pip install -e git://github.com/pyrf/pyqtgraph.git#egg=pyqtgraph

Or install GUI requirements from source::

   apt-get install qt-sdk python-dev cmake \
	libblas-dev libatlas-dev liblapack-dev gfortran
   export BLAS=/usr/lib/libblas/libblas.so
   export ATLAS=/usr/lib/atlas-base/libatlas.so
   export LAPACK=/usr/lib/lapack/liblapack.so
   pip install -r gui-requirements.txt

Continue from :ref:`pyrf-installation` below.

.. _pyrf-installation:

PyRF Installation
~~~~~~~~~~~~~~~~~

Download the development version::

   git clone git://github.com/pyrf/pyrf.git
   cd pyrf
   python setup.py install

Or `download a stable release <https://github.com/pyrf/pyrf/releases>`_, then
from the source directory::

   python setup.py install


Building Standalone Spectrum Analyzer EXE
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Find and install the
`latest version of py2exe for 32-bit Python2.7 <http://sourceforge.net/projects/py2exe/files/py2exe/>`_
e.g. "py2exe-0.6.9.win32-py2.7.exe".

Then switch to your pyrf directory and run::

  python setup.py py2exe



API for WSA RF Receiver
-----------------------

:class:`pyrf.devices.thinkrf.WSA` is the class that provides access
to WSA4000 and WSA5000 devices.
Its methods closely match the SCPI Command Set described in the
Programmers Reference available in
`ThinkRF Resources <http://www.thinkrf.com/resources>`_.

There are simple examples that use this API under the "examples" directory
included with the source code.

This API may be used in a blocking mode (the default) or in an asynchronous
mode with using the `Twisted`_ python library.

In blocking mode all methods that read from the device will wait
to receive a response before returning.

In asynchronous mode all methods will send their commands to the device and
then immediately return a Twisted Deferred object.  If you need to wait for
the response or completion of this command you can attach a callback to the
Deferred object and the Twisted reactor will call it when ready.  You may
choose to use Twisted's inlineCallbacks function decorator to write Twisted
code that resembles synchronous code by yielding the Deferred objects
returned from the API.

To use the asynchronous when a WSA instance is created
you must pass a :class:`pyrf.connectors.twisted_async.TwistedConnector`
instance as the connector parameter, as in :ref:`twisted-show-i-q`


.. _demo-gui:

Spectrum Analyzer GUI
---------------------

.. image:: speca-gui.png
   :alt: speca-gui screen shot

.. image:: speca-gui-2.png
   :alt: speca-gui screen shot

``speca-gui`` is a cross-platform GUI application built with the
Qt_ toolkit and PySideProject_ bindings for Python.

.. _Qt: http://qt.digia.com/
.. _PySideProject: http://qt-project.org/wiki/PySide

The GUI may be launched with the command::

  speca-gui <hostname> [--reset]

If *hostname* is not specified a dialog will appear asking you to enter one.
If ``--reset`` is used the WSA will be reset to defaults before the GUI
appears.

