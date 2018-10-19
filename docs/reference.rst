Reference
=========

pyrf.devices
------------

.thinkrf
~~~~~~~~

.. module:: pyrf.devices.thinkrf

.. autoclass:: WSA

 The methods are grouped and listed by functionalities.

 **Connection Related Methods:**

   .. automethod:: connect(host)

   .. automethod:: disconnect()

   .. automethod:: async_connector()

   .. automethod:: set_async_callback(callback)

 **Direct SCPI commands:**

   .. automethod:: scpiget(cmd)

   .. automethod:: scpiset(cmd)

   .. automethod:: errors()

 **Device System Related:**

   .. automethod:: id()

   .. automethod:: reset()

   .. automethod:: locked(modulestr)

 **Data Acquisition Related Methods:**

  - Get permission:

   .. automethod:: has_data()

   .. automethod:: request_read_perm()

   .. automethod:: have_read_perm()

  - Set capture size for stream or block mode capture:

   .. automethod:: ppb(packets=None)

   .. automethod:: spp(samples=None)

  - Stream setup

   .. automethod:: stream_status()

   .. automethod:: stream_start(stream_id=None)

   .. automethod:: stream_stop()

  - Sweep setup:

   .. automethod:: sweep_add(entry)

   .. automethod:: sweep_clear()

   .. automethod:: sweep_iterations(count=None)

   .. automethod:: sweep_read(index)

   .. automethod:: sweep_start(start_id=None)

   .. automethod:: sweep_stop()

  - VRT data acquisition related methods:

   .. automethod:: capture(spp, ppb)

   .. automethod:: capture_mode()

   .. automethod:: raw_read(num)

   .. automethod:: read()

   .. automethod:: read_data(spp)

   .. automethod:: abort()

   .. automethod:: flush()

   .. automethod:: eof()

 **Device Configuration Methods for Non-Sweep Setup:**

   .. automethod:: attenuator(atten_val=None)

   .. automethod:: decimation(value=None)

   .. automethod:: freq(freq=None)

   .. automethod:: fshift(shift=None)

   .. automethod:: hdr_gain(gain=None)

   .. automethod:: iq_output_path(path=None)

   .. automethod:: pll_reference(src=None)

   .. automethod:: psfm_gain(gain=None)

   .. automethod:: rfe_mode(mode=None)

   .. automethod:: trigger(settings=None)

   .. automethod:: apply_device_settings(settings, force_change=False)

 **DSP and Data Processing Related Methods:**

  .. automethod:: measure_noisefloor(rbw=None, average=1)

  .. automethod:: peakfind(n=1, rbw=None, average=1)

 **Data Recording Related Methods:**

   .. automethod:: inject_recording_state(state)

   .. automethod:: set_recording_output(output_file=None)

**Device Discovery Functions:**

.. autofunction:: discover_wsa(wait_time=0.125)

.. autofunction:: parse_discovery_response(response)


pyrf.connectors
---------------

.blocking
~~~~~~~~~

.. automodule:: pyrf.connectors.blocking
   :members:
   :no-undoc-members:
   :exclude-members: sync_async


.twisted_async
~~~~~~~~~~~~~~

.. automodule:: pyrf.connectors.twisted_async
   :members:
   :no-undoc-members:


pyrf.capture_device
-------------------

.. automodule:: pyrf.capture_device
   :members:
   :no-undoc-members:


pyrf.sweep_device
-----------------

.. automodule:: pyrf.sweep_device
   :members:
   :no-undoc-members:
   :exclude-members: plan_sweep


pyrf.config
-----------

.. automodule:: pyrf.config
   :members:
   :no-undoc-members:


pyrf.numpy_util
---------------

.. automodule:: pyrf.numpy_util
   :members:
   :no-undoc-members:


pyrf.util
---------

.. module:: pyrf.util

.. autofunction:: pyrf.util.capture_spectrum

.. autofunction:: pyrf.util.read_data_and_context

pyrf.vrt
--------

.. automodule:: pyrf.vrt
   :members:
   :no-undoc-members:
   :exclude-members: DataArray, generate_speca_packet
