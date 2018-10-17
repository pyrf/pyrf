Reference
=========

pyrf.devices
------------

.thinkrf
~~~~~~~~

.. module:: pyrf.devices.thinkrf

.. autoclass:: WSA

   .. automethod:: abort()

   .. automethod:: apply_device_settings(settings, force_change=False)

   .. automethod:: async_connector()

   .. automethod:: attenuator(atten_val=None)

   .. automethod:: capture(spp, ppb)

   .. automethod:: capture_mode()

   .. automethod:: connect(host)

   .. automethod:: decimation(value=None)

   .. automethod:: disconnect()

   .. automethod:: eof()

   .. automethod:: errors()

   .. automethod:: flush()

   .. automethod:: freq(freq=None)

   .. automethod:: fshift(shift=None)

   .. automethod:: has_data()

   .. automethod:: have_read_perm()

   .. automethod:: hdr_gain(gain=None)

   .. automethod:: id()

   .. automethod:: inject_recording_state(state)

   .. automethod:: iq_output_path(path=None)

   .. automethod:: locked(modulestr)

   .. automethod:: measure_noisefloor(rbw=None, average=1)

   .. automethod:: peakfind(n=1, rbw=None, average=1)

   .. automethod:: pll_reference(src)

   .. automethod:: ppb(packets=None)

   .. automethod:: psfm_gain(gain=None)

   .. automethod:: raw_read(num)

   .. automethod:: read()

   .. automethod:: read_data(spp)

   .. automethod:: request_read_perm()

   .. automethod:: reset()

   .. automethod:: rfe_mode(mode=None)

   .. automethod:: scpiget(cmd)

   .. automethod:: scpiset(cmd)

   .. automethod:: set_async_callback(callback)

   .. automethod:: set_recording_output(output_file=None)

   .. automethod:: spp(samples=None)

   .. automethod:: stream_start(stream_id=None)

   .. automethod:: stream_status()

   .. automethod:: stream_stop()

   .. automethod:: sweep_add(entry)

   .. automethod:: sweep_clear()

   .. automethod:: sweep_iterations(count=None)

   .. automethod:: sweep_read(index)

   .. automethod:: sweep_start(start_id=None)

   .. automethod:: sweep_stop()

   .. automethod:: trigger(settings=None)

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
   :undoc-members:


pyrf.numpy_util
---------------

.. automodule:: pyrf.numpy_util
   :members:
   :undoc-members:


pyrf.util
---------

.. module:: pyrf.util

.. autofunction:: pyrf.util.read_data_and_context

.. autofunction:: pyrf.util.collect_data_and_context


pyrf.vrt
--------

.. automodule:: pyrf.vrt
   :members:
   :undoc-members:
