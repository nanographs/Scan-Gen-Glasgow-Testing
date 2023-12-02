import sys
import asyncio
import numpy as np

from PyQt6.QtWidgets import QWidget, QGridLayout, QLabel, QPushButton

import pyqtgraph as pg
from pyqtgraph.exporters import Exporter
from pyqtgraph.Qt import QtCore


from qasync import QEventLoop, QApplication, asyncSlot, asyncClose

# from bmp_utils import *
from argparse import Namespace

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

    def __init__(self, scan_iface):
        super().__init__()
        self.scan_iface = scan_iface
        data = np.random.randint(low = 1, high = 255, size = (2048,2048))

        self.setWindowTitle("Scan Control")
        self.layout = QGridLayout()
        self.setLayout(self.layout)

        self.image_display = ImageDisplay(2048, 2048)
        #self.layout.addWidget(self.image_display)

        self.scan_btn = QPushButton('!')
        self.scan_btn.clicked.connect(self.do_stuff)

        self.layout.addWidget(self.scan_btn)

    @asyncSlot()
    async def do_stuff(self):
        #await self.scan_iface.send_vec_stream_and_recieve_data()
        data = await self.scan_iface.stream_video()
        print(data)
        
        #self.image_display.showTest()

        # self.image_display = pg.plot(title="image")
        # test_vector_points = [
        #     [2000, 1000, 30], ## X, Y, D
        #     [1000, 2000, 40],
        #     [3000, 2500, 50],
        # ]

    #     self.scatter = pg.ScatterPlotItem()
    #     for n in test_vector_points:
    #         self.add_point(n)
            
    #     
    #     self.image_display.addItem(self.scatter)

    # def add_point(self,n):
    #     x, y, d, = n
    #     brush=pg.mkBrush(d)
    #     self.scatter.addPoints([x], [y], brush = brush)


def run_gui(scan_iface):
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

