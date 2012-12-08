
.. _demo-gui:

GUI Example: wsa4000demo
========================

``wsa4000demo`` is a cross-platform GUI application built with the
Qt_ toolkit and PySide_ bindings for Python.

.. _Qt: http://qt.digia.com/
.. _PySide: http://qt-project.org/wiki/PySide

You may run application by launching the ``wsa4000demo.py`` script in
the ``examples/gui`` directory.

You may specify a device on the command line or open a device after the
GUI has launched.  Adding ``--reset`` to the command line parameters
will cause the device to be reset to defaults after connecting.

wsa4000demo.py
--------------

This is the script that launches the application.

.. literalinclude:: ../examples/gui/wsa4000demo.py

gui.py
------

The main application window and GUI controls are created here.

``MainWindow`` creates and handles the ``File | Open Device`` menu and
wraps the ``MainPanel`` widget responsible for most of the interface.

All the buttons and controls and their callback functions are built in
``MainPanel`` and arranged on a grid.  A ``SpectrumView`` is created
and placed to left of the controls.

.. note::

   This version calls ``MainPanel.update_screen()`` in a timer
   loop 20 times a second.  This method makes a blocking call to capture
   the next packet and render it all in the same thread as the application.
   This can make the interface slow or completely unresponsive if you
   lose connection to the device.

   The next release will move the blocking call and data processing
   into a separate process.

.. literalinclude:: ../examples/gui/gui.py

spectrum.py
-----------

The ``SpectrumView`` widget is divided into three parts:

* ``SpectrumViewPlot`` contains the plotted spectrum data.
* ``SpectrumViewLeftAxis`` displays the dBm axis along the left.
* ``SpectrumViewBottomAxis`` displays the MHz axis across the bottom.

The utility functions ``dBm_labels`` and ``MHz_labels`` compute the
positions and labels for each axis.

.. literalinclude:: ../examples/gui/spectrum.py

util.py
-------

Pretty-print frequency values

.. literalinclude:: ../examples/gui/util.py
