import asyncio
import functools
import sys

import tifffile
from tifffile import imwrite

import os, datetime

import numpy as np

from PyQt6.QtWidgets import QMainWindow, QPushButton

import pyqtgraph as pg
from pyqtgraph.dockarea import DockArea, Dock
from pyqtgraph.exporters import Exporter
from pyqtgraph.Qt import QtCore

import qasync
from qasync import asyncSlot, asyncClose, QApplication

from microscope import ScanController


app = pg.mkQApp("Scan Control")

cwd = os.getcwd()

# # Open the qss styles file and read in the CSS-like styling code
# with open(cwd + '/software/glasgow/applet/video/scan_gen/output_formats/styles.qss', 'r') as f:
#     style = f.read()
#     # Set the stylesheet of the application
#     app.setStyleSheet(style)



scan_controller = ScanController()

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Scan Control")
        self.conn_btn = QPushButton("Disconnected")
        self.conn_btn.clicked.connect(self.connect)

        # Set the central widget of the Window.
        self.setCentralWidget(self.conn_btn)
    
    @asyncSlot()
    async def connect(self):
        connection = await scan_controller.connect()
        self.conn_btn.setText(connection)



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

