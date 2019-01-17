Manual
======

.. image:: pyrf_logo.png
   :alt: PyRF logo

Installation
------------
This section provides information on how to install the required python packages.

**Note:** Python v2.7.x is the required version for PyRF, not v3.x or higher.


Windows Setup
~~~~~~~~~~~~~

**1. Set-up Python v2.7**

* Install Python v2.7 from https://www.python.org/downloads/release/python-2715/
* Add to the windows PATH: **C:\\Python27** and **C:\\Python27\\Scripts**

**2. Install Dependencies**

These installation steps make use of `pip <https://en.wikipedia.org/wiki/Pip_(package_manager)>`_ software to install required libraries.  Open a command prompt window and type **pip**, if a help menu appears, **pip** is already in your system.  If **pip** has not yet been installed, follow these instructions:

* Download `get-pip.py <https://bootstrap.pypa.io/get-pip.py>`_ (right mouse click and save)
* Open a command prompt window, navigate to get-pip.py and run::

     python get-pip.py

* Now use **pip** to install the dependencies by typing into the command prompt window::

    pip install numpy scipy pyside==1.2.2 pyqtgraph twisted zope.interface setuptools pywin32
    pip install netifaces

**Notes:**
 - **pySide v1.2.2** is needed, not the latest
 - When installing **netifaces**, **MS Visual C++ 9.0** is required, follow the recommended instruction, such as ``error: Microsoft Visual C++ 9.0 is required. Get it from http://aka.ms/vcpython27``

* To install **qtreactor**, choose one of the following option:

 - If you have `git <https://git-scm.com/>`_, run::

    pip install -e git://github.com/pyrf/qtreactor.git#egg=qtreactor

 - Otherwise, download `qtreactor-pyrf-1.0 <https://github.com/pyrf/qtreactor/releases>`_ to your computer, unzip and then go into the extracted folder in a command prompt window and type::

    python setup.py install

Continue with :ref:`pyrf-installation` below.


Linux Setup
~~~~~~~~~~~

These instructions are tested on Debian/Ubuntu system, equivalent **apt-get** command might be needed for your system.

* Install **python2.7** package if not already available in your system
* Install required libraries (sudo privilege might be needed)::

    apt-get install pip 
    pip install numpy scipy pyqtgraph twisted netifaces zope.interface setuptools
    pip install -e git://github.com/pyrf/qtreactor.git#egg=qtreactor
    pip install PySide

**Note:**
 - **pySide v1.2.2** might be needed if the latest 1.2.4 version would not work on your OS (additional installation such as **cmake** or **python-tk** (for Tinker) might be needed if these errors shown during installation)

* Or install dependencies from source::

    apt-get install qt-sdk python-dev cmake libblas-dev libatlas-dev liblapack-dev gfortran
    export BLAS=/usr/lib/libblas/libblas.so
    export ATLAS=/usr/lib/atlas-base/libatlas.so
    export LAPACK=/usr/lib/lapack/liblapack.so
    pip install -r requirements.txt
    pip install pyside==1.2.2

Continue with :ref:`pyrf-installation` below.

.. _pyrf-installation:

PyRF Installation
~~~~~~~~~~~~~~~~~

* Download the development version by either:

 - Using `git <https://git-scm.com/>`_ and run::

    git clone git://github.com/pyrf/pyrf.git

 - Or `download a stable release here <https://github.com/pyrf/pyrf/releases>`_ and extract

* Navigate to `pyrf` directory (``cd pyrf``), run::

    python setup.py install


PyRF API for ThinkRF RTSA Products
----------------------------------

:class:`pyrf.devices.thinkrf.WSA` is the class that provides access
to `ThinkRF Real-Time Spectrum Analyzers <https://www.thinkrf.com>`_
(RTSA, also formerly known as WSA) devices.
Its methods closely match the SCPI Command Set described in the product's
Programmer's Guide (available on
`ThinkRF Resources <http://www.thinkrf.com/resources>`_).

There are simple examples illustrating usage of this API under the `examples`
directory included with the source code directory.  Some are mentioned in the
:doc:`examples` section of this document .

This API may be used in a **blocking** mode (the default) or in an **asynchronous**
mode with using the `Twisted <https://twistedmatrix.com/>`_ python library.

In **blocking** mode, all methods that read from the device will wait
to receive a response before returning.

In **asynchronous** mode, all methods will send their commands to the device and
then immediately return a Twisted Deferred object.  If you need to wait for
the response or completion of this command, you can attach a callback to the
Deferred object and the Twisted reactor will call it when ready.  You may
choose to use Twisted's ``inlineCallbacks`` function decorator to write Twisted
code that resembles synchronous code by yielding the Deferred objects
returned from the API.

To use the **asynchronous**, when a WSA instance of a device (ex. ``dut = WSA()``) is created,
you must pass a :class:`pyrf.connectors.twisted_async.TwistedConnector`
instance as the connector parameter, as shown in :ref:`twisted-show-i-q`
