import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

logging.basicConfig(filename='otherlogs.txt', filemode='w', level=logging.DEBUG)

from threading import Thread

import asyncio
import functools
import sys

from PIL import Image

import os, datetime

import numpy as np

from PyQt6.QtWidgets import (QMainWindow, QPushButton, QHBoxLayout,
                            QGridLayout, QWidget, QComboBox, 
                            QLabel, QSpinBox, QFileDialog)

import pyqtgraph as pg
from pyqtgraph.dockarea import DockArea, Dock
from pyqtgraph.exporters import Exporter
from pyqtgraph.Qt import QtCore

import qasync
from qasync import asyncSlot, asyncClose, QApplication, QEventLoop

#from microscope import ScanCtrl, ScanStream
from threading_test import ScanInterface
from gui_modules.image_display import ImageDisplay
from gui_modules.frame_settings import FrameSettings, RegisterUpdateBox


from bmp_utils import *


app = pg.mkQApp("Scan Control")

cwd = os.getcwd()

# # Open the qss styles file and read in the CSS-like styling code
# with open(cwd + '/software/glasgow/applet/video/scan_gen/output_formats/styles.qss', 'r') as f:
#     style = f.read()
#     # Set the stylesheet of the application
#     app.setStyleSheet(style)


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


class StreamFrameSettings(FrameSettings):
    def __init__(self, con):
        super().__init__(RegisterUpdateBox)
        self.con = con

        self.rx.spinbox.valueChanged.connect(self.set_x)
        self.ry.spinbox.valueChanged.connect(self.set_y)

    
    def set_x(self):
        xval = self.rx.getval()
        self.con.set_x_resolution(xval)
        self.con.strobe_config()

    def set_y(self):
        yval = self.ry.getval()
        self.con.set_y_resolution(yval)
        self.con.strobe_config()


class MainWindow(QWidget):

    def __init__(self):
        super().__init__()
        self.con = ScanInterface()

        self.setWindowTitle("Scan Control")
        self.layout = QGridLayout()
        self.setLayout(self.layout)

        self.image_display = ImageDisplay(510,510)
        self.image_display.setRange(510,510)
        self.layout.addWidget(self.image_display, 1, 0)

        self.frame_settings = StreamFrameSettings(self.con)
        self.layout.addLayout(self.frame_settings, 2, 0)

        self.dwellselect = RegisterUpdateBox("Dwell Time", 1, 255, 1)
        self.frame_settings.addLayout(self.dwellselect)
        self.dwellselect.spinbox.valueChanged.connect(self.change_dwell)

        self.conn_btn = QPushButton("Click to Connect")
        self.conn_btn.setCheckable(True) 
        self.conn_btn.clicked.connect(self.connect)


        self.mode_select_dropdown = QComboBox()
        self.mode_select_dropdown.addItem("Imaging")
        self.mode_select_dropdown.addItem("Raster Patterning")
        self.mode_select_dropdown.addItem("Vector Patterning")

        self.mode_select_dropdown.currentIndexChanged.connect(self.set_scan_mode)


        self.start_btn = QPushButton('▶️')
        self.start_btn.setCheckable(True) #when clicked, button.isChecked() = True until clicked again
        self.start_btn.clicked.connect(self.toggle_scan)

        self.reset_btn = QPushButton("Clear")
        self.reset_btn.clicked.connect(self.reset_display)

        self.roi_btn = QPushButton("ROI")
        self.roi_btn.setCheckable(True) 
        self.roi_btn.clicked.connect(self.toggle_ROI)

        self.info_btn = QPushButton('?')
        self.info_btn.clicked.connect(self.getinfo)

        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.image_display.saveImage_PIL)


        mode_options = QGridLayout()
        mode_options.addWidget(self.conn_btn,0,0)
        mode_options.addWidget(self.mode_select_dropdown,0,1)
        mode_options.addWidget(self.start_btn,0,2)
        mode_options.addWidget(self.reset_btn,0,3)
        mode_options.addWidget(self.roi_btn,0,4)
        #mode_options.addWidget(self.info_btn,0,4)
        mode_options.addWidget(self.save_btn, 0, 5)

        self.layout.addLayout(mode_options,0,0)

    def file_select(self):
        self.file_dialog = ImportPatternFileWindow()
        self.file_path = self.file_dialog.show_and_get_file()
        print(self.file_path)
        pattern_stream = bmp_to_bitstream(self.file_path, self.dimension)
        self.pattern = pattern_loop(self.dimension, pattern_stream)
        # self.image_display.image_view.addItem(self.file_dialog.image_display.live_img) #oof
        # self.image_display.image_view.autoRange()
        # print(self.image_display.image_view.allChildren())

    @asyncSlot()
    async def reset_display(self):
        self.con.scan_stream.clear_buffer()
        await self.updateData()

    @asyncSlot()
    async def getinfo(self):
        tasks = asyncio.all_tasks()
        for task in tasks:
            print(task.get_name(), ":", task.get_coro())
            task.print_stack()

    @asyncSlot()
    async def change_dwell(self):
        dval = self.dwellselect.getval()
        await self.con.set_dwell_time(dval)

    def toggle_ROI(self):
        if self.roi_btn.isChecked():
            self.add_ROI()
        else:
            self.image_display.remove_ROI()

    def add_ROI(self):
        self.image_display.add_ROI()
        self.image_display.roi.sigRegionChanged.connect(self.get_ROI)

    @asyncSlot()
    async def get_ROI(self):
        x_lower, x_upper, y_lower, y_upper = self.image_display.get_ROI()
        await self.con.set_ROI(x_lower, x_upper, y_lower, y_upper)
        await self.con.strobe_config()

    @asyncSlot()
    async def connect(self):
        self.con.start()
        self.transmit_current_settings()
        self.con.strobe_config()

    def transmit_current_settings(self):
        x_width, y_height = self.frame_settings.getframe()
        self.con.set_x_resolution(x_width)
        self.con.set_y_resolution(y_height)
        mode = self.mode_select_dropdown.currentIndex() + 1
        self.con.set_scan_mode(mode)


    def set_scan_mode(self):
        mode = self.mode_select_dropdown.currentIndex() + 1
        self.con.set_scan_mode(mode)
        if mode == 1:
            self.con.set_8bit_output()
        if mode == 3:
            self.con.set_16bit_output()
        self.con.strobe_config()

    @asyncSlot()   
    async def toggle_scan(self):
        if self.start_btn.isChecked():
            print("starting scan")
            self.start_btn.setText('🔄')
            #await self.updateData()
            self.con.unpause()
            self.update_continously = asyncio.ensure_future(self.keepUpdating())
            
            # loop = asyncio.get_event_loop()
            # loop.create_task(self.keepUpdating())
            # self.setState("scanning")
            self.start_btn.setText('⏸️')

        else:
            print("Stopped scanning now")
            self.start_btn.setText('🔄')
            self.con.stream_pattern = False
            self.con.pause()
            self.update_continously.cancel()
            self.start_btn.setText('▶️')

    async def keepUpdating(self):
        while True:   
            #print("keep updating")
            #await asyncio.sleep(0)
            await self.updateData()
                
            # except RuntimeError:
            #     print("error")
            #     break

    async def updateData(self):
        # print("*", self.con.data_client._buffer.data_processed)
        # async with self.con.data_client._buffer.data_processed:
        #     await self.con.data_client._buffer.data_processed.wait()
        print("updating display")
        self.image_display.setImage(self.con.buffer.scan_stream.y_height, self.con.buffer.scan_stream.x_width, self.con.buffer.scan_stream.buffer)

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
            self.resolution_options.menu.setEnabled(True)
            self.dwell_options.spinbox.setEnabled(True)



def run_gui():
    app = QApplication(sys.argv)

    event_loop = QEventLoop(app)
    asyncio.set_event_loop(event_loop)

    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)

    main_window = MainWindow()
    main_window.show()

    with event_loop:
        event_loop.run_until_complete(app_close_event.wait())

    return main_window

if __name__ == "__main__":
    run_gui()
