
.. image:: pyrf_logo.png
   :alt: PyRF logo

PyRF Documentation
==================

** Note **
----------

As of January 2024, pyRF3 (the superseded version of pyRF) version is **deprecated** and has been replaced by the **libtrf API** (C++/C), for which a sample pyRF4 binding is available upon request.

pyRF3 remains functional all R5xx0 features released prior to 2024; however, it does not support the newer RTSA products or the R55x0/R57x0 features introduced after 2024. This API is to be used as is.

Contact `Support <https://support.thinkrf.com/support/home>`_ or support@thinkrf.com for more information.

**References:**

* `ThinkRF APIs <https://thinkrf.com/documentation-2/software-apis/>`_
* `Spectraware Spectrum Viewer (replacement for S240v5) <https://thinkrf.com/real-time-spectrum-analyzers/spectraware-spectrum-analysis-software/>`_
* `ThinkRF RTSA Documentation and Resources <https://thinkrf.com/documentation/>`_

Overview
--------

PyRF is an openly available, comprehensive development environment for wireless signal analysis. PyRF handles the low-level details of configuring a device, real-time data acquisition and signal processing, allowing you to concentrate on your analysis solutions. Hence, it enables rapid development of powerful applications that leverage the new generation of measurement-grade software-defined radio technology, such as `ThinkRF Real-Time Spectrum Analysis Software`_.

.. _ThinkRF Real-Time Spectrum Analysis Software: https://www.thinkrf.com/s240-real-time-spectrum-analysis-software/

PyRF is built on the `Python Programming Language <https://www.python.org/>`_ (v2.7) and includes feature-rich libraries, examples including visualization applications and source code, all specific to the requirements of signal analysis. It is openly available, allowing commercialization of solutions through BSD open licensing and offering device independence via standard hardware APIs.


.. image:: PyRF-Block-Diagram1.png
   :alt: PyRF block diagram

Table of Contents
-----------------

   .. toctree::
      :maxdepth: 2

      usermanual
      reference
      examples
      changelog

Hardware Support
----------------

This library currently supports development for the following `ThinkRF Real-Time Spectrum Analyzer (RTSA) <https://www.thinkrf.com>`_ platforms:

* R5500
* R5700
* WSA5000 (EOL)

Links
-----

* `Official PyRF github page <https://github.com/pyrf/pyrf>`_
* `PyRF Documentation <https://www.pyrf.org>`_

Indices and Tables
------------------

* :ref:`genindex`
* :ref:`search`
