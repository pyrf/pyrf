Examples
========

These are some of the examples may be found in the "examples" directory included
with the PyRF source code.

Usage: python <filename>.py [device_IP_when_needed]

discovery.py / twisted_discovery.py
-----------------------------------

* `discovery.py <https://github.com/pyrf/pyrf/blob/master/examples/discovery.py>`_
* `twisted_discovery.py <https://github.com/pyrf/pyrf/blob/master/examples/twisted_discovery.py>`_

These examples detect RTSA devices on the local network

Example output:

.. code-block:: none

   R5500-427 180601-661 1.5.0 10.126.110.133
   R5500-408 171212-007 1.5.0 10.126.110.123
   R5500-418 180522-659 1.4.8 10.126.110.104

.. _twisted-show-i-q:

show_i_q.py / twisted_show_i_q.py
---------------------------------

These examples connect to a device specified on the command line,
tunes it to a center frequency of 2.450 MHz
then reads and displays one capture of 1024 i, q values.

* `show_i_q.py <https://github.com/pyrf/pyrf/blob/master/examples/show_i_q.py>`_
* `twisted_show_i_q.py <https://github.com/pyrf/pyrf/blob/master/examples/twisted_show_i_q.py>`_

Example output (truncated):

.. code-block:: none

   0,-20
   -8,-16
   0,-24
   -8,-12
   0,-32
   24,-24
   32,-16
   -12,-24
   -20,0
   12,-32
   32,-4
   0,12
   -20,-16
   -48,16
   -12,12
   0,-36
   4,-12


matplotlib_plot_sweep.py
------------------------

This example connects to a device specified on the command line,
and plots a complete sweep of the spectrum using NumPy_ and matplotlib_.

* `matplotlib_plot_sweep.py <https://github.com/pyrf/pyrf/blob/master/examples/matplotlib_plot_sweep.py>`_

.. _NumPy: http://numpy.scipy.org/
.. _matplotlib: http://matplotlib.org/


pyqtgraph_plot_block.py
-----------------------

This example connects to a device with IP specified on the command line,
tunes it to a center frequency of 2.450 MHz then continually captures
and displays an FFT in a GUI window using pyqtgraph_.

.. _pyqtgraph: http://pyqtgraph.org/

* `pyqtgraph_plot_block.py <https://github.com/pyrf/pyrf/blob/master/examples/pyqtgraph_plot_block.py>`_

pyqtgraph_plot_sweep.py
-----------------------

This example connects to a device with IP specified on the command line,
and makes use of sweep_device.py to perform a single sweep entry
monitoring and plot FFT results in a GUI window using pyqtgraph_.

.. _pyqtgraph: http://pyqtgraph.org/

* `pyqtgraph_plot_sweep.py <https://github.com/pyrf/pyrf/blob/master/examples/pyqtgraph_plot_sweep.py>`_
