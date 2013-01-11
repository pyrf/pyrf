
Planned Development
===================

Blocking Sockets
----------------

This library will continue to be usable in a simple
blocking-socket manner the way the current GUI example does.

Simple data capture and processing needs can be accomplished
with few lines of code.

Twisted and Async
-----------------

The device API is being extended so that it can also work with a
provided non-blocking `Twisted <http://twistedmatrix.com/>`_ API,
or any other async library the user chooses to add support for.

The simplest Twisted use will have all processing blocks in the same
process, much like the current GUI example but without the problem
of the UI freezing when no data is arriving from the device.  This mode
is the simplest for the programmer and incurrs no cost for passing data
from one processing block to the next.

.. graphviz::

   digraph processing {
      WSA4000 [shape=box];
      WSA4000 -> FFT;
      FFT -> calibrate;
      calibrate -> spectrum;
      spectrum [shape=box];
   }


.. code-block:: python

   wsa = WSA4000(host)
   fft = fft_block(wsa)
   calibrate = calibrate_block(fft)
   spectrum = spectrum_display(calibrate)


Processing Blocks
-----------------

Processing blocks will use Python interfaces based on zope.interface
to describe connections that may be made from consumer to producer.

Consumers will connect to their configured producers only if they
are not producers (e.g. a graph renderer) or if all their required
producer interfaces have consumers connected.

.. graphviz::

   digraph processing {
      WSA4000 [shape=box];
      WSA4000 -> FFT [style=dotted];
      FFT -> calibrate [style=dotted];
   }


.. code-block:: python

   wsa = WSA4000(host)
   fft = fft_block(wsa)
   calibrate = calibrate_block(fft)

Multiprocess and HTTP
---------------------

Using multiple cores for data processing will be accomplished by
grouping some or all processing blocks into separate processes. These
processes will pass data with long-polling HTTP requests at the
boundaries.

HTTP Headers will be used to indicate the type of data/packet being
sent.  The body will contain the raw packet bytes.

.. graphviz::

   digraph processing {
      WSA4000_1 [shape=box];
      WSA4000_2 [shape=box];
      subgraph cluster1 {
	 label = "process #1";
	 FFT_1 -> calibrate_1;
      }
      subgraph cluster2 {
	 label = "process #2";
	 FFT_2 -> calibrate_2;
      }
      WSA4000_1 -> FFT_1;
      WSA4000_2 -> FFT_2;
      calibrate_1 -> multi_spectrum;
      calibrate_2 -> multi_spectrum;
      multi_spectrum [shape=box];
   }


.. code-block:: python

   process1 = process()
   process2 = process()
   wsa1 = WSA4000(host1)
   fft1 = fft_block(wsa1, proc=process1)
   calibrate1 = calibrate_block(fft1, proc=process1)
   wsa2 = WSA4000(host2)
   fft2 = fft_block(wsa2, proc=process2)
   calibrate2 = calibrate_block(fft2, proc=process2)
   multi_spectrum = multi_spectrum_display(calibrate1, calibrate2)


Distributed
-----------

HTTP servers work across different machines without modification.
Setting up a distributed processing chain across separate machines
will be possible to set up, but will require some more manual
configuration than multiprocess configuration.

Authentication between machines is outside the scope of this library.

Extending the process block deployment across machines in an easier
way (with ssh, for example) is a possible future enhancement.

