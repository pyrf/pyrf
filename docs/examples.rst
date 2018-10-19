Examples
========

This section explains **some** of the `examples <https://github.com/pyrf/pyrf/blob/master/examples/>`_ included with the PyRF source code.

Typical Usage::

    python <example_file>.py [device_IP_when_needed]

.. _twisted-show-i-q:

discovery.py / twisted_discovery.py
-----------------------------------

* `discovery.py <https://github.com/pyrf/pyrf/blob/master/examples/discovery.py>`_
* `twisted_discovery.py <https://github.com/pyrf/pyrf/blob/master/examples/twisted_discovery.py>`_

These examples detect RTSA devices on the local network.

Example output:

.. code-block:: none

   R5700-427 180601-661 1.5.0 10.126.110.133
   R5500-408 171212-007 1.5.0 10.126.110.123
   R5500-418 180522-659 1.4.8 10.126.110.104


show_i_q.py / twisted_show_i_q.py
---------------------------------

These examples connect to a device of IP specified on the command line,
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


pyqtgraph_plot_single_capture.py / pyqtgraph_plot_block.py
----------------------------------------------------------

These examples connect to a device of IP specified on the command line,
tunes it to a center frequency, then continually capture
and display the computed spectral data using `pyqtgraph <http://pyqtgraph.org/>`_.

* `pyqtgraph_plot_single_capture.py <https://github.com/pyrf/pyrf/blob/master/examples/pyqtgraph_plot_single_capture.py>`_
* `pyqtgraph_plot_block.py <https://github.com/pyrf/pyrf/blob/master/examples/pyqtgraph_plot_block.py>`_

pyqtgraph_plot_sweep.py
-----------------------

This example connects to a device of IP specified on the command line,
makes use of sweep_device.py to perform a single sweep entry
monitoring and plots computed spectral results using `pyqtgraph <http://pyqtgraph.org/>`_.

* `pyqtgraph_plot_sweep.py <https://github.com/pyrf/pyrf/blob/master/examples/pyqtgraph_plot_sweep.py>`_


matplotlib_plot_sweep.py
------------------------

This example connects to a device specified on the command line,
and plots a large sweep of the spectrum using NumPy_ and matplotlib_.

* `matplotlib_plot_sweep.py <https://github.com/pyrf/pyrf/blob/master/examples/matplotlib_plot_sweep.py>`_

.. _NumPy: http://numpy.scipy.org/
.. _matplotlib: http://matplotlib.org/


simple_gui
----------
This folder contains a simple example on creating a GUI (using `pyqtgraph <http://pyqtgraph.org/>`_ along with `Twisted <https://twistedmatrix.com/>`_) to plot real-time data acquired from ThinkRF's RTSA device.  It displays the spectral density data in the top plot, and the raw I &/or Q data (when available) in the lower plot.

* `simple_gui <https://github.com/pyrf/pyrf/blob/master/examples/example_gui/>`_

Usage::

    python run_gui.py <device_ip>
