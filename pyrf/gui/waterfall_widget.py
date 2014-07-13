import collections
import threading
import time
import itertools
import ctypes
import Queue

# import required libraries
from PySide import QtGui, QtCore
import pyqtgraph as pg
import pyqtgraph.functions as pgfuncs
import sys
import numpy as np


FRAME_WAIT_TIMEOUT_s = 0.2
CROSSHAIR_FPS = 10.0

DLOG_ENABLED = True and __debug__

DLOG_start_time = None
def dlog(msg):
    """Simple debug logging function."""
    if DLOG_ENABLED:
        global DLOG_start_time
        if DLOG_start_time is None:
            DLOG_start_time = time.time()
        print "%5.3f - %s" % (time.time() - DLOG_start_time, msg)


class WaterfallModel(QtCore.QObject):
    sigNewDataRow = QtCore.Signal(tuple) #(time_s, data_row, metadata)
    
    #Could also be a playback history model?
    
    #This is screaming for dataframes.
    
    #Assumption is that it will be a FIFO, scope-style. ie: fast data
    #arrivals going on for a long time, with old data dropping away.
    
    #for SpectralLog:
    # - abscissa = frequency array
    # - data = spectra
    #this is crying for pandas
    
    #If willing to pre-allocate the full potential FIFO history, some
    #(minor?) performance improvement might be obtainable by rotating a row
    #pointer (FIFO-style) through a big numpy array. This could be a future
    #option (deques are easy for now, and were quick to get going initially).
    
    #Also may consider having the double-buffered circular buffer down at the
    #model level, but it is probably better to allow massive amounts of model
    #data without 2x the memory. If profiling really shows that copy memory
    #from the deque is the limiter (unlikely), this could be changed.
    def __init__(self, x_data, max_len):
        self._start_time_s = 0.0
        self._x_data = x_data
        self._min_x = np.min(x_data)
        self._max_x = np.max(x_data)
        self._x_len = len(x_data)
        self._max_len = max_len
        
        self._history = collections.deque() #of (timestamp_s, data, metadata)
        
        self._mutex = threading.RLock()
        
        super(WaterfallModel, self).__init__()
    
    def add_row(self, data, metadata = None, timestamp_s = None):
        assert len(data) == self._x_len
        assert data.ndim == 1
        if timestamp_s is None:
            timestamp_s = time.time()
        
        with self._mutex:
            data_tuple = (timestamp_s, data, metadata)
            self._history.append(data_tuple)
            if len(self._history) > self._max_len:
                self._history.popleft()
            self.sigNewDataRow.emit(data_tuple)
    
    def get_all_data(self):
        with self._mutex:
            #deque iterator efficiency *should* be fine with this generator...
            # - deque indexing is NOT efficient
            if self._history:
                data_arrays = (d[1] for d in self._history)
                all_data = np.vstack(tuple(data_arrays)).T
            else:
                all_data = np.ndarray((0, self._x_len))
        return all_data
    
    def get_latest_data(self, num_rows, pad_black = True):
        #st = time.time()
        with self._mutex:
            if self._history:
                no_data = False
                #use the deque's fast iterator to get num_rows, starting with
                #the latest (which is the last element in the deque since we
                #add to the end)...
                # - result is that the oldest (of num_rows) is at the end/bottom,
                #    which is what we want.
                data_iter = itertools.islice(reversed(self._history), num_rows)
                #materialize as a tuple of so we can vstack them...
                data_arrays = tuple(d[1] for d in data_iter)
            else:
                no_data = True
        
        if no_data:
            #no rows added yet!  We return an empty array of proper width...
            if pad_black:
                all_data = np.NINF * np.ones((num_rows, self._x_len))
            else:
                all_data = np.ndarray((0, self._x_len))
        else:
            #make the 2D array with vstack...
            all_data = np.vstack(data_arrays)
            if pad_black and (num_rows > len(data_arrays)):
                #make just enough 'black' rows to pad to the provided number
                #of rows...
                ones_padding = np.ones((num_rows - len(data_arrays), self._x_len))
                black_padding = ones_padding * np.NINF
                #black_padding = ones_padding * 0
                #stack the black padding below the actual waterfall data
                all_data = np.vstack((all_data, black_padding))
        #data = np.rot90(all_data, 3)
        data = all_data
        #print time.time() - st
        return data

    
    def get_vslice(self, x):
        """Returns a vertical slice (eg: single freq.) from the model at x.
        
        The returned slice is a two-tuple: (x_data, y_data).
        
        """
        with self._mutex:
            #for now just find the index of the first one >=
            for i, val in enumerate(self._x_data):
                if val >= x:
                    break
            idx = i
            #assemble the historical data...
            # - TODO: a better way to do this
            ret_t = np.zeros(len(self._history))
            ret_data = np.zeros(len(self._history))
            for i, (t, data, md) in enumerate(self._history):
                ret_t[i] = t
                ret_data[i] = data[idx]
        return ret_t, ret_data
    
    def set_max_len(self, max_len):
        with self._mutex:
            self._max_len = max_len
            for i in xrange(len(self._history) - max_len):
                self._history.popleft()


class _WaterfallImageRenderer(QtCore.QObject):
    
    # NOTES ON THREAD SAFETY:
    #
    # The image renderer is running on a thread.
    #
    # All image manipulation is thread-safe due to the use of the _data_queue for passing image updates around.
    #
    # Any other shared memory access must be careful to use approriate synchronization mechanisms.
    #
    # Also note that the slots (Qt signal handlers) are all executed on timing that is These slots execute with Qt
    # event loop timing. Appropriate thread synchronization mechanisms need
    # to be used for them to play well together!
    
    sigNewImageReady = QtCore.Signal(QtGui.QImage)
    sigImageRendered = QtCore.Signal() #for sync
    sigStatsChanged = QtCore.Signal() #slots call get_stats() to fetch
    
    _instance_count = 0
    
    def __init__(self,
                 #width, #always the width of the model
                 data_model,
                 color_lookup_table,
                 color_lookup_min, #value to map to 0.0 for lookup (ie: black)
                 color_lookup_max, #value to map to 1.0 for lookup (ie: white)
                 max_frame_rate_fps):
        super(_WaterfallImageRenderer, self).__init__()
        self._data_model = data_model
        self._lut = color_lookup_table
        self._lut_levels = (color_lookup_min, color_lookup_max)
        self._frame_period_ms = (1000.0 / float(max_frame_rate_fps))
        
        assert isinstance(data_model, WaterfallModel)
        
        self._active = True
        self._raw_image = None
        self._render_thread_name = None
        
        #We will keep a local copy of the data that is currently being
        #rendered. This *ensures* that we do not lose sync with the model. A
        #good example of when sync is lost (in a BIG way) is if/when the
        #plotting is paused, but the model is continually accumulating data.
        #Keeping a separate copy also enables us to always be able to pick
        #out exact source data for a given row. Also note that using a deque
        #makes access extremely cheap (eg: deque.append(deque.pop()) clocks
        #at < 0.2 us on this laptop).
        self._src_data = collections.deque()
        
        self.__ring_buffer = None
        self.__cur_buffer_row = None
        
        self._raw_image_height  = None
        self._raw_image_width = None
        self._output_image_width = None
        self._output_image_height = None
        
        self._render_pipeline = Queue.Queue()
        self._render_job_count = 0
        self._mutex = threading.RLock() #for generic use (quick stuff only!)
        
        #stats...
        self._stats_lock = threading.Lock()
        self._max_backlog = 0
        
        #Configure thread synchronization stuff...
        self._configure_synchronization()
        
        self._image_ready = False
        
        #Seed the charting with the initial data...
        # - no need... initial resizing will do it.
        #self._do_full_image_refresh()

    def _configure_synchronization(self):
        """Sets up synchronization of the waterfall rendering.
        
        The general synchronization premises are that:
        
        1) We don't want to try and draw faster than the specifed frame rate
           - there is no point in going faster, and we just clog up the
              event loop if we go too quickly.
        2) We don't want to update the image before it is actually drawn
           - data can potentially be arriving for the waterfall off of the
              regular Qt event loop timing.  Updating the backing image when
              the new data arrives could easily cause drawing problems.
        
        """
        #set up regular "frame ok" approvals to ensure we don't draw faster
        #than the specified max_frame_rate_fps...
        self._frame_ok_event = threading.Event()
        self._frame_ok_event.set() #first frame is immediately ok to draw!
        self._fps_timer = QtCore.QTimer()
        self._fps_timer.timeout.connect(self.onFPSTimer)
        self._fps_timer.start(self._frame_period_ms)


    def start(self):
        """Kicks off the rendering thread that actually does all the work."""
        self._render_thread_name = "WFRenderer-%d" % self._instance_count
        self._instance_count += 1
        self._render_thread = threading.Thread(
            target = self._thread_master,
            name = self._render_thread_name,
        )
        self._render_thread.setDaemon(True)
        self._render_thread.start()


    ### ALL CALLS BELOW MUST BE THREAD SAFE
    ### ALL CALLS BELOW MUST BE THREAD SAFE
    ### ALL CALLS BELOW MUST BE THREAD SAFE
    
    
    ## START OF SLOTS ##
    ## START OF SLOTS ##
    ## START OF SLOTS ##
    
    def onImageResize(self, new_size, old_size):
        dlog("_WaterfallImageRenderer.onImageResize fired")
        assert isinstance(new_size, QtCore.QSize)
        assert isinstance(old_size, QtCore.QSize)
        
        new_size_tuple = new_size.toTuple()
        old_size_tuple = old_size.toTuple()
        
        if old_size_tuple == (-1, -1): #never had a size!
            self._output_image_width = new_size_tuple[0]
            self._output_image_height = new_size_tuple[1]
            self._raw_image_width = self._data_model._x_len
            self._raw_image_height = self._output_image_height
        
        if new_size_tuple != old_size_tuple:
            new_width, new_height = new_size_tuple
            old_width, old_height = old_size_tuple
            refresh_image_data = (new_height != old_height)
            
            #updating image params while the render thread may be rendering
            #is a Bad idea, so we'll serialize it in the render pipeline...
            def resize_image():
                dlog("resize_image() closure called")
                self._output_image_width = new_width
                self._output_image_height = new_height
                #the raw image width never changes, but height does...
                self._raw_image_height = new_height
                
                if refresh_image_data:
                    # Keep it simple for now and just re-fetch all the
                    # appropriate data and redraw. This could be smarter.
                    # Note that both calls are thread safe.
                    new_data = self._get_data_from_model(new_height)
                    self.set_image_data(new_data) #thread safe
            
            #queue up the resize in the render pipeline...
            #if refresh_image_data:
                ##anything else in the pipeline is pointless
                #with self._render_pipeline.mutex:
                    #self._render_pipeline.queue.clear()
            self._render_pipeline.put(resize_image)
    
    
    def onFPSTimer(self):
        #Indicate it is ok to work on the next frame...
        self._frame_ok_event.set()
    
    
    ## END OF SLOTS ##
    ## END OF SLOTS ##
    ## END OF SLOTS ##
    
    
    def _drain_queue(self):
        """Returns a list of new data from the queue (earliest first).
        
        Blocks until there is new data, so the returned list will always have
        a length of at least one.
        
        """
        #TODO: add limiting for when we can't keep up with incoming data
        new_data = []
        
        #block until we get one...
        #dlog("about to block on queue get...")
        new_data.append(self._render_pipeline.get(block=True))
        #dlog("queue get completed")
        
        #grab the rest of 'em (if any)...
        while self._render_pipeline.qsize() > 0:
            try:
                new_data.append(self._render_pipeline.get(block=False))
            except Queue.Empty:
                #Should never happen due to qsize checking!!!  If this happens
                #someone other than us is being evil and draining our queue.
                msg = "Code error: Unexpected empty queue in waterfall"
                raise Exception(msg)
        
        last_max_backlog = self._max_backlog
        with self._stats_lock:
            self._max_backlog = max(self._max_backlog, len(new_data))
        
        if last_max_backlog != self._max_backlog:
            dlog("New pipeline backlog record = %d" % self._max_backlog)
            self.sigStatsChanged.emit()
        
        return new_data
    
    def _wait_for_frame_ok(self):
        """Waits until our frame is ok to draw, or we're no longer active."""
        assert threading.current_thread().name == self._render_thread_name
        
        while self._active:
            if self._frame_ok_event.wait(FRAME_WAIT_TIMEOUT_s) == True:
                #immediately clear the event for the next time...
                self._frame_ok_event.clear()
                #dlog("FRAME OK!")
                break
    
    def _process_rendering_pipeline(self):
        #wait for data in the queue...
        new_data = self._drain_queue()
        #render new data to self._raw_image...
        self._update_image_with_new_data(new_data)
    
    
    def _thread_master(self):
        """The master function that is run on the rendering thread."""
        # This IS the rendering thread.
        while self._active:
            self._process_rendering_pipeline()
            
            if self._raw_image is None:
                continue
            
            output_image = self._raw_image.scaled(self._output_image_width,
                                                  self._output_image_height)
            
            #emit signals...
            # - note that the sigImageRendered emit statement will block due
            #    to the way we connected it.  This is intentional and is a
            #    cheap way for us to do nothing on this thread until the main
            #    Qt event loop has rendered the image.
            self.sigNewImageReady.emit(output_image)
            self.sigImageRendered.emit() #blocking emit
            self._wait_for_frame_ok()
    
    
    def _point_raw_image_at_cur_offset(self):
        """Sets the address of the _qimage data to the current/correct
        circular buffer location.
        
        """
        assert threading.current_thread().name == self._render_thread_name
        
        raw_w = self._raw_image_width
        raw_h = self._raw_image_height
        #get the precise memory location we want to start the buffer from...
        pixel_offset = self.__cur_buffer_row * raw_w
        byte_offset = 4 * pixel_offset
        ptr = ctypes.c_char.from_buffer(self.__ring_buffer, byte_offset)
        #construct the display image from the memory at this pointer...
        fmt = QtGui.QImage.Format.Format_ARGB32
        self._raw_image = QtGui.QImage(ptr, raw_w, raw_h, fmt)
    
    
    def _create_image(self, img_data):
        """Regenerates a completely new image, given the new img_data."""
        assert threading.current_thread().name == self._render_thread_name
        assert img_data.ndim == 2
        
        dlog("_create_image called and re-assigning raw image dimensions")
        with self._mutex:
            self._raw_image_height, self._raw_image_width = img_data.shape
            
            #only keep a record of those rows that have data...
            # - soemthign is backwards here... we shoudl be able to have the
            #    real data instead of going backwards from img data.
            # - FIXME
            populated_row_filter = img_data[:, 0] != np.NINF
            populated_img_data = img_data[populated_row_filter, :]
            
            self._src_data = collections.deque(populated_img_data)
            
            argb, alpha = pgfuncs.makeARGB(img_data,
                                           lut=self._lut,
                                           levels=self._lut_levels,
                                           )
            tmp_img = pgfuncs.makeQImage(argb, alpha, transpose=False)
            
            # We now have a fully generated tmp_image. We need to prep the
            # doubled-up ring buffer by setting up two copies and initializing
            # our current frame pointer offset...
            self.__ring_buffer = np.vstack((tmp_img.data, tmp_img.data))
            dlog("ring buffer size set to %r" % (self.__ring_buffer.shape, ))
            self.__cur_buffer_row = self._raw_image_height
            
            #set our _qimage to point at the proper location in the ring buffer...
            self._point_raw_image_at_cur_offset()
            
            self._image_ready = True
    
    
    def _add_image_row(self, row_data):
        assert threading.current_thread().name == self._render_thread_name
        assert row_data.shape == (self._raw_image_width, )
        
        if self._image_ready == False:
            return
        
        st = time.time()
        with self._mutex:
            #get (potentially) shared memory access out of the way...
            # - all are (must be) immutable
            img_cols = self._raw_image_width
            img_rows = self._raw_image_height
            
            lut = self._lut
            lut_levels = self._lut_levels
            
            self.__cur_buffer_row -= 1
            if self.__cur_buffer_row < 0:
                self.__cur_buffer_row = img_rows
            
            idx1 = self.__cur_buffer_row
            idx2 = self.__cur_buffer_row + img_rows - 1
            
            #update the local copy of source data...
            self._src_data.append(row_data)
            if len(self._src_data) > img_rows:
                self._src_data.popleft()
        
        argb, alpha = pg.functions.makeARGB(row_data.reshape((1, img_cols)),
                                            lut=lut,
                                            levels=lut_levels)
        #argb, alpha = fn.makeARGB(image.transpose((1, 0, 2)[:image.ndim]), lut=lut, levels=self.levels)
        new_img_row = pg.functions.makeQImage(argb, alpha, transpose=False)
        
        #dlog("writing ring rows %d and %d.  num_rows = %d, buffer shape = %r" % (idx1, idx2, img_rows, self.__ring_buffer.shape))
        self.__ring_buffer[idx1, :, :] = new_img_row.data
        self.__ring_buffer[idx2, :, :] = new_img_row.data
        
        et1 = time.time() - st
        self._point_raw_image_at_cur_offset()
        
        et2 = time.time() - st
        pass #as a breakpoint anchor
    
    
    def _process_rendering_pipeline(self):
        """Removes and processes all instructions in the pipeline.
        
        Pipeline instructions can be:
            1) a callable that needed to be serialized in the render pipeline
            2) a new row (1D array)
            3) a full image (2D array)
        
        """
        assert threading.current_thread().name == self._render_thread_name
        
        instructions = self._drain_queue()
        #should probably have instructions in the buffer be explicitly
        #identified (eg: (instr_type, instr_data)) and dispatch accordingly,
        #but this works well enough for now.
        for job in instructions:
            if callable(job):
                job()
            elif job.ndim == 1:
                self._add_image_row(job)
            elif job.ndim == 2:
                self._create_image(job)
            self._render_job_count += 1
    
    def _do_full_image_refresh(self):
        """Triggers a complete redraw with new data."""
        dlog("Full image refresh triggered!")
        data = self._get_data_from_model(self._raw_image_height)
        self._render_pipeline.put(data)


    def _get_data_from_model(self, num_rows):
        #This is thread-safe because get_latest_data is.
        return self._data_model.get_latest_data(num_rows, True)

    ### PUBLIC METHODS
    ### PUBLIC METHODS
    ### PUBLIC METHODS
    
    def setLookupTable(self, lut):
        dlog("setLookupTable called")
        if not np.array_equal(self._lut, lut):
            self._lut = lut
            if self._raw_image is not None:
                dlog("setLookupTable triggered a full image refresh!")
                self._do_full_image_refresh()
    
    def add_image_row(self, data_row):
        assert data_row.ndim == 1
        #Note that the data queue handles both new rows and full data sets.
        self._render_pipeline.put(data_row)
    
    def set_image_data(self, data, pre_render_call = None):
        #This call is thread safe.
        assert len(data.shape) == 2
        #It is very possible that the data queue may be being cleared out at
        #the moment by the rendering thread. There may even be some rows left
        #to clear out. However, since we've got a brand spanking new image to
        #render we safely jump the gun and trigger a full render (by
        #providing a full data set instead of a row).
        with self._render_pipeline.mutex:
            self._render_pipeline.queue.clear()
            if pre_render_call:
                assert callable(pre_render_call)
                self._render_pipeline.queue.append(pre_render_call)
            self._render_pipeline.queue.append(data)
    
    def get_stats(self):
        with self._stats_lock:
            stats = {
                "max_backlog": self._max_backlog,
            }
        return stats
    
    def get_hslice(self, row_num):
        """Gets the source data for the current image row at row_num.
        
        Returned data is a two-tuple: (xdata, ydata), where:
        
        xdata is the actual x data from the source model, and
        ydata is the source data for the given row_num.
        
        """
        if row_num < 0:
            #An example of when this happens is when the mouse is hovering
            #over an area with no data.
            return None
        
        xdata = self._data_model._x_data
        ydata = self._src_data[row_num]
        return (xdata, ydata)
    
    def get_vslice(self, col_num):
        """Gets the source data for the current image row at col_num.
        
        Returned data is a two-tuple: (xdata, ydata), where
        
        xdata is the row number from the waterfall plot, and ydata is the
        historical source data, one point per row number (limited to what is
        displayed in the plot).
        
        For accessing *real* data, the underlying data model should be used
        instead.
        
        """
        with self._mutex:
            npts = len(self._src_data)
            xdata = np.arange(npts)
            ydata = np.empty(npts)
            for i, val in enumerate(self._src_data):
                
                ydata[i] = val[col_num]
        return (xdata, ydata)


class _WaterfallImageWidget(QtGui.QWidget):
    """The widget where the waterfall itself is drawn."""
    
    sigResized = QtCore.Signal(QtCore.QSize, QtCore.QSize)
    sigMouseMoved = QtCore.Signal(int, int) #(x, y) in pixels
    
    def __init__(self, parent = None, track_mouse = True):
        super(_WaterfallImageWidget, self).__init__(parent)
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
                           QtGui.QSizePolicy.Expanding)

        #self.setAttribute(Qt.WA_StaticContents)
        self._qimage = QtGui.QImage()
        self._crosshair_xy = (None, None)
        self._last_crosshair_xy = self._crosshair_xy
        
        if track_mouse:
            #Configure crosshair lines...
            self._hline = QtGui.QRubberBand(QtGui.QRubberBand.Line, self)
            self._vline = QtGui.QRubberBand(QtGui.QRubberBand.Line, self)
            self._hline.show()
            self._vline.show()
            self._set_crosshair(-1, -1)
            
            #Tell Qt we actually want mouse events...
            self.setMouseTracking(True)
            
            #limit the crosshair painting speed...
            # - intended to help with massive slowdowns happening with mouse
            #    processing, but it didn't help (yet?).  See the slot, too.
            self._crosshair_timer = QtCore.QTimer()
            self._crosshair_timer.timeout.connect(self._onCrosshairTimer)
            self._crosshair_timer.start(1.0 / CROSSHAIR_FPS)
        
        #self.show()
    
    def paintEvent(self, event):
        #dlog("_WaterfallImage paintEvent triggered.  Current size = %r, rect = %r" % (self.size().toTuple(), event.rect().getRect()))
        
        #FOR RENDERING SPEED, SEE THIS THREAD:
        #http://www.qtcentre.org/threads/6929-Any-fast-way(-lt-10ms)-to-display-640*480-QImage-on-QGraphicsScene?p=184003#post184003
        
        #see post #8 as well to try the excellent QGraphicsScene,
        #QGraphicsPixmapItem, QGraphicsView example (including the GL
        #viewport, commented out). The fps method is very good, too. Shoudl
        #do in my update routine as a measure of how fast we are going.
        #
        #trying the C code directly (esp. with different image sizes) would
        #be very illuminating.
        #
        #Note that the pixmap setting thing is somewhat misleading since it
        #has a set of pregenerated pixmaps to work with, wehreas we need to
        #generate them on the fly, one for each frame (and pixmap generation
        #is rumoured to be slow... time it!).
        
        painter = QtGui.QPainter(self)
        dirty_rect = event.rect()
        
        painter.drawImage(dirty_rect, self._qimage, dirty_rect)

    def resizeEvent(self, event):
        #Need to broadcast this primarily so that the image renderer can know
        #what dimensions to render...
        dlog("Waterfall image resized to %r and 'sigResized' about to be emitted" % (event.size().toTuple(), ))
        self.sigResized.emit(event.size(), event.oldSize())
        #dlog("Waterfall image 'sigResized' signal has been emitted.")
        super(_WaterfallImageWidget, self).resizeEvent(event)
    
    def onWaterfallImageUpdate(self, new_image):
        #dlog("Image update signal received by _WaterfallImageWidget slot")
        self._qimage = new_image
        
        #Request a Qt repaint to be scheduled (and when it *does* eventually
        #happen, self.paintEvent is invoked)...
        self.update()
    
    def updateGeometry(self):
        dlog("updateGeometry called!")
        super(_WaterfallImageWidget, self).updateGeometry()


    def _set_crosshair(self, x, y):
        self._crosshair_xy = (x, y)


    def _onCrosshairTimer(self):
        #dlog("crosshair update!")
        
        #this exists because moving the crosshair around on every mousemove
        #was inexplicably slow... BUT... this timer did not help much!
        #Something else is going on (tbd).
        if self._crosshair_xy == self._last_crosshair_xy:
            return
        else:
            w, h = self.size().toTuple()
            x, y = self._crosshair_xy
            
            self._hline.setGeometry(0, y, w, 1)
            self._vline.setGeometry(x, 0, 1, h)
            
            self._last_crosshair_xy = self._crosshair_xy
            
            if x >= 0: #mouse is in the window
                self.sigMouseMoved.emit(x, y)


    def mouseMoveEvent(self, event):
        #figure out where we are, get an hslice and vslice (as appropriate)
        #and signal them up...
        dlog("Mouse moved to (%d, %d)" % (event.x(), event.y()))
        self._set_crosshair(*event.pos().toTuple())
        
        #if self._plot_widget.sceneBoundingRect().contains(pos):
            #if self._pending_mouse_move_pos:
                ##set the pending one to the new one!
                #self._pending_mouse_move_pos = pos
            #else:
                #mousePoint = self._plot_widget.plotItem.vb.mapSceneToView(pos)
                #index = int(mousePoint.x())
                #v_line.setPos(mousePoint.x())
                #self.sigMouseMoved.emit(mousePoint)    


class WaterfallPlotWidget(QtGui.QWidget):
    """Top level waterfall widget.
    
    Contains multiple widgets: the waterfall image, and the gradient editor.
    
    """
    #sigMouseMoved = QtCore.Signal(object)
    sigMouseMove = QtCore.Signal(float, float, object, object) #(xval, yval, hslice, vslice)
    
    def __init__(self,
                 data_model,
                 parent = None, #Qt parent
                 scale_limits = None, #(min_val, max_val) or None (autoscale to data)
                 display_threshold = None, # > this or not displayed
                 vertical_stretch = False,
                 max_frame_rate_fps = 60,
                 show_gradient_editor = True,
                 ):
        """
        
        num_rows == -1 means to plot all data in the model.
        
        """
        assert isinstance(data_model, WaterfallModel)
        super(WaterfallPlotWidget, self).__init__(parent)
        
        if scale_limits is not None:
            try:
                scale_min, scale_max = scale_limits
            except ValueError:
                msg = ("If scale_limits is specified, it must be a tuple like "
                       "(black_level, white_level)")
                raise ValueError(msg)
            self._scale_limits = scale_limits
        self._show_ge = show_gradient_editor
        self._vertical_stretch = vertical_stretch
        self._data_model = data_model
        
        self._pending_mouse_move_pos = None
        
        self._LUT_PTS = 256
        self._latest_lut = None
        
        #create child widgets...
        #self._plot_widget = pg.PlotWidget(self)
        self._wf_img = _WaterfallImageWidget()
        
        if self._show_ge:
            self._gradient_editor = pg.GradientWidget(parent = self,
                                                      orientation = "right")
        
        #configure the widgets...
        #self._plot_widget.addItem(self._wf_img)
        #self._wf_img.setLookupTable(self._get_lut)
        
        #do layout...
        hbox = QtGui.QHBoxLayout(self)
        #hbox.addWidget(self._plot_widget)
        hbox.addWidget(self._wf_img)
        if self._show_ge:
            hbox.addWidget(self._gradient_editor)
        
        #Configure the background image renderer (but don't start it yet)...
        self._renderer = _WaterfallImageRenderer(data_model,
                                                 self._get_lut(),
                                                 scale_min,
                                                 scale_max,
                                                 max_frame_rate_fps)
        
        #connect signals...
        self._connect_signals()
        
    def onImageRendered(self):
        """This stub only exists to enable convenient synchronization with
        the Qt::BlockingQueuedConnection connection type.
        
        """
        #dlog("onImageRendered fired!")
        pass

    
    def _connect_signals(self):
        
        #deal with new data rows when they arrive...
        self._data_model.sigNewDataRow.connect(self._onNewDataRow)
        
        #Let the image renderer know what size images to render (when the
        #target image is resized)...
        self._wf_img.sigResized.connect(self._renderer.onImageResize)
        
        #Make any adjustments (eg: redraw) needed when the color lookup table
        #changes...
        if self._show_ge:
            self._gradient_editor.sigGradientChanged.connect(
                self._onGradientChange
            )
        
        #Hook up mouse movement handling...
        self._wf_img.sigMouseMoved.connect(self._onImageMouseMove)
        
        #self._wf_img.scene().sigMouseMoved.connect(self._onPlotMouseMove)
        
        #Connect newly rendered images to the image widget...
        self._renderer.sigNewImageReady.connect(
            self._wf_img.onWaterfallImageUpdate
        )
        
        #ensure we don't update the backing image until Qt has rendered it...
        self._renderer.sigImageRendered.connect(
            self.onImageRendered,
            #type = QtCore.Qt.BlockingQueuedConnection
        )


    def _onImageMouseMove(self, mouse_x, mouse_y):
        if __debug__:
            st = time.time()
        
        #figure out the source coordinates that the mouse coordinates
        #correspond to...
        # - TODO: FIXME
        x = -1.0
        y = -1.0
        
        #get the slices...
        # - not that the data in the slices is limited to the data that is in
        #    the image itself.  The (x, y) in the signal payload can be used to
        #    get more data (for the vslice, anyway) from the underlying model.
        # - vpos is flipped (mouse 0 is the top, but 0 == newest)
        h_index = len(self._renderer._src_data) - mouse_y - 1
        hslice = self._renderer.get_hslice(h_index)
        if hslice is None:
            return
        
        #The horizontal cursor position we have for the vslice is in screen
        #coords (pixels from the left), while the backing data we are slicing
        #from has the full spectral width. We need to scale to teh correct
        #value. note that this means that images with less pixels in them
        #than data in the spectrum cannot access all points via the mouse).
        display_width_max = self._renderer._output_image_width - 1
        max_src_index = self._renderer._raw_image_width - 1
        data_col = (float(mouse_x) / display_width_max) * max_src_index
        vslice = self._renderer.get_vslice(data_col)
        
        self.sigMouseMove.emit(x, y, hslice, vslice)
        
        if __debug__:
            dlog("mousemove handler took %f s" % (time.time() - st, ))


    def _get_lut(self):
        lut = self._gradient_editor.getLookupTable(self._LUT_PTS)
        self._latest_lut = lut
        return lut
    
    def set_lut(self, lut):
        """Sets the lookup table for the waterfall image.
        
        This redraws the image.
        
        """
        self._renderer.setLookupTable(lut)
        
    def _onGradientChange(self, gradient_editor_item):
        assert isinstance(gradient_editor_item, pg.GradientEditorItem)
        lut = gradient_editor_item.getLookupTable(self._LUT_PTS)
        self._renderer.setLookupTable(lut)
    
    def _onNewDataRow(self, data_row_tuple):
        timestamp_s, data_row, metadata = data_row_tuple
        self._renderer.add_image_row(data_row)


class ThreadedWaterfallPlotWidget(WaterfallPlotWidget):
    """
    Automatically start renderer thread on first paintEvent
    """
    def paintEvent(self, event):
        #we will only ever run this once and then pass back to the
        #superclass event handler. Now is a safe time to start the rendering
        #thread...
        dlog("Starting rendering thread...")
        self._renderer.start()
        self.paintEvent = super(WaterfallPlotWidget, self).paintEvent
        self.paintEvent(event)
