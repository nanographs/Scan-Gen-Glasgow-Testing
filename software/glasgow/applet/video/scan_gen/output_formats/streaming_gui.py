import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

logging.basicConfig(filename='otherlogs.txt', filemode='w', level=logging.DEBUG)

import asyncio
import functools
import sys

import tifffile
from tifffile import imwrite
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
from new_socket_test import ConnectionManager
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

class StreamRegisterUpdateBox(RegisterUpdateBox):
    def __init__(self, label, lower_limit, upper_limit, initial_val, con=None, msgfn=None):
        super().__init__(label, lower_limit, upper_limit, initial_val)
        self.msgfn = msgfn
        self.con = con

    @asyncSlot()
    async def do_fn(self):
        val = self.getval()
        print("set", self.name, ":", val)
        msg = self.msgfn(val)
        await self.con.tcp_msg_client([self.con.scan_ctrl.raise_config_flag(), msg])


class StreamFrameSettings(FrameSettings):
    def __init__(self, con):
        super().__init__(StreamRegisterUpdateBox)
        self.con = con
        self.btn = self.addButton()
        self.btn.clicked.connect(self.do_fns)

        self.rx.con = self.con
        self.rx.msgfn = self.con.scan_ctrl.set_x_resolution
        self.ry.con = self.con
        self.ry.msgfn = self.con.scan_ctrl.set_y_resolution

    @asyncSlot()
    async def do_fns(self):
        for register in self.registers:
            await register.do_fn()

class MainWindow(QWidget):

    def __init__(self):
        super().__init__()
        # scan_controller = ScanController()
        # self.x_width = scan_controller.x_width
        # self.y_height = scan_controller.y_height

        # self.scan_ctrl = ScanCtrl()
        # self.scan_stream = ScanStream()
        self.con = ConnectionManager()

        self.setWindowTitle("Scan Control")
        self.layout = QGridLayout()
        self.setLayout(self.layout)

        self.image_display = ImageDisplay(512,512)
        self.image_display.setRange(512,512)
        self.layout.addWidget(self.image_display, 1, 0)

        self.frame_settings = StreamFrameSettings(self.con)
        self.layout.addLayout(self.frame_settings, 2, 0)

        self.frame_settings.btn.clicked.connect(self.updateFrameSize)

        self.conn_btn = QPushButton("Click to Connect")
        self.conn_btn.setCheckable(True) 
        self.conn_btn.clicked.connect(self.connect)


        # self.mode_select_dropdown = QComboBox()
        # self.mode_select_dropdown.addItem("Imaging")
        # self.mode_select_dropdown.addItem("Patterning")
        # self.mode_select_dropdown.currentIndexChanged.connect(self.mode_select)

        # self.loopback_btn = QPushButton("Loopback Off")
        # self.loopback_btn.setCheckable(True) 
        # self.loopback_btn.clicked.connect(self.set_loopback)

        self.start_btn = QPushButton('▶️')
        self.start_btn.setCheckable(True) #when clicked, button.isChecked() = True until clicked again
        self.start_btn.clicked.connect(self.toggle_scan)

        # self.new_scan_btn = QPushButton('↻')
        # self.new_scan_btn.clicked.connect(self.reset_scan)

        # # self.save_btn = QPushButton('save')
        # # self.save_btn.clicked.connect(self.saveImage)
        
        

        # mode_options = QGridLayout()
        self.layout.addWidget(self.conn_btn,0,0)
        # mode_options.addWidget(self.mode_select_dropdown,0,1)
        # mode_options.addWidget(self.loopback_btn,0,3)
        self.layout.addWidget(self.start_btn,0,1)
        # mode_options.addWidget(self.new_scan_btn,0,5)
        # # mode_options.addWidget(self.save_btn, 0, 6)


        # self.layout.addLayout(mode_options,0,0)

        # self.resolution_options = ResolutionDropdown()
        # self.layout.addLayout(self.resolution_options, 1,0)
        # self.resolution_options.menu.currentIndexChanged.connect(self.changeResolution)

        # self.dwell_options = DwellTimeSelector()
        # self.layout.addLayout(self.dwell_options, 1,1)
        # self.dwell_options.spinbox.valueChanged.connect(self.changeDwellTime)

        # self.new_pattern_btn = QPushButton('Pattern file')
        # self.new_pattern_btn.clicked.connect(self.file_select)
        # self.layout.addWidget(self.new_pattern_btn, 1,1)
        # self.new_pattern_btn.setHidden(True)

        # self.image_display = ImageDisplay(512, 512)
        # self.image_display.live_img.setImage(scan_controller.buf) #set blank 512x512 image
        # self.layout.addWidget(self.image_display)

        # self.setState("disconnected")
        # self.mode = "Imaging"

        # self.image_display.showTest()

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
    async def updateFrameSize(self):
        x_width, y_height = self.frame_settings.getframe()
        print("updating frame size",x_width, y_height)
        self.con.scan_stream.change_buffer(x_width, y_height)
        #self.image_display.setRange(x_width, y_height)
        #self.image_display.live_img.setImage(np.zeros((y_height, x_width)).astype(np.uint8), rect = (0,0,x_width, y_height))

    @asyncSlot()
    async def connect(self):
        await self.con.recieve_data_client()
        await self.con.tcp_msg_client(["sc00000", self.con.scan_ctrl.raise_config_flag()])
        # await self.con.tcp_msg_client("ry16384")
        # if connection == "Connected":
        #     self.setState("scan_not_started")


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
            print("starting scan")
            self.start_btn.setText('🔄')
            loop = asyncio.get_event_loop()
            loop.create_task(self.con.start_reading())
            self.update_continously = asyncio.ensure_future(self.keepUpdating())
            # self.setState("scanning")
            self.start_btn.setText('⏸️')

        else:
            print("Stopped scanning now")
            self.start_btn.setText('🔄')
            #self.update_continously.cancel()
            loop = asyncio.get_event_loop()
            loop.create_task(self.con.stop_reading())
            # if self.mode == "Patterning":
            #     scan_controller.writer.write_eof()
            # self.setState("scan_paused")
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
