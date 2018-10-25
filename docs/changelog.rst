
Change Logs
===========

PyRF 2.9.1
----------

 * Updated this PyRF Manual/Documentation
 * Added more examples

PyRF 2.9.0
----------

2018-10-12

 * Added GNSS support for R5700 RTSA products including VRT GNSS context packet
 * Added support for R5500 products
 * Added flush and reset to capture setup
 * Added calibrate_time_domain() function for a given time-domain data point
 * Added calculate_occupied_bw() function for a given spectrum and occupied percentage
 * Refactored sweep_device functions
 * Restructured ThinkRF device properties and removed deprecated ones
 * Improved IQ offset algorithm
 * Enabled "100 kHz span" (HDR mode) for R5500 products
 * Enabled trigger feature
 * Changed Baseband (DD mode)'s MIN_TUNABLE to 32.25 MHz
 * Changed R5500's minimum frequency to 10 kHz
 * Changed WSA5000's minimum frequency to 100 kHz
 * Changed minimum sample size for sweep to be 32
 * Fixed zero-span setting
 * Fixed bugs related to RBW setup
 * Fixed bugs related sweep setup
 * Fixed lock-up issue due to unexpected data packet received
 * Fixed attenuation setting for R5500
 * Fixed sample sizes being off by 32 samples
 * Fixed capture_device bug related to number of data points
 * Fixed bugs related to CSV file and settings


PyRF 2.8.0
----------

2015-08-12

 * Removed RTSA Instructions from the web page
 * Fixed windows installation instructions
 * Added capture spectrum function
 * Added find peak function
 * Added Measure noisefloor function
 * Changed default span settings
 * Added saturation level value for each device

PyRF 2.7.2
----------

2014-12-16

 * Added capture control widget
 * Changed default save file names to represent date and time of capture
 * Fixed baseband mode frequency axis issue
 * Netifaces library is no longer a hard requirement
 * Improved overall marker controls
 * Added 'Enable mouse tune' option to frequency widget
 * Default HDR gain is now 25

PyRF 2.7.1
----------

2014-11-13

 * Discovery widget now queries for new WSA's on the network every 10 seconds
 * Fixed issue where switching from sweep to non-sweep wrongly changed center frequency
 * Fixed issue where Minimum control not behaving as designed
 * Fixed issue where trigger controls were not disabled for non-trigger modes
 * Fixed frequency axis texts
 * Y-axis in the persistence plot now corresponds with spectral plot's y-axis

PyRF 2.7.0
----------

2014-11-04

 * All control widgets are now dockable
 * Enabled mouse control of spectral plot's y-axis
 * Added lower RBW values in non-sweep modes

PyRF 2.6.2
----------

2014-10-10

 * HDR gain control in GUI now allows values up to +20 dB
 * Sweep ZIF (100 MHz steps) now only shown in GUI when developer menu is
   enabled
 * GUI PLL Reference control now works in Sweep mode
 * Darkened trace color in GUI for attenuated edges and dc offset now matches
   trace color
 * Alternate sweep step color in GUI now matches trace color
 * DC offset region now limited to middle three bins in GUI (was expanding
   when decimation was applied)
 * Correction to usable region in ZIF and SH modes with decimation applied
 * Fixed HDR center offset value
 * Added device information dialog to GUI

PyRF 2.6.1
----------

2014-09-30

 * Upload corrected version with changelog

PyRF 2.6.0
----------

2014-09-30

 * Added channel power measurement feature to GUI
 * Added Export to CSV feature to GUI for saving streams of processed
   power spectrum data
 * Added a power level cursor (adjustable horizontal line) to GUI
 * Added reference level offset adjustment box to GUI
 * Trigger region in GUI is now a rectangle to make it visibly different
   than channel power measurement controls
 * Update mode drop-down in GUI to include information about each mode
   instead of showing internal mode names
 * Use netifaces for address detection to fix discover issue on
   non-English windows machines

PyRF 2.5.0
----------

2014-09-09

 * Added Persistence plot
 * Made markers drag-able in the plot
 * Added version number to title bar
 * Moved DSP options to developer menu, developer menu now hidden
   unless GUI run with -d option
 * Rounded center to nearest tuning resolution step in GUI
 * Fixed a number of GUI control and label issues
 * Moved changelog into docs and updated

PyRF 2.4.1
----------

2014-08-19

 * Added missing requirement
 * Fixed use with CONNECTOR IQ path

PyRF 2.4.0
----------

2014-08-19

 * Improved trigger controls
 * Fixed modes available with some WSA versions

PyRF 2.3.0
----------

2014-08-12

 * Added full playback support (including sweep) in GUI
 * Added hdr_gain control to WSA class
 * Added average mode and clear button for traces
 * Added handling for different REFLEVEL_ERROR on early firmware versions
 * Disable triggers for unsupported WSA firmware versions
 * Added free plot adjustment developer option
 * Fixed a number of GUI interface issues

PyRF 2.2.0
----------

2014-07-15

 * Added waterfall display for GUI and example program
 * Added automatic re-tuning when plot dragged of zoomed
 * Added recording speca state in recorded VRT files, Start/Stop recording menu
 * Added GUI non-sweep playback support and command line '-p' option
 * Added marker controls: peak left, right, center to marker
 * Redesigned frequency controls, device controls and trace controls
 * Default to Sweep SH mode in GUI
 * Added developer options menu for attenuated edges etc.
 * Refactored shared GUI code and panels
 * SweepDevice now returns numpy arrays of dBm values
 * Fixed device discovery with multiple interfaces
 * Replaced reflevel adjustment properties with REFLEVEL_ERROR value
 * Renamed GUI launcher to rtsa-gui

PyRF 2.1.0
----------

2014-06-20

 * Refactored GUI code to separate out device control and state
 * Added SPECA defaults to device properties
 * Restored trigger controls in GUI
 * Added DSP panel to control fft calculations in GUI
 * Fixed a number of GUI plot issues

PyRF 2.0.3
----------

2014-06-03

 * Added simple QT GUI example with frequency, attenuation and rbw controls
 * Added support for more hardware versions
 * Fixed plotting issues in a number of modes in GUI

PyRF 2.0.2
----------

2014-04-29

 * Removed Sweep ZIF mode from GUI
 * Fixed RFE input mode GUI issues

PyRF 2.0.1
----------

2014-04-21

 * Added Sweep SH mode support to SweepDevice
 * Added IQ in, DD, SHN RFE modes to GUI
 * Added IQ output path and PLL reference controls to GUI
 * Added discovery widget to GUI for finding devices
 * Fixed a number of issues

PyRF 2.0.0
----------

2014-01-31
 * Added multiple traces and trace controls to GUI
 * Added constellation and IQ plots
 * Added raw VRT capture-to-file support
 * Updated SweepDevice sweep plan calculation
 * Created separate GUI for single capture modes
 * Updated device properties for WSA5000 RFE modes
 * Show attenuated edges in gray, sweep steps in different colors in GUI
 * Added decimation and frequency shift controls to single capture GUI
 * Fixed many issues with WSA5000 different RFE mode support
 * Removed trigger controls, waiting for hardware support
 * Switched to using pyinstaller for better windows build support

PyRF 1.2.0
----------

2013-10-01
 * Added WSA5000 support
 * Added WSA discovery example scripts
 * Renamed WSA4000 class to WSA (supports WSA5000 as well)
 * Separated device properties from WSA class

PyRF 1.1.0
----------

2013-07-19
 * Fixed some py2exe issues
 * Show the GUI even when not connected

PyRF 1.0.0
----------

2013-07-18

 * Switched to pyqtgraph for spectrum plot
 * Added trigger controls
 * Added markers
 * Added hotkeys for control
 * Added bandwidth control
 * Renamed GUI launcher speca-gui
 * Created SweepDevice to generalize spectrum analyzer-type function
 * Created CaptureDevice to collect single captures and related context

PyRF 0.4.0
----------

2013-05-18

 * pyrf.connectors.twisted_async.TwistedConnector now has a
   vrt_callback attribute for setting a function to call when
   VRT packets are received.

   This new callback takes a single parameter: a pyrf.vrt.DataPacket
   or pyrf.vrt.ContextPacket instance.

   The old method of emulating a synchronous read() interface
   from a pyrf.devices.thinkrf.WSA4000 instance is no longer
   supported, and will now raise a
   pyrf.connectors.twisted_async.TwistedConnectorError exception.
 * New methods added to pyrf.devices.thinkrf.WSA4000: abort(),
   spp(), ppb(), stream_start(), stream_stop(), stream_status()
 * Added support for stream ID context packets and provide a value
   for sweep ID context packet not converted to a hex string
 * wsa4000gui updated to use vrt callback
 * "wsa4000gui -v" enables verbose mode which currently shows SCPI
   commands sent and responses received on stdout
 * Added examples/stream.py example for testing stream data rate
 * Updated examples/twisted_show_i_q.py for new vrt_callback
 * Removed pyrf.twisted_util module which implemented old
   synchronous read() interface
 * Removed now unused pyrf.connectors.twisted_async.VRTTooMuchData
   exception
 * Removed wsa4000gui-blocking script
 * Fix for power spectrum calculation in pyrf.numpy_util

PyRF 0.3.0
----------

2013-02-01

 * API now allows asynchronous use with TwistedConnector
 * GUI now uses asynchronous mode, but synchronous version may still
   be built as wsa4000gui-blocking
 * GUI moved from examples to inside the package at pyrf.gui and built
   from the same setup.py
 * add Twisted version of show_i_q.py example
 * documentation: installation instructions, requirements, py2exe
   instructions, user manual and many other changes
 * fix support for reading WSA4000 very low frequency range
 * pyrf.util.read_data_and_reflevel() was renamed to
   read_data_and_context()
 * pyrf.util.socketread() was moved to
   pyrf.connectors.blocking.socketread()
 * added requirements.txt for building dependencies from source

PyRF 0.2.5
----------

2013-01-26

 * fix for compute_fft calculations

PyRF 0.2.4
----------

2013-01-19

 * fix for missing devices file in setup.py

PyRF 0.2.3
----------

2013-01-19

 * add planned features to docs

PyRF 0.2.2
----------

2013-01-17

 * rename package from python-thinkrf to PyRF

python-thinkrf 0.2.1
--------------------

2012-12-21

 * update for WSA4000 firmware 2.5.3 decimation change

python-thinkrf 0.2.0
--------------------

2012-12-09

 * GUI: add BPF toggle, Antenna switching, --reset option, "Open Device"
   dialog, IF Gain control, Span control, RBW control, update freq on
   finished editing
 * create basic documentation and reference and improve docstrings
 * bug fixes for GUI, py2exe setup.py
 * GUI perfomance improvements

python-thinkrf 0.1.0
--------------------

2012-12-01

 * initial release
