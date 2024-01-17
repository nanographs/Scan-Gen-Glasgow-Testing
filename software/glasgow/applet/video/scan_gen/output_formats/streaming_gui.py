import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

logging.basicConfig(filename='otherlogs.txt', filemode='w', level=logging.DEBUG)

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
from new_socket_test import ScanInterface
from gui_modules.image_display import ImageDisplay
from gui_modules.frame_settings import FrameSettings, RegisterUpdateBox
from generic_gui import ScanMainWindow


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
        self.dwell.spinbox.valueChanged.connect(self.set_dwell)

    
    @asyncSlot()
    async def set_x(self):
        xval = self.rx.getval()
        await self.con.set_x_resolution(xval)
        await self.con.strobe_config()

    @asyncSlot()
    async def set_y(self):
        yval = self.ry.getval()
        await self.con.set_y_resolution(yval)
        await self.con.strobe_config()

    @asyncSlot()
    async def set_dwell(self):
        dval = self.dwell.getval()
        await self.con.set_dwell_time(dval)


class MainWindow(ScanMainWindow):

    def __init__(self, con, frame_settings):
        super().__init__(frame_settings)
        self.conn_btn.clicked.connect(self.connect)

        self.frame_settings.pattern_settings.dropdown.currentIndexChanged.connect(self.set_pattern)

        self.mode_select_dropdown.currentIndexChanged.connect(self.set_scan_mode)

        self.start_btn.clicked.connect(self.toggle_scan)

        self.reset_btn.clicked.connect(self.reset_display)
        
        self.setState("disconnected")

    # def file_select(self):
    #     self.file_dialog = ImportPatternFileWindow()
    #     self.file_path = self.file_dialog.show_and_get_file()
    #     print(self.file_path)
    #     pattern_stream = bmp_to_bitstream(self.file_path, self.dimension)
    #     self.pattern = pattern_loop(self.dimension, pattern_stream)
    #     # self.image_display.image_view.addItem(self.file_dialog.image_display.live_img) #oof
    #     # self.image_display.image_view.autoRange()
    #     # print(self.image_display.image_view.allChildren())


    @asyncSlot()
    async def reset_display(self):
        self.con.scan_stream.clear_buffer()
        await self.updateData()
    
    def set_pattern(self):
        self.con.set_patterngen(self.frame_settings.scale_pattern())

    @asyncSlot()
    async def get_ROI(self):
        x_lower, x_upper, y_lower, y_upper = self.image_display.get_ROI()
        await self.con.set_ROI(x_lower, x_upper, y_lower, y_upper)
        await self.con.strobe_config()

    @asyncSlot()
    async def connect(self):
        await self.transmit_current_settings()
        await self.con.strobe_config()
        await self.con.open_data_client()
        self.setState("scan_not_started")

    @asyncSlot()
    async def transmit_current_settings(self):
        x_width, y_height = self.frame_settings.getframe()
        await self.con.set_x_resolution(x_width)
        await self.con.set_y_resolution(y_height)
        mode = self.mode_select_dropdown.currentIndex() + 1
        await self.con.set_scan_mode(mode)


    @asyncSlot()
    async def set_scan_mode(self):
        mode = self.mode_select_dropdown.currentIndex() + 1
        await self.con.set_scan_mode(mode)
        if mode == 1:
            await self.con.set_8bit_output()
        if mode == 3:
            self.set_pattern()
            await self.con.set_16bit_output()
        await self.con.strobe_config()

        
    @asyncSlot()
    async def toggle_scan(self):
        if self.start_btn.isChecked():
            print("starting scan")
            self.start_btn.setText('🔄')
            await self.con.unpause()
            mode = self.mode_select_dropdown.currentIndex() + 1
            if mode == 3:
                self.con.stream_pattern = True
                await self.con.write_points("*")
            self.update_continously = asyncio.ensure_future(self.keepUpdating())
            self.setState("scanning")
            self.start_btn.setText('⏸️')

        else:
            print("Stopped scanning now")
            self.start_btn.setText('🔄')
            self.con.stream_pattern = False
            await self.con.pause()
            self.update_continously.cancel()
            self.setState("scan_paused")
            self.start_btn.setText('▶️')

    async def keepUpdating(self):
        while True:   
            await asyncio.sleep(0)
            try:
                await self.updateData()
            except RuntimeError:
                print("error")
                break

    async def updateData(self):
        self.image_display.setImage(self.con.scan_stream.y_height, self.con.scan_stream.x_width, self.con.scan_stream.buffer)
        
        




def run_gui():
    app = QApplication(sys.argv)

    event_loop = QEventLoop(app)
    asyncio.set_event_loop(event_loop)

    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)

    con = ScanInterface()
    frame_settings = StreamFrameSettings(con)
    main_window = MainWindow(con, frame_settings)
    main_window.show()

    with event_loop:
        event_loop.run_until_complete(app_close_event.wait())

    return main_window

if __name__ == "__main__":
    run_gui()
