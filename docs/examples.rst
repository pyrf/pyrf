
Examples
========

These examples may be found in the "examples" directory included
with the PyRF source code.


discovery.py / twisted_discovery.py
-----------------------------------

* `discovery.py <https://github.com/pyrf/pyrf/blob/master/examples/discovery.py>`_
* `twisted_discovery.py <https://github.com/pyrf/pyrf/blob/master/examples/twisted_discovery.py>`_

These examples detect WSA devices on the same network

Example output:

.. code-block:: none

   WSA4000 00:50:c2:ea:29:14 None at 10.126.110.111
   WSA4000 00:50:c2:ea:29:26 None at 10.126.110.113


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


matplotlib_trigger_plot_fft.py
------------------------------

This example connects to a device specified on the command line,
tunes it to a center frequency of 2.450 MHz
and sets a trigger for a signal with an amplitude of -70 dBm or
greater between 2.400 MHz and 2.480 MHz.

* `matplotlib_trigger_plot_fft.py <https://github.com/pyrf/pyrf/blob/master/examples/matplotlib_trigger_plot_fft.py>`_

.. figure:: plot_fft.png
   :alt: matplotlib_trigger_plot_fft screen shot

   Example output of ``matplotlib_trigger_plot_fft.py``


