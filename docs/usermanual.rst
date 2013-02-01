Manual
======

.. image:: pyrf_logo.png
   :alt: PyRF logo

Installation
------------


Install from PyPI::

   pip install pyrf

Or Obtain the Development Version::

   git clone git://github.com/pyrf/pyrf.git

(Or `Download a Stable Release <https://github.com/pyrf/pyrf/tags>`_)

Then Install from Source or Extracted Tarball/Zip file::

   python setup.py install


Installing GUI Requirements
~~~~~~~~~~~~~~~~~~~~~~~~~~~

On Debian/Ubuntu::

   apt-get install python-pyside python-twisted python-numpy \
   	python-zope.interface python-pip
   pip install -e git://github.com/pyrf/qtreactor.git#egg=qtreactor

On Windows:

   Download and install:

   * `32-bit version of Python 2.7 <http://www.python.org/ftp/python/2.7/python-2.7.msi>`_

   Find the latest version of each of the following and install:

   * `NumPy for 32-bit Python 2.7 <http://sourceforge.net/projects/numpy/files/NumPy/>`_ e.g. "numpy-1.6.2-win32-superpack-python2.7.exe"
   * `PySide for 32-bit Python 2.7 <http://qt-project.org/wiki/PySide_Binaries_Windows>`_
     e.g. "PySide-1.1.2.win32-py2.7.exe"
   * `zope.interface for 32-bit Python 2.7 <http://pypi.python.org/pypi/zope.interface#download>`_ e.g. "zope.interface-4.0.3-py2.7-win32.egg"
   * `Twisted for 32-bit Python 2.7 <http://twistedmatrix.com/trac/wiki/Downloads#Windows>`_
     e.g. "Twisted-12.3.0.win32-py2.7.msi"
   * `pywin32 for 32-bit Python 2.7 <http://sourceforge.net/projects/pywin32/files/pywin32/>`_
     e.g. "pywin32-218.win32-py2.7.exe"

   Download the `latest version of qtreactor <https://github.com/pyrf/qtreactor/tags>`_,
   extract it then switch to the qtreactor directory and run::

      python setup.py install


Installing GUI Requirements from Source
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On Debian/Ubuntu::

   apt-get install qt-sdk python-dev cmake
   pip install -r gui-requirements.txt



Building EXE Version of GUI
~~~~~~~~~~~~~~~~~~~~~~~~~~~

On Windows:

   Install the GUI requirements above and make sure you can launch the GUI.

   Find and install the
   `latest version of py2exe for 32-bit Python2.7 <http://sourceforge.net/projects/py2exe/files/py2exe/>`_
   e.g. "py2exe-0.6.9.win32-py2.7.exe".

   Then switch to your pyrf directory and run::

      python setup.py py2exe

API for WSA4000 RF Receiver
---------------------------

:class:`pyrf.devices.thinkrf.WSA4000` is the class that provides access
to WSA4000 devices.
Its methods closely match the SCPI Command Set described in the
Programmers Reference available in
`ThinkRF Resources <http://www.thinkrf.com/resources>`_.

There are simple examples that use this API under the "examples" directory
included with the source code.

This API may be used in a blocking mode (the default) or in an asynchronous
mode with using the `Twisted <http://twistedmatrix.com/>`_ python library.
Asynchronous modes using other libraries may be added in the future.

In blocking mode all methods that read from the device will wait
to receive a response before returning.

In asynchronous mode all methods will send their commands to the device and
then immediately return a Twisted Deferred object.  If you need to wait for
the response or completion of this command you can attach a callback to the
Deferred object and the Twisted reactor will call it when ready.  You may
choose to use Twisted's inlineCallbacks function decorator to write Twisted
code that resembles synchronous code by yielding the Deferred objects
returned from the API.

To use the asynchronous when a WSA4000 instance is created
you must pass a :class:`pyrf.connectors.twisted_async.TwistedConnector`
instance as the connector parameter, as in :ref:`twisted-show-i-q`


Processing Tools
----------------

Additional PyRF tools are under active development, but will soon support
processing blocks, multiprocess use and distributed processing as
described in :ref:`planned-development`.


.. _demo-gui:

GUI
---

.. image:: wsa4000demo.png
   :alt: wsa4000gui screen shot

``wsa4000gui`` is a cross-platform GUI application built with the
Qt_ toolkit and PySide_ bindings for Python.

.. _Qt: http://qt.digia.com/
.. _PySide: http://qt-project.org/wiki/PySide

The GUI may be launched with the command::

  wsa4000gui <hostname> [--reset]

If *hostname* is not specified a dialog will appear asking you to enter one.
If ``--reset`` is used the WSA will be reset to defaults before the GUI
appears.

