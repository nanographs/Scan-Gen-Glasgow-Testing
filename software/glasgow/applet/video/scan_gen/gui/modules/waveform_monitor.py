import datetime
import numpy as np
import pyqtgraph as pg
from pyqtgraph.exporters import Exporter
from pyqtgraph.Qt import QtCore
from pyqtgraph.graphicsItems.TextItem import TextItem

from PyQt6.QtWidgets import (QHBoxLayout, QMainWindow,
                             QMessageBox, QPushButton,
                             QVBoxLayout, QWidget, QLabel, QGridLayout,
                             QSpinBox)

from PIL import Image
import tifffile




class WFM(pg.GraphicsLayoutWidget):
    def __init__(self):
        super().__init__()
        self.plot = self.addPlot(title="WFM")
        self.plot.setMouseEnabled(x=False, y=True)
        self.plot.enableAutoRange(y=True,x=True)
        line_pen = pg.mkPen(color = "#00ff00", width = 2)
        self.line = self.plot.plot(pen=line_pen)
    def setData(self, data):
        self.line.setData(data)




if __name__ == "__main__":
    app = pg.mkQApp()
    wfm = WFM()
    wfm.show()
    wfm.setData()
    pg.exec()