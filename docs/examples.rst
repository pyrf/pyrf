
Examples
========

These examples may be found in the "examples" directory included
with the PyRF source code.

show_i_q.py
-----------

This example connects to a device specified on the command line,
tunes it to a center frequency of 2.450 MHz
then reads and displays one capture of 1024 i, q values.

.. literalinclude:: ../examples/show_i_q.py

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


plot_fft.py
-----------

This example connects to a device specified on the command line,
tunes it to a center frequency of 2.450 MHz
and sets a trigger for a signal with an amplitude of -70 dBm or
greater between 2.400 MHz and 2.480 MHz.

When the trigger is satisfied the data is captured and rendered
as a spectrum display using NumPy_ and matplotlib_.

.. _NumPy: http://numpy.scipy.org/
.. _matplotlib: http://matplotlib.org/

.. literalinclude:: ../examples/plot_fft.py

.. figure:: plot_fft.png
   :alt: plot_fft screen shot

   Example output of ``plot_fft.py``


.. _twisted-show-i-q:

twisted_show_i_q.py
-------------------

This is a Twisted version of the show_i_q.py example above.

.. literalinclude:: ../examples/twisted_show_i_q.py


.. _gui-source:

GUI Source
----------

These files may be found in the PyRF package under the "gui" directory.

wsa4000gui.py
~~~~~~~~~~~~~

This script adds nonblocking code using Twisted to the GUI application
and launches it from the ``main()`` function.

.. literalinclude:: ../pyrf/gui/wsa4000gui.py


gui.py
~~~~~~

The main application window and GUI controls are created here.

``MainWindow`` creates and handles the ``File | Open Device`` menu and
wraps the ``MainPanel`` widget responsible for most of the interface.

All the buttons and controls and their callback functions are built in
``MainPanel`` and arranged on a grid.  A ``SpectrumView`` is created
and placed to left of the controls.

.. literalinclude:: ../pyrf/gui/gui.py

spectrum.py
~~~~~~~~~~~

The ``SpectrumView`` widget is divided into three parts:

* ``SpectrumViewPlot`` contains the plotted spectrum data.
* ``SpectrumViewLeftAxis`` displays the dBm axis along the left.
* ``SpectrumViewBottomAxis`` displays the MHz axis across the bottom.

The utility functions ``dBm_labels`` and ``MHz_labels`` compute the
positions and labels for each axis.

.. literalinclude:: ../pyrf/gui/spectrum.py

util.py
~~~~~~~

Pretty-print frequency values

.. literalinclude:: ../pyrf/gui/util.py

wsa4000blocking.py
~~~~~~~~~~~~~~~~~~

This the launcher for the old version of the GUI that doesn't use
Twisted and may be run as ``wsa4000gui-blocking``.

.. literalinclude:: ../pyrf/gui/wsa4000blocking.py

.. note::

   This version calls ``MainPanel.update_screen()`` in a timer
   loop 20 times a second.  This method makes a blocking call to capture
   the next packet and render it all in the same thread as the application.
   This can make the interface slow or completely unresponsive if you
   lose connection to the device.


