import asyncio
import functools
import sys

import tifffile
from tifffile import imwrite
from PIL import Image

import os, datetime

import numpy as np

from PyQt6.QtWidgets import (QMainWindow, QPushButton, 
                            QGridLayout, QWidget, QComboBox, 
                            QLabel, QSpinBox, QFileDialog)

import pyqtgraph as pg
from pyqtgraph.dockarea import DockArea, Dock
from pyqtgraph.exporters import Exporter
from pyqtgraph.Qt import QtCore

import qasync
from qasync import asyncSlot, asyncClose, QApplication

from microscope import ScanController


from bmp_utils import *


app = pg.mkQApp("Scan Control")

cwd = os.getcwd()

# # Open the qss styles file and read in the CSS-like styling code
# with open(cwd + '/software/glasgow/applet/video/scan_gen/output_formats/styles.qss', 'r') as f:
#     style = f.read()
#     # Set the stylesheet of the application
#     app.setStyleSheet(style)



scan_controller = ScanController()

class ResolutionDropdown(QGridLayout):
    def __init__(self):
        super().__init__()
        self.menu = QComboBox()
        self.label = QLabel("Resolution")
        self.menu.addItem('512x512')
        self.menu.addItem('1024x1024')
        self.menu.addItem('2048x2048')
        self.menu.addItem('4096x4096')
        self.menu.addItem('8192x8192')
        self.menu.addItem('16384x16384')
        self.addWidget(self.label,0,1)
        self.addWidget(self.menu,1,1)

class DwellTimeSelector(QGridLayout):
    def __init__(self):
        super().__init__()
        self.spinbox = QSpinBox()
        self.label = QLabel("Dwell Time")
        self.spinbox.setRange(1,255)
        self.spinbox.setSingleStep(1)
        self.addWidget(self.label,0,1)
        self.addWidget(self.spinbox,1,1)

class ImportPatternFileWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Import Pattern File")
        self.layout = QGridLayout()
        self.setLayout(self.layout)

        self.file_dialog = QFileDialog()
        self.file_dialog.setNameFilter("tr(Images (*.bmp)")
        self.layout.addWidget(self.file_dialog)

    def show_and_get_file(self):
        self.show()
        if self.file_dialog.exec():
            self.file_path = self.file_dialog.selectedFiles()[0]
            print(self.file_path)
            self.show_pattern(self.file_path)
            # self.hide()
            return self.file_path

    def show_pattern(self, file_path):
        bmp = bmp_import(file_path)
        print(bmp)
        path_label = QLabel(file_path)
        height, width = bmp.size
        size_label = QLabel("Height: " + str(height) + "px  Width: " + str(width) + "px")
        self.layout.addWidget(path_label, 0, 0)
        self.layout.addWidget(size_label, 1, 0)
        array = np.array(bmp).astype(np.uint8)
        # graphicsview = pg.GraphicsView()

        self.image_display = ImageDisplay(height, width)
        self.image_display.live_img.setImage(array)
        
        self.layout.addWidget(self.image_display)

        self.resolution_options = ResolutionDropdown()

        # if any(height < self.dimension, width < self.dimension):
        #     error_label = QLabel("Image dimensions exceed current scan resolution")
        #     self.layout.addWidget(error_label)
        # else:
        self.go_button = QPushButton("Go")
        self.layout.addWidget(self.go_button)
        self.go_button.clicked.connect(self.go)

    @asyncSlot()
    async def go(self):
        self.hide()

def pattern_loop(dimension, pattern_stream):
    while 1:
        for n in range(int(dimension*dimension/16384)): #packets per frame
            print(n)
            yield pattern_stream[n*16384:(n+1)*16384]
        print("pattern complete")




class ImageDisplay(pg.GraphicsLayoutWidget):
    def __init__(self, height, width):
        super().__init__()
        self.image_view = self.addViewBox()
        ## lock the aspect ratio so pixels are always square
        self.image_view.setAspectLocked(True)
        self.image_view.setRange(QtCore.QRectF(0, 0, height, width))
        
        self.live_img = pg.ImageItem(border='w',axisOrder="row-major", invertY=False, invertX=False)
        self.image_view.addItem(self.live_img)

        # Contrast/color control
        hist = pg.HistogramLUTItem()
        hist.setImageItem(self.live_img)
        hist.disableAutoHistogramRange()
        self.addItem(hist)

        self.exporter = pg.exporters.ImageExporter(self.live_img)
    def setRange(self, height, width):
        self.image_view.setRange(QtCore.QRectF(0, 0, height, width))

class MainWindow(QWidget):

    def __init__(self):
        super().__init__()
        self.dimension = scan_controller.dimension

        self.setWindowTitle("Scan Control")
        self.layout = QGridLayout()
        self.setLayout(self.layout)


        self.conn_btn = QPushButton("Disconnected")
        self.conn_btn.setCheckable(True) 
        self.conn_btn.clicked.connect(self.connect)

        self.mode_select_dropdown = QComboBox()
        self.mode_select_dropdown.addItem("Imaging")
        self.mode_select_dropdown.addItem("Patterning")
        self.mode_select_dropdown.currentIndexChanged.connect(self.mode_select)

        self.loopback_btn = QPushButton("Loopback Off")
        self.loopback_btn.setCheckable(True) 
        self.loopback_btn.clicked.connect(self.set_loopback)

        self.start_btn = QPushButton('▶️')
        self.start_btn.setCheckable(True) #when clicked, button.isChecked() = True until clicked again
        self.start_btn.clicked.connect(self.toggle_scan)

        self.new_scan_btn = QPushButton('↻')
        self.new_scan_btn.clicked.connect(self.reset_scan)

        self.save_btn = QPushButton('save')
        self.save_btn.clicked.connect(self.saveImage)
        
        

        mode_options = QGridLayout()
        mode_options.addWidget(self.conn_btn,0,0)
        mode_options.addWidget(self.mode_select_dropdown,0,1)
        mode_options.addWidget(self.loopback_btn,0,3)
        mode_options.addWidget(self.start_btn,0,4)
        mode_options.addWidget(self.new_scan_btn,0,5)
        mode_options.addWidget(self.save_btn, 0, 6)


        self.layout.addLayout(mode_options,0,0)

        self.resolution_options = ResolutionDropdown()
        self.layout.addLayout(self.resolution_options, 1,0)
        self.resolution_options.menu.currentIndexChanged.connect(self.changeResolution)

        self.dwell_options = DwellTimeSelector()
        self.layout.addLayout(self.dwell_options, 1,1)
        self.dwell_options.spinbox.valueChanged.connect(self.changeDwellTime)

        self.new_pattern_btn = QPushButton('Pattern file')
        self.new_pattern_btn.clicked.connect(self.file_select)
        self.layout.addWidget(self.new_pattern_btn, 1,1)
        self.new_pattern_btn.setHidden(True)

        self.image_display = ImageDisplay(512, 512)
        self.image_display.live_img.setImage(scan_controller.buf) #set blank 512x512 image
        self.layout.addWidget(self.image_display)

        self.setState("disconnected")
        self.mode = "Imaging"


    def file_select(self):
        self.file_dialog = ImportPatternFileWindow()
        self.file_path = self.file_dialog.show_and_get_file()
        print(self.file_path)
        pattern_stream = bmp_to_bitstream(self.file_path, self.dimension, self.dimension)
        self.pattern = pattern_loop(self.dimension, pattern_stream)
        # self.image_display.image_view.addItem(self.file_dialog.image_display.live_img) #oof
        # self.image_display.image_view.autoRange()
        # print(self.image_display.image_view.allChildren())
        

    @asyncSlot()
    async def connect(self):
        connection = await scan_controller.connect()
        self.conn_btn.setText(connection)
        if connection == "Connected":
            self.setState("scan_not_started")
    
    @asyncSlot()
    async def mode_select(self):
        await scan_controller.reset_scan()
        await scan_controller.set_mode()
        self.mode = self.mode_select_dropdown.currentText()
        if self.mode == "Imaging":
            print("Imaging")
            self.new_pattern_btn.setHidden(True)
            self.dwell_options.label.setHidden(False)
            self.dwell_options.spinbox.setHidden(False)
        if self.mode == "Patterning":
            print("Patterning")
            self.dwell_options.label.setHidden(True)
            self.dwell_options.spinbox.setHidden(True)
            self.new_pattern_btn.setHidden(False)
            
            

    @asyncSlot()
    async def set_loopback(self):
        await scan_controller.set_loopback()
        if self.loopback_btn.isChecked():
            self.loopback_btn.setText("Loopback On")
        else:
            self.loopback_btn.setText("Loopback Off")
        

    @asyncSlot()
    async def reset_scan(self):
        await scan_controller.reset_scan()

    @asyncSlot()
    async def toggle_scan(self):
        if self.start_btn.isChecked():
            self.start_btn.setText('🔄')
            self.mode = self.mode_select_dropdown.currentText()
            await scan_controller.start_scan()
            # if mode == "Imaging":
            #     await scan_controller.start_scan()
            #     await scan_controller.start_scan_pattern_stream(pattern_stream)
            loop = asyncio.get_event_loop()
            print("GUI", loop)
            self.update_continously = asyncio.ensure_future(self.keepUpdating())
            self.setState("scanning")
            self.start_btn.setText('⏸️')

        else:
            print("Stopped scanning now")
            self.start_btn.setText('🔄')
            self.update_continously.cancel()
            await scan_controller.stop_scan()
            # if self.mode == "Patterning":
            #     scan_controller.writer.write_eof()
            self.start_btn.setText('▶️')
            self.setState("scan_paused")
    
    @asyncSlot()
    async def changeResolution(self):
        res_bits = self.resolution_options.menu.currentIndex() + 9 #9 through 14
        dimension = pow(2,res_bits)
        await scan_controller.set_resolution(res_bits)
        self.image_display.setRange(dimension, dimension)
        self.dimension = dimension
        print("setting resolution to", dimension)

    @asyncSlot()
    async def changeDwellTime(self):
        dwell_time = self.dwell_options.spinbox.cleanText()
        await scan_controller.set_dwell_time(int(dwell_time))
        print("setting dwell time to", dwell_time)

    async def keepUpdating(self):
        while True:   
            try:
                await self.updateData()
            except RuntimeError:
                print("error")
                break
    
    async def updateData(self):
        print("mode=", self.mode)
        if self.mode == "Imaging":
            await scan_controller.get_single_packet()
        if self.mode == "Patterning":
            pattern_slice = (next(self.pattern)).tobytes(order='C')
            print("sending single packet")
            await scan_controller.send_single_packet(pattern_slice)
            print("recieving single packet")
            await scan_controller.get_single_packet()
        # scan_controller.stream_to_buffer(data)
        self.image_display.live_img.setImage(scan_controller.buf, autoLevels = False)
        print(scan_controller.buf)
    

    def saveImage(self):
        self.image_display.exporter.parameters()['height'] = self.dimension
        self.image_display.exporter.parameters()['width'] = self.dimension
        img_name = "saved" + datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + ".tif"
        self.image_display.exporter.export(img_name)
        print(img_name)
        
    def setState(self, state):
        if state == "disconnected":
            self.start_btn.setEnabled(False)
            self.new_scan_btn.setEnabled(False)
            self.loopback_btn.setEnabled(False)
            self.resolution_options.menu.setEnabled(False)
            self.dwell_options.spinbox.setEnabled(False)
            self.mode_select_dropdown.setEnabled(False)
        if state == "scan_not_started":
            self.start_btn.setEnabled(True)
            self.loopback_btn.setEnabled(True)
            self.resolution_options.menu.setEnabled(True)
            self.dwell_options.spinbox.setEnabled(True)
            self.mode_select_dropdown.setEnabled(True)
        if state == "scanning":
            self.new_scan_btn.setEnabled(False)
            self.loopback_btn.setEnabled(False)
            self.resolution_options.menu.setEnabled(False)
            self.dwell_options.spinbox.setEnabled(False)
        if state == "scan_paused":
            self.new_scan_btn.setEnabled(True)
            self.loopback_btn.setEnabled(True)
            self.resolution_options.setEnabled(True)
            self.dwell_options.setEnabled(True)






w = MainWindow()





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

    w.show()

    await future
    return True


if __name__ == "__main__":
    try:
        qasync.run(main())
    except asyncio.exceptions.CancelledError:
        sys.exit(0)

