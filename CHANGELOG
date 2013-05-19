2013-05-18 PyRF 0.4.0

    * pyrf.connectors.twisted_async.TwistedConnector now has a
      vrt_callback attribute for setting a function to call when
      VRT packets are received.

      This new callback takes a single parameter: a pyrf.vrt.DataPacket
      or pyrf.vrt.ContextPacket instance.

      The old method of emulating a synchronous read() interface
      from a pyrf.devices.thinkrf.WSA4000 instance is no longer
      supported, and will now raise a
      pyrf.connectors.twisted_async.TwistedConnectorError exception.

    * New methods added to pyrf.devices.thinkrf.WSA4000: abort(),
      spp(), ppb(), stream_start(), stream_stop(), stream_status()

    * Added support for stream ID context packets and provide a value
      for sweep ID context packet not converted to a hex string

    * wsa4000gui updated to use vrt callback

    * "wsa4000gui -v" enables verbose mode which currently shows SCPI
      commands sent and responses received on stdout

    * Added examples/stream.py example for testing stream data rate

    * Updated examples/twisted_show_i_q.py for new vrt_callback

    * Removed pyrf.twisted_util module which implemented old
      synchronous read() interface

    * Removed now unused pyrf.connectors.twisted_async.VRTTooMuchData
      exception

    * Removed wsa4000gui-blocking script

    * Fix for power spectrum calculation in pyrf.numpy_util

2013-02-01 PyRF 0.3.0

    * API now allows asynchronous use with TwistedConnector

    * GUI now uses asynchronous mode, but synchronous version may still
      be built as wsa4000gui-blocking

    * GUI moved from examples to inside the package at pyrf.gui and built
      from the same setup.py

    * add Twisted version of show_i_q.py example

    * documentation: installation instructions, requirements, py2exe
      instructions, user manual and many other changes

    * fix support for reading WSA4000 very low frequency range

    * pyrf.util.read_data_and_reflevel() was renamed to
      read_data_and_context()

    * pyrf.util.socketread() was moved to
      pyrf.connectors.blocking.socketread()

    * added requirements.txt for building dependencies from source

2013-01-26 PyRF 0.2.5

    * fix for compute_fft calculations

2013-01-19 PyRF 0.2.4

    * fix for missing devices file in setup.py

2013-01-19 PyRF 0.2.3

    * add planned features to docs

2013-01-17 PyRF 0.2.2

    * rename package from python-thinkrf to PyRF

2012-12-21 python-thinkrf 0.2.1

    * update for WSA4000 firmware 2.5.3 decimation change

2012-12-09 python-thinkrf 0.2.0

    * GUI: add BPF toggle, Antenna switching, --reset option, "Open Device"
      dialog, IF Gain control, Span control, RBW control, update freq on
      finished editing

    * create basic documentation and reference and improve docstrings

    * bug fixes for GUI, py2exe setup.py

    * GUI perfomance improvements

2012-12-01 python-thinkrf 0.1.0

    * initial release
