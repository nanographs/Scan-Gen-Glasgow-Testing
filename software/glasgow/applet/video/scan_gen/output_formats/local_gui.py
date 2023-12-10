import numpy as np
import os

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore

from PyQt6.QtWidgets import (QMainWindow, QPushButton, 
                            QGridLayout, QWidget, QComboBox, 
                            QLabel, QSpinBox, QFileDialog)

from even_newer_gui import ImageDisplay



class MainWindow(QWidget):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.layout = QGridLayout()
        self.setLayout(self.layout)
        
        self.image_display = ImageDisplay(2048, 2048)
        self.layout.addWidget(self.image_display, 1, 0)

        elapsed = 0

        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        # not using QTimer.singleShot() because of persistence on PyQt. see PR #1605
    
    def get_dimensions(self):
        settings = np.loadtxt(os.path.join(self.path, "current_display_setting"))
        dimension = int(settings)
        return dimension
    def get_buffer(self):
        FrameBufDirectory = os.path.join(self.path, "current_frame")

    def updateData(self):
        d = np.memmap(self.FrameBufDirectory, shape = (dimension*dimension),mode = "r+")
        data = np.reshape(d,(dimension,dimension))
        #data = np.random.rand(dimension,dimension)

        print(data)
        print(data.shape)
        self.image_display.live_img.setImage(data) #this is the correct orientation to display the image
        
        self.timer.start(1)

    def startUpdating(self):
        self.timer.timeout.connect(self.updateData)
        self.updateData()


def run_gui(path):
    app = pg.mkQApp("Scan Live View")
    w = MainWindow(path)
    w.show()
    pg.exec()


if __name__ == '__main__':
    run_gui(os.getcwd())

