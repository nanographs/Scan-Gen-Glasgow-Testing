from time import perf_counter

import asyncio
import functools
import sys

import numpy as np

from PyQt6 import QtWidgets

import pyqtgraph as pg
from pyqtgraph.dockarea import DockArea, Dock
from pyqtgraph.exporters import Exporter
from pyqtgraph.Qt import QtCore

import tifffile
from tifffile import imwrite

import os, datetime

# import socket

import qasync
from qasync import asyncSlot, asyncClose, QApplication



#from .....support.endpoint import *


HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
PORT = 1234  # Port to listen on (non-privileged ports are > 1023)



app = pg.mkQApp("Scan Live View")



dimension = 512

## Define a top-level widget to hold everything

class MainWindow(QtWidgets.QWidget):
    _msg_scan = ("scan").encode("UTF-8")
    _msg_stop = ("stop").encode("UTF-8") 
        
    def __init__(self):
        global dimension
        super().__init__()

        self.setWindowTitle('/|/|/|/| scanning /|/|/|/|')
        ## Create a grid layout to manage the widgets size and position
        self.layout = QtWidgets.QGridLayout()
        self.setLayout(self.layout)

        self.conn_btn = QtWidgets.QPushButton('Disconnected')
        self.conn_btn.setCheckable(True)
        self.conn_btn.clicked.connect(self.conn)

        self.layout.addWidget(self.conn_btn,0,0)

        ## Create window with GraphicsView widget
        self.win = pg.GraphicsLayoutWidget()

        # A plot area (ViewBox + axes) for displaying the image
        #view = win.addPlot(title="") 
        self.image_view = self.win.addViewBox()

        ## lock the aspect ratio so pixels are always square
        self.image_view.setAspectLocked(True)

        ## Create image item
        self.img = LiveScan()
        # self.img = pg.ImageItem(border='w', levels = (0,255))
        self.image_view.addItem(self.img)
        self.update_continously = False

        ## Set initial view bounds
        self.image_view.setRange(QtCore.QRectF(0, 0, dimension, dimension))

        self.layout.addWidget(self.win,1,0)

        self.start_btn = QtWidgets.QPushButton('▶️')
        self.start_btn.setCheckable(True) #when clicked, button.isChecked() = True until clicked again
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.start)

        self.new_scan_btn = QtWidgets.QPushButton('↻')
        # self.new_scan_btn.setEnabled(False)
        self.new_scan_btn.clicked.connect(self.new_scan)


    @asyncSlot()
    async def conn(self):
        global HOST, PORT
        self.writer = None
        if self.conn_btn.isChecked():
            self.conn_btn.setText('Connecting...')
            try:
                self.reader, self.writer = await asyncio.open_connection(HOST, PORT)
            except Exception as exc:
                self.conn_btn.setText("Error: {}".format(exc))
            else:
                self.start_btn.setEnabled(True)
                save_btn.setEnabled(True)
                resolution_dropdown.setEnabled(True)
                dwelltime_options.setEnabled(True)

                self.conn_btn.setText("Connected")
            # finally:
            #     self.btnFetch.setEnabled(True)
        else:
            self.conn_btn.setText("Disconnected")
            if self.writer is not None:
                self.writer.close()
                await self.writer.wait_closed()

    @asyncSlot()
    async def start(self):
        resolution_dropdown.setEnabled(False)
        dwelltime_options.setEnabled(False)
        # res_btn.setEnabled(False)
        if self.start_btn.isChecked():
            self.start_btn.setText('🔄')
            self.writer.write(self._msg_scan)
            await self.writer.drain()
            self.update_continously = asyncio.ensure_future(self.keepUpdating())
            self.start_btn.setText('⏸️')
            self.new_scan_btn.setEnabled(False)
            
        else:
            self.start_btn.setText('🔄')
            self.writer.write(self._msg_stop)
            #self.update_continously.cancel()
            self.start_btn.setText('▶️')
            print("Stopped scanning now")
            resolution_dropdown.setEnabled(True)
            dwelltime_options.setEnabled(True)
            self.new_scan_btn.setEnabled(True)
            # res_btn.setEnabled(True)

    async def keepUpdating(self):
        while True:   
            try:
                await self.updateData()
            except RuntimeError:
                print("eep")
                print(self.reader.at_eof())
                break

    async def updateData(self):
        global dimension
        if self.conn_btn.isChecked(): #and start_btn.isChecked():
            data = await self.reader.read(16384)
            #data = await self.reader.readexactly(16384)
            if data is not None:
                print("recvd", (list(data))[0], ":", (list(data))[-1], "-", len(list(data)))
                imgout(data)

        self.img.setImage(np.rot90(buf,k=3)) #this is the correct orientation to display the image

    def update_dimension(self, dim):
        global dimension, cur_line, packet_lines, buf
        dimension = dim
        cur_line = 0
        packet_lines = int(16384/dimension)
        buf = np.ones(shape=(dimension,dimension))
        self.image_view.setRange(QtCore.QRectF(0, 0, dimension, dimension))
        self.img.setImage(np.rot90(buf,k=3))
        #updateData()

    @asyncSlot()
    async def new_scan(self):
        res_bits = resolution_dropdown.currentIndex() + 9 #9 through 14
        dimension = pow(2,res_bits)
        msg = ("eeee").encode("UTF-8") ## ex: res09, res10
        self.writer.write(msg)
        await self.writer.drain()
        self.update_dimension(dimension)

    @asyncSlot()
    async def res(self):
        res_bits = resolution_dropdown.currentIndex() + 9 #9 through 14
        dimension = pow(2,res_bits)
        msg = ("re" + format(res_bits, '02d')).encode("UTF-8") ## ex: res09, res10
        self.writer.write(msg)
        await self.writer.drain()
        print("sent", msg)
        self.update_dimension(dimension)

    @asyncSlot()
    async def dwell(self):
        global dimension, dwelltime
        #res_bits = resolution_dropdown.currentIndex() + 9 #9 through 14
        #dimension = pow(2,res_bits)
        dwell_time =int(dwelltime_options.cleanText()) 
        dwelltime = dwell_time
        msg = ("d" + format(dwell_time, '03d')).encode("UTF-8") ## ex: d255, d001
        self.writer.write(msg)
        await self.writer.drain()
        print("sent", msg)
        self.update_dimension(dimension)
   

class LiveScan(pg.ImageItem):
    def __init__(self):
        super().__init__()
        # self.border = "white"
        self.levels = (0,255)
        buf = np.ones((512,512))
        self.setImage(np.rot90(buf,k=3))

        # now = perf_counter()
        # elapsed_now = now - updateTime
        # updateTime = now
        # elapsed = elapsed * 0.9 + elapsed_now * 0.1

        # print(data.shape)
        # print(f"{1 / elapsed:.1f} fps")

   

w = MainWindow()





#win.show()  ## show widget alone in its own window


## experimenting with more complex layouts
# tab_widget = QtWidgets.QTabWidget()
# ww.setCentralWidget(tab_widget)

# area = DockArea()
# d = Dock("Hello", size = (800,20))
# area.addDock(d)
# tab_widget.addTab(area, "Hi")
# tab_widget.addTab(w, "Win")








## to do: add an arrow/line to track current scan position
# axis = pg.AxisItem(orientation="right", linkView = view, showValues = False)
# arrow = pg.ArrowItem(angle = 180)
# view.addItem(arrow)
# win.addItem(axis)


save_btn = QtWidgets.QPushButton('save image')
def save_image():
    data = np.memmap(FrameBufDirectory,
    shape = (dimension,dimension))
    save_path = os.path.join(os.getcwd(), "Scan Capture/saved" + datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + ".tif")
    imwrite(save_path, data.astype(np.uint8), photometric='minisblack') 
save_btn.clicked.connect(save_image)



resolution_options = QtWidgets.QGridLayout()

resolution_dropdown = QtWidgets.QComboBox()
resolutionLabel = QtWidgets.QLabel("Resolution")
resolution_dropdown.addItem('512x512')
resolution_dropdown.addItem('1024x1024')
resolution_dropdown.addItem('2048x2048')
resolution_dropdown.addItem('4096x4096')
resolution_dropdown.addItem('8192x8192')
resolution_dropdown.addItem('16384x16384')
resolution_options.addWidget(resolutionLabel,0,1)
resolution_options.addWidget(resolution_dropdown,1,1)

dwellLabel = QtWidgets.QLabel("Dwell Time")
dwelltime_options = QtWidgets.QSpinBox()
dwelltime_options.setRange(1,255)
dwelltime_options.setSingleStep(1)
resolution_options.addWidget(dwellLabel,0,0)
resolution_options.addWidget(dwelltime_options,1,0)

# res_btn = QtWidgets.QPushButton('!!')
# resolution_options.addWidget(res_btn,1,2)
# resolution_dropdown.setEnabled(False)
# dwelltime_options.setEnabled(False)


resolution_dropdown.currentIndexChanged.connect(w.res)
dwelltime = 1
dwelltime_options.valueChanged.connect(w.dwell)


## start w most controls disabled until connection is made

resolution_dropdown.setEnabled(False)
dwelltime_options.setEnabled(False)
save_btn.setEnabled(False)


buf = np.ones(shape=(dimension,dimension))
cur_line = 0
cur_x = 0
packet_lines = int(16384/dimension)

def imgout(raw_data):
    global buf, cur_line, packet_lines
    # print("-----------")
    # print("frame", current.n)
    data = list(raw_data)
    if len(data) != 16384:
        print(data)
    else:
        d = np.array(data)
        d.shape = (packet_lines,dimension)
        buf[cur_line:cur_line+packet_lines] = d
        cur_line += packet_lines
        if cur_line == dimension:
            cur_line = 0 ## new frame, back to the top



scan_buttons = QtWidgets.QGridLayout()
scan_buttons.addWidget(save_btn,2,0)
scan_buttons.addWidget(w.start_btn,2,1)
scan_buttons.addWidget(w.new_scan_btn,2,2)
w.layout.addLayout(scan_buttons,2,0)
w.layout.addLayout(resolution_options, 3,0)






# # Custom ROI for selecting an image region
# roi = pg.ROI([50,100], [100, 50])
# roi.addScaleHandle([0.5, 1], [0.5, 0.5])
# roi.addScaleHandle([0, 0.5], [0.5, 0.5])
# view.addItem(roi)
# roi.setZValue(10)  # make sure ROI is drawn above image




# # Isocurve drawing
# iso = pg.IsocurveItem(level=0.8, pen='g')
# iso.setParentItem(img)
# iso.setZValue(5)

# Contrast/color control
hist = pg.HistogramLUTItem()
hist.setImageItem(w.img)
hist.disableAutoHistogramRange()
w.win.addItem(hist)

# # Draggable line for setting isocurve level
# isoLine = pg.InfiniteLine(angle=0, movable=True, pen='g')
# hist.vb.addItem(isoLine)
# hist.vb.setMouseEnabled(y=False) # makes user interaction a little easier
# isoLine.setValue(0.8)
# isoLine.setZValue(1000) # bring iso line above contrast controls







## https://github.com/CabbageDevelopment/qasync/blob/master/examples/aiohttp_fetch.py
async def main():
    def close_future(future, loop):
        loop.call_later(10, future.cancel)
        future.cancel()

    loop = asyncio.get_event_loop()
    future = asyncio.Future()

    app = QApplication.instance()
    if hasattr(app, "aboutToQuit"):
        getattr(app, "aboutToQuit").connect(
            functools.partial(close_future, future, loop)
        )

    # mainWindow = MainWindow()
    # mainWindow.addWidget(w)
    # mainWindow.show()
    w.show()

    await future
    return True


if __name__ == "__main__":
    try:
        qasync.run(main())
    except asyncio.exceptions.CancelledError:
        sys.exit(0)



# if __name__ == '__main__':
#     pg.exec()