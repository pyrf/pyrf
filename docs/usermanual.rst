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

   Download and install, in the order as listed, the latest version of:

   * `32-bit version of Python 2.7.x <http://www.python.org/download/releases/>`_
   * `PyPI setup tools <https://pypi.python.org/pypi/setuptools>`_
   * `pywin32 for 32-bit Python 2.7 <http://sourceforge.net/projects/pywin32/files/pywin32/>`_
     e.g. "pywin32-218.win32-py2.7.exe"

   Add ``Python27`` and ``Python27\Scripts`` directories to your PATH environment
   variable.  e.g. if using the default install path, add::

      ;C:\Python27;C:\Python27\Scripts

   Open a Command Prompt window and run the following to download the lastest
   library package::
   
      easy_install -U numpy
      easy_install -U pyside
      easy_install -U zope.interface
      easy_install -U twisted
      easy_install -U qt4reactor
      
   (Or in one line: ``easy_install -U numpy pyside zope.interface twisted qt4reactor``)
   
   With ``pyrf``, first time running, use::
   
      easy_install pyrf 
   
   Next update usage, use::

      easy_install -U pyrf
   
   If ``easy_install`` failed for any of the libraries above, download the latest
   version for ``32-bit Python 2.7`` directly from:
   
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
   * `qtreactor <https://github.com/pyrf/qtreactor/tags>`_,
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

