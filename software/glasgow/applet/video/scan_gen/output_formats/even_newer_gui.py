import sys
import asyncio
import pyqtgraph as pg
from pyqtgraph.exporters import Exporter
from pyqtgraph.Qt import QtCore

import logging
import types
import functools
# logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)
import numpy as np



from PyQt6.QtWidgets import (QHBoxLayout, QMainWindow,
                             QMessageBox, QPlainTextEdit, QPushButton,
                             QVBoxLayout, QWidget, QLabel, QGridLayout,
                             QSpinBox)




from qasync import QEventLoop, QApplication, asyncSlot, asyncClose

# from bmp_utils import *
from argparse import Namespace

class RegisterUpdateBox(QGridLayout):
    def __init__(self, label, lower_limit, upper_limit, fn=None):
        super().__init__()
        self.name = label
        self.fn = fn
        self.label = QLabel(label)
        self.addWidget(self.label,0,1)


        self.spinbox = QSpinBox()
        self.spinbox.setRange(lower_limit, upper_limit)
        self.spinbox.setSingleStep(1)
        self.addWidget(self.spinbox,1,1)




    @asyncSlot()
    async def do_fn(self):
        val = int(self.spinbox.cleanText())
        print("set", self.name, ":", val)
        if not self.fn == None: ## allow previewing the button without any function
            await self.fn(val)

class FrameSettings(QHBoxLayout):
    def __init__(self, img_display, scan_iface=None):
        super().__init__()
        self.scan_iface = scan_iface
        self.img_display = img_display
        if not self.scan_iface == None:
            self.x_resolution = RegisterUpdateBox("X Resolution", 1, 16384, self.scan_iface.set_x_resolution)
            self.y_resolution = RegisterUpdateBox("Y Resolution", 1, 16384, self.scan_iface.set_y_resolution)
        else:
            self.x_resolution = RegisterUpdateBox("X Resolution", 1, 16384)
            self.y_resolution = RegisterUpdateBox("Y Resolution", 1, 16384)

        self.x_resolution.spinbox.setValue(2048)
        self.y_resolution.spinbox.setValue(2048)

        self.registers = [self.x_resolution, self.y_resolution]

        self.addLayout(self.x_resolution)
        self.addLayout(self.y_resolution)

        self.btn = QPushButton("->")
        self.addWidget(self.btn) 
        self.btn.clicked.connect(self.do_fns)

    @asyncSlot()
    async def do_fns(self):
        height = int(self.y_resolution.spinbox.cleanText())
        width = int(self.x_resolution.spinbox.cleanText())
        self.img_display.setRange(height, width)
        for register in self.registers:
            await register.do_fn()



class ImageDisplay(pg.GraphicsLayoutWidget):
    def __init__(self, height, width):
        super().__init__()
        self.image_view = self.addViewBox(invertY = True)
        ## lock the aspect ratio so pixels are always square
        self.image_view.setAspectLocked(True)
        self.image_view.setRange(QtCore.QRectF(0, 0, height, width))
        
        self.live_img = pg.ImageItem(border='w',axisOrder="row-major")
        self.image_view.addItem(self.live_img)

        # Contrast/color control
        self.hist = pg.HistogramLUTItem()
        self.hist.setImageItem(self.live_img)
        self.hist.disableAutoHistogramRange()
        self.addItem(self.hist)

        self.hist.setLevels(min=0,max=0)

        self.exporter = pg.exporters.ImageExporter(self.live_img)

    def setRange(self, height, width):
        self.image_view.setRange(QtCore.QRectF(0, 0, height, width))
    
    def showTest(self):
        test_file = "software/glasgow/applet/video/scan_gen/output_formats/Nanographs Pattern Test Logo and Gradients.bmp"
        bmp = bmp_import(test_file)
        array = np.array(bmp).astype(np.uint8)
        self.live_img.setImage(array)
class MainWindow(QWidget):

    def __init__(self, scan_iface=None):
        super().__init__()
        self.scan_iface = scan_iface

        self.setWindowTitle("Scan Control")
        self.layout = QGridLayout()
        self.setLayout(self.layout)

        self.image_display = ImageDisplay(2048, 2048)
        self.layout.addWidget(self.image_display, 0, 0)

        self.frame_settings = FrameSettings(self.image_display, self.scan_iface)

        self.start_btn = QPushButton('▶️')
        self.start_btn.setCheckable(True) #when clicked, button.isChecked() = True until clicked again
        self.start_btn.clicked.connect(self.toggle_scan)


        self.layout.addWidget(self.start_btn, 1, 0)

        self.frame_settings = FrameSettings(self.image_display, self.scan_iface)
        self.layout.addLayout(self.frame_settings, 2, 0)






    @asyncSlot()
    async def do_stuff(self):
        #await self.scan_iface.send_vec_stream_and_recieve_data()
        data = await self.scan_iface.stream_video()
        print(data)
        
        #self.image_display.showTest()
        self.scan_btn = QPushButton('!')
        self.scan_btn.clicked.connect(self.do_stuff)

        self.layout.addWidget(self.scan_btn, 1, 0)

    @asyncSlot()
    async def toggle_scan(self):
        if self.start_btn.isChecked():
            self.start_btn.setText('🔄')
            await self.scan_iface.set_raster_mode()
            self.update_continously = asyncio.ensure_future(self.keepUpdating())
            self.start_btn.setText('⏸️')

        else:
            print("Stopped scanning now")
            self.start_btn.setText('🔄')
            self.update_continously.cancel()
            self.start_btn.setText('▶️')


    async def keepUpdating(self):
        while True:
            try:
                await self.updateData()
            except Exception as error:
                print("error:",error)
                break

    async def updateData(self):
        await self.scan_iface.stream_video()
        await asyncio.sleep(0)
        data = np.array(self.scan_iface.buffer).astype(np.uint8)
        self.image_display.live_img.setImage(data, autoLevels = False)



def run_gui(scan_iface=None):
    app = QApplication(sys.argv)

    event_loop = QEventLoop(app)
    asyncio.set_event_loop(event_loop)

    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)

    main_window = MainWindow(scan_iface)
    main_window.show()

    with event_loop:
        event_loop.run_until_complete(app_close_event.wait())

    return main_window

if __name__ == "__main__":
    run_gui()

