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

if __name__ == "__main__":
    import sys
    import os
    path = os.path.split(sys.path[0])[0]
    sys.path.append(path)

    from interface.scan_socket import ScanInterface
    from modules.image_display import ImageDisplay
    from modules.frame_settings import FrameSettings, RegisterUpdateBox
    from generic_gui import ScanMainWindow
    from pattern_generators.bmp_utils import *


app = pg.mkQApp("Scan Control")

cwd = os.getcwd()

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

    def __init__(self, con):
        self.con = con
        frame_settings = StreamFrameSettings(con)
        super().__init__(frame_settings)
        self.conn_btn.clicked.connect(self.connect)

        self.frame_settings.pattern_settings.dropdown.currentIndexChanged.connect(self.set_pattern)

        self.mode_select_dropdown.currentIndexChanged.connect(self.set_scan_mode)

        self.start_btn.clicked.connect(self.toggle_scan)

        self.reset_btn.clicked.connect(self.reset_display)
        
        self.setState("disconnected")

    def file_select(self):
        super().file_select()
        self.con.set_patterngen(self.pattern)

    def set_pattern(self):
        print("setting pattern...")
        gen1, gen2 = self.scale_pattern()
        print(f'g1: {gen2}, g2: {gen2}')
        self.con.set_patterngen(gen1)
        self.con.scan_stream.patterngen = gen2

    @asyncSlot()
    async def reset_display(self):
        self.con.scan_stream.clear_buffer()
        await self.updateData()
    

    @asyncSlot()
    async def set_ROI(self):
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
        await self.set_scan_mode()


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
            if (mode == 3) | (mode == 2):
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
    main_window = MainWindow(con)
    main_window.show()

    with event_loop:
        event_loop.run_until_complete(app_close_event.wait())

    return main_window

if __name__ == "__main__":
    run_gui()
