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

(Or `Download a Stable Release Tarball <https://github.com/pyrf/pyrf/tags>`_)

Then Install from Source or Extracted Tarball::

   python setup.py install


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

.. seealso:: :ref:`gui-source`
