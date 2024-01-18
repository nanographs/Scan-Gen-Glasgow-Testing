import numpy as np
import pyqtgraph as pg
from pyqtgraph.exporters import Exporter
from pyqtgraph.Qt import QtCore

from PyQt6.QtWidgets import (QHBoxLayout, QMainWindow,
                             QMessageBox, QPushButton, QComboBox,
                             QVBoxLayout, QWidget, QLabel, QGridLayout,
                             QSpinBox)

from gui_modules.frame_settings import FrameSettings
from gui_modules.image_display import ImageDisplay
from scan_stream import ScanStream

class ScanMainWindow(QWidget):

    def __init__(self, frame_settings):
        super().__init__()

        self.setWindowTitle("Scan Control")
        self.layout = QGridLayout()
        self.setLayout(self.layout)

        self.image_display = ImageDisplay(512,512)
        self.image_display.setRange(512,512)
        self.layout.addWidget(self.image_display, 1, 0)

        self.frame_settings = frame_settings
        self.layout.addLayout(self.frame_settings, 2, 0)

        self.conn_btn = QPushButton("Click to Connect")
        self.conn_btn.setCheckable(True) 

        self.frame_settings.pattern_settings.dropdown.currentIndexChanged.connect(self.set_pattern)

        self.mode_select_dropdown = QComboBox()
        self.mode_select_dropdown.addItem("Imaging")
        self.mode_select_dropdown.addItem("Raster Patterning")
        self.mode_select_dropdown.addItem("Vector Patterning")

        self.start_btn = QPushButton('▶️')
        self.start_btn.setCheckable(True) #when clicked, button.isChecked() = True until clicked again
        #self.start_btn.clicked.connect(self.toggle_scan)

        self.reset_btn = QPushButton("Clear")
        #self.reset_btn.clicked.connect(self.reset_display)

        self.roi_btn = QPushButton("ROI")
        self.roi_btn.setCheckable(True) 
        self.roi_btn.clicked.connect(self.toggle_ROI)

        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.image_display.saveImage_PIL)


        mode_options = QGridLayout()
        mode_options.addWidget(self.conn_btn,0,0)
        mode_options.addWidget(self.mode_select_dropdown,0,1)
        mode_options.addWidget(self.start_btn,0,2)
        mode_options.addWidget(self.reset_btn,0,3)
        mode_options.addWidget(self.roi_btn,0,4)
        mode_options.addWidget(self.save_btn, 0, 5)

        self.layout.addLayout(mode_options,0,0)

        #self.setState("disconnected")

    def toggle_ROI(self):
        print(f'roi mode? {self.roi_btn.isChecked()}')
        if self.roi_btn.isChecked():
            self.add_ROI()
        else:
            self.image_display.remove_ROI()

    def add_ROI(self):
        self.image_display.add_ROI()
        self.image_display.roi.sigRegionChanged.connect(self.set_ROI)

    def get_ROI(self):
        #return self.image_display.get_ROI()
        x_lower, x_upper, y_lower, y_upper = self.image_display.get_ROI()
        print(f'x: {x_lower} - {x_upper}; y: {y_lower} - {y_upper}')
        return x_lower, x_upper, y_lower, y_upper
    
    def getframe(self):
        return self.frame_settings.getframe()


    def scale_pattern(self):
        index = self.frame_settings.pattern_settings.dropdown.currentIndex()
        gen = self.frame_settings.pattern_settings.patterns[index]
        x_width, y_height = self.getframe()
        dwell = self.frame_settings.dwell.getval()
        
        print(f'roi mode? {self.roi_btn.isChecked()}')
        if self.roi_btn.isChecked():
            print("scaling pattern to ROI")
            x_lower, x_upper, y_lower, y_upper = self.get_ROI()
            
        else:
            print("no ROI")
            x_lower, x_upper, y_lower, y_upper = None, None, None, None
            
            
            
        
        return gen.create(x_width, y_height, dwell, x_lower, x_upper, y_lower, y_upper)

    def setState(self, state):
        if state == "disconnected":
            self.start_btn.setEnabled(False)
            self.reset_btn.setEnabled(False)
            self.frame_settings.setEnabled(False)
            self.mode_select_dropdown.setEnabled(False)
            self.frame_settings.pattern_settings.dropdown.setEnabled(False)
            self.roi_btn.setEnabled(False)
            self.save_btn.setEnabled(False)
        if state == "scan_not_started":
            self.start_btn.setEnabled(True)
            self.frame_settings.setEnabled(True)
            self.mode_select_dropdown.setEnabled(True)
            self.frame_settings.pattern_settings.dropdown.setEnabled(True)
            self.roi_btn.setEnabled(True)
            self.save_btn.setEnabled(True)
        if state == "scanning":
            self.reset_btn.setEnabled(False)
            self.mode_select_dropdown.setEnabled(False)
        if state == "scan_paused":
            self.reset_btn.setEnabled(True)
            self.mode_select_dropdown.setEnabled(True)

    

class Mockup(ScanMainWindow):
    def __init__(self):
        frame_settings = FrameSettings()
        super().__init__(frame_settings)
        self.stream = ScanStream()
    
    def set_pattern(self):
        x_width, y_height = self.getframe()
        self.stream.change_buffer(x_width, y_height)
        pattern = self.scale_pattern()
        print(f'got pattern: {pattern}')
        while True:
            try:
                x = next(pattern)
                y = next(pattern)
                a = next(pattern)
                self.stream.buffer[y][x] = a
                print(x,y,a)
            except StopIteration:
                break
        self.image_display.setImage(y_height, x_width, self.stream.buffer)
    
    def set_ROI(self):
        print (self.get_ROI())



if __name__ == "__main__":
    app = pg.mkQApp()
    w = Mockup()
    w.show()
    pg.exec()