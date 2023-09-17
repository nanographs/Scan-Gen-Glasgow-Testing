from time import perf_counter

import numpy as np

from PyQt6 import QtWidgets

import pyqtgraph as pg
from pyqtgraph.exporters import Exporter
from pyqtgraph.Qt import QtCore

import tifffile
from tifffile import imwrite

import os, datetime

import socket

HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
PORT = 1234  # Port to listen on (non-privileged ports are > 1023)



app = pg.mkQApp("Scan Live View")

settings = np.loadtxt(os.path.join(os.getcwd(), "Scan Capture/current_display_setting"))
dimension = int(settings)

## Define a top-level widget to hold everything
w = QtWidgets.QWidget()
w.setWindowTitle('/|/|/|/| scanning /|/|/|/|')

## Create a grid layout to manage the widgets size and position
layout = QtWidgets.QGridLayout()
w.setLayout(layout)

## Create window with GraphicsView widget
win = pg.GraphicsLayoutWidget()
#win.show()  ## show widget alone in its own window

# A plot area (ViewBox + axes) for displaying the image
#view = win.addPlot(title="")
view = win.addViewBox()

## lock the aspect ratio so pixels are always square
view.setAspectLocked(True)

## Create image item
img = pg.ImageItem(border='w', levels = (0,255))
view.addItem(img)

## Set initial view bounds
view.setRange(QtCore.QRectF(0, 0, dimension, dimension))


updateTime = perf_counter()
elapsed = 0

timer = QtCore.QTimer()
timer.setSingleShot(True)
# not using QTimer.singleShot() because of persistence on PyQt. see PR #1605

FrameBufDirectory = os.path.join(os.getcwd(), "Scan Capture/current_frame")


conn_btn = QtWidgets.QPushButton('💼')
conn_btn.setCheckable(True)
def conn():
    global HOST, PORT, sock
    if conn_btn.isChecked():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((HOST, PORT))
    else:
        sock.close()
conn_btn.clicked.connect(conn)


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
dwelltime_options.setRange(0,255)
dwelltime_options.setSingleStep(1)
resolution_options.addWidget(dwellLabel,0,0)
resolution_options.addWidget(dwelltime_options,1,0)

res_btn = QtWidgets.QPushButton('!!')
resolution_options.addWidget(res_btn,1,2)



start_btn = QtWidgets.QPushButton('▶️')
start_btn.setCheckable(True)

buf = np.ones(shape=(dimension*dimension))
last_pixel = 0

def imgout(raw_data):
    global buf, last_pixel
    # print("-----------")
    # print("frame", current.n)
    data = list(raw_data)
    d = np.array(data)
    print(d)
    # print(buf)
    zero_index = np.nonzero(d < 1)[0]
    # print("buffer length:", len(buf))
    # print("last pixel:",current.last_pixel)
    print("d length:", len(d))
    # print("d:",d)
    
    if len(zero_index) > 0: #if a zero was found
        # current.n += 1
        # print("zero index:",zero_index)
        zero_index = int(zero_index)

        buf[:d[zero_index+1:].size] = d[zero_index+1:]
        # print(buf[:d[zero_index+1:].size])
        # print(d[:zero_index+1].size)
        buf[dimension * dimension - zero_index:] = d[:zero_index]
        # print(buf[dimension * dimension - zero_index:])
        last_pixel = d[zero_index+1:].size
    
    else: 
        if len(buf[last_pixel:last_pixel+len(d)]) < len(d):
            pass
        #     print("data too long to fit in end of frame, but no zero")
        #     print(d[:dimension])
        print(d.shape)
        print(buf.shape)
        print(buf[last_pixel:last_pixel + d.size].shape)
        buf[last_pixel:last_pixel + d.size] = d
        # print(buf[current.last_pixel:current.last_pixel + d.size])
        last_pixel = last_pixel + d.size
    
    print(buf)


def start():
    global timer, updateData, dimension, sock
    resolution_dropdown.setEnabled(False)
    dwelltime_options.setEnabled(False)
    res_btn.setEnabled(False)
    if start_btn.isChecked():
        start_btn.setText('⏸️')
        msg = ("scan").encode("UTF-8") ## ex: res09, res10
        sock.send(msg)
        updateData()
        #timer.timeout.connect(updateData)
        # start_btn.setStyleSheet("background-color : lightblue") #gets rid of native styles, button becomes uglier
    else:
        # timer.timeout.disconnect(updateData)
        start_btn.setText('▶️')
        resolution_dropdown.setEnabled(True)
        dwelltime_options.setEnabled(True)
        res_btn.setEnabled(True)
        
        


start_btn.clicked.connect(start)

def update_dimension(dim):
    global dimension
    dimension = dim
    view.setRange(QtCore.QRectF(0, 0, dimension, dimension))
    updateData()

def res():
    res_bits = resolution_dropdown.currentIndex() + 9 #9 through 14
    dimension = pow(2,res_bits)
    msg = ("res" + format(res_bits, '02d')).encode("UTF-8") ## ex: res09, res10
    HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
    PORT = 1234  # Port to listen on (non-privileged ports are > 1023)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))
    sock.send(msg)
    print("sent", msg)
    update_dimension(dimension)
res_btn.clicked.connect(res)

## add widgets to layout
layout.addWidget(win,0,0)
layout.addWidget(save_btn,1,0)
layout.addWidget(start_btn,1,1)
layout.addWidget(conn_btn,1,2)
layout.addLayout(resolution_options, 2,0)

w.show()



# Custom ROI for selecting an image region
# roi = pg.ROI([10,100], [100, 500])
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
hist.setImageItem(img)
hist.disableAutoHistogramRange()
win.addItem(hist)

# # Draggable line for setting isocurve level
# isoLine = pg.InfiniteLine(angle=0, movable=True, pen='g')
# hist.vb.addItem(isoLine)
# hist.vb.setMouseEnabled(y=False) # makes user interaction a little easier
# isoLine.setValue(0.8)
# isoLine.setZValue(1000) # bring iso line above contrast controls





def updateData():
    print("update")
    global img, updateTime, elapsed, dimension, sock, buf
    if start_btn.isChecked():
        data = sock.recv(16384)
        imgout(data)
        # data = np.memmap(FrameBufDirectory,
        # shape = (dimension,dimension))
        # data = np.random.rand(dimension,dimension)

        # print(data)
        data = buf.copy()
        data.shape = (dimension, dimension)
    else:
        print("no data")
        data = np.ones(shape = (dimension,dimension))
    img.setImage(np.rot90(data,k=3)) #this is the correct orientation to display the image
        

    timer.start(1)
    now = perf_counter()
    elapsed_now = now - updateTime
    updateTime = now
    elapsed = elapsed * 0.9 + elapsed_now * 0.1

    # print(data.shape)
    # print(f"{1 / elapsed:.1f} fps")

# updateData()
# timer.timeout.connect(updateData)



if __name__ == '__main__':
    pg.exec()