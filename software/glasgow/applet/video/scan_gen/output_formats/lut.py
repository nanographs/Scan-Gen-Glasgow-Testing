import pyqtgraph as pg
import numpy as np
from pyqtgraph.Qt import QtCore

from PyQt6.QtWidgets import (QMainWindow, QPushButton, 
                            QGridLayout, QWidget, QComboBox, 
                            QLabel, QSpinBox, QFileDialog)


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

        self.showTest()



        lut = []
        for n in range(0, 256):
            lut.append([255-n,255-n,255-n])
        
        lut = np.array(lut, dtype = np.uint8)
        self.live_img.setLookupTable(self.lut)


        # color = self.live_img.getColorMap()
        # print(color)
        # color = color.reverse()
        # self.live_img.setColorMap(color)

        # self.exporter = pg.exporters.ImageExporter(self.live_img)


    def setRange(self, height, width):
        self.image_view.setRange(QtCore.QRectF(0, 0, width, height))
    
    def showTest(self):
        # test_file = "software/glasgow/applet/video/scan_gen/output_formats/Nanographs Pattern Test Logo and Gradients.bmp"
        # bmp = bmp_import(test_file)
        # array = np.array(bmp).astype(np.uint8)
        array = np.random.randint(0, 255,size = (512,512))
        array = array.astype(np.uint8)
        self.live_img.setImage(array)

black = pg.mkColor(0)
white = pg.mkColor(255)
print(black)
print(vars(black))

app = pg.mkQApp()
w = ImageDisplay(512,512)
# n = np.full((512,512), 255)
# w.live_img.setImage(n)
w.show()
pg.exec()