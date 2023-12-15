import numpy as np
import pyqtgraph as pg
from pyqtgraph.exporters import Exporter
from pyqtgraph.Qt import QtCore

from PyQt6.QtWidgets import (QHBoxLayout, QMainWindow,
                             QMessageBox, QPushButton,
                             QVBoxLayout, QWidget, QLabel, QGridLayout,
                             QSpinBox)



class ImageDisplay(pg.GraphicsLayoutWidget):
    def __init__(self, y_height, x_width):
        super().__init__()
        self.y_height = y_height
        self.x_width = x_width

        self.image_view = self.addViewBox(invertY = True)
        ## lock the aspect ratio so pixels are always square
        self.image_view.setAspectLocked(True)
        self.image_view.setRange(QtCore.QRectF(0, 0, y_height, x_width))
        
        self.live_img = pg.ImageItem(border='w',axisOrder="row-major")
        self.live_img.setImage(np.full((y_height, x_width), 0, np.uint8), rect = (0,0,x_width, y_height))
        self.image_view.addItem(self.live_img)

        # Contrast/color control
        self.hist = pg.HistogramLUTItem()
        self.hist.setImageItem(self.live_img)
        self.hist.disableAutoHistogramRange()
        self.addItem(self.hist)

        self.hist.setLevels(min=0,max=255)


        ### reverse the default LUT
        lut = []
        for n in range(0, 256):
            lut.append([255-n,255-n,255-n])
        
        lut = np.array(lut, dtype = np.uint8)
        self.live_img.setLookupTable(lut)


        self.exporter = pg.exporters.ImageExporter(self.live_img)

        #self.add_ROI()

    def add_ROI(self):
        border = pg.mkPen(color = "#00ff00", width = 5)
        # Custom ROI for selecting an image region
        roi = pg.ROI([100, 100], [200, 400], pen = border)
        roi.addScaleHandle([0.5, 1], [0.5, 0.5])
        roi.addScaleHandle([0, 0.5], [0.5, 0.5])
        self.image_view.addItem(roi)
        roi.setZValue(10)  # make sure ROI is drawn above image

    def setImage(self, y_height, x_width, image):
        ## image must be 2D np.array of np.uint8
        self.live_img.setImage(image, rect = (0,0, x_width, y_height))


    def setRange(self, y_height, x_width):
        self.image_view.setRange(QtCore.QRectF(0, 0, x_width, y_height))
    
    def showTest(self):
        # test_file = "software/glasgow/applet/video/scan_gen/output_formats/Nanographs Pattern Test Logo and Gradients.bmp"
        # bmp = bmp_import(test_file)
        # array = np.array(bmp).astype(np.uint8)
        array = np.random.randint(0, 255,size = (512,512))
        array = array.astype(np.uint8)
        self.live_img.setImage(array)

    def saveImage(self):
        self.exporter.parameters()['height'] = self.dimension
        self.exporter.parameters()['width'] = self.dimension
        img_name = "saved" + datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + ".tif"
        self.exporter.export(img_name)
        print(img_name)

if __name__ == "__main__":
    app = pg.mkQApp()
    image_display = ImageDisplay(512, 512)
    image_display.showTest()
    image_display.show()
    pg.exec()