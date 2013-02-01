
Reference
=========

pyrf.devices
------------

.thinkrf
~~~~~~~~

.. module:: pyrf.devices.thinkrf

.. autoclass:: WSA4000

   .. automethod:: antenna(number=None)

   .. automethod:: capture(spp, ppb)

   .. automethod:: connect(host)

   .. automethod:: decimation(value=None)

   .. automethod:: disconnect()

   .. automethod:: eof()

   .. automethod:: flush()

   .. automethod:: flush_captures()

   .. automethod:: freq(freq=None)

   .. automethod:: fshift(shift=None)

   .. automethod:: gain(gain=None)

   .. automethod:: has_data()

   .. automethod:: have_read_perm()

   .. automethod:: id()

   .. automethod:: ifgain(gain=None)

   .. automethod:: locked(modulestr)

   .. automethod:: preselect_filter(enable=None)

   .. automethod:: raw_read(num)

   .. automethod:: read()

   .. automethod:: request_read_perm()

   .. automethod:: reset()

   .. automethod:: scpiget(cmd)

   .. automethod:: scpiset(cmd)

   .. automethod:: sweep_add(entry)

   .. automethod:: sweep_clear()

   .. automethod:: sweep_read(index)

   .. automethod:: sweep_start(start_id=None)

   .. automethod:: sweep_stop()

   .. automethod:: trigger(settings=None)


pyrf.connectors
---------------

.blocking
~~~~~~~~~

.. automodule:: pyrf.connectors.blocking
   :members:
   :undoc-members:

.twisted_async
~~~~~~~~~~~~~~

.. automodule:: pyrf.connectors.twisted_async
   :members:
   :undoc-members:

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

pyrf.twisted_util
-----------------

.. automodule:: pyrf.twisted_util
   :members:
   :undoc-members:

pyrf.util
---------

.. module:: pyrf.util

.. autofunction:: pyrf.util.read_data_and_context


pyrf.vrt
--------

.. automodule:: pyrf.vrt
   :members:
   :undoc-members:

