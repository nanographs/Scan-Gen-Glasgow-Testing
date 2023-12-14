import numpy as np
import pyqtgraph as pg
from pyqtgraph.exporters import Exporter
from pyqtgraph.Qt import QtCore

from PyQt6.QtWidgets import (QHBoxLayout, QMainWindow,
                             QMessageBox, QPushButton,
                             QVBoxLayout, QWidget, QLabel, QGridLayout,
                             QSpinBox)


class RegisterUpdateBox(QGridLayout):
    def __init__(self, label, lower_limit, upper_limit, initial_val):
        super().__init__()
        self.name = label
        self.label = QLabel(label)
        self.addWidget(self.label,0,1)

        self.spinbox = QSpinBox()
        self.spinbox.setRange(lower_limit, upper_limit)
        self.spinbox.setSingleStep(1)
        self.spinbox.setValue(initial_val)
        self.addWidget(self.spinbox,1,1)

    def addButton(self):
        self.btn = QPushButton("->")
        self.addWidget(self.btn, 2, 1)

    def getval(self):
        return int(self.spinbox.cleanText())


class FrameSettings(QHBoxLayout):
    def __init__(self, boxType = RegisterUpdateBox):
        super().__init__()
        self.boxType = boxType
        self.registers = []

        self.rx = self.addRegister("X Resolution", 1, 16384, 512)
        self.ry = self.addRegister("Y Resolution", 1, 16384, 512)

    def addRegister(self, label, lower_limit, upper_limit, initial_val):
        register_box = self.boxType(label, lower_limit, upper_limit, initial_val)
        self.registers.append(register_box)
        self.addLayout(register_box)
        return register_box

    def addButton(self):
        self.btn = QPushButton("->")
        self.addWidget(self.btn) 
        return self.btn

    def getframe(self):
        x_width = self.rx.getval()
        y_height = self.ry.getval()
        return x_width, y_height



if __name__ == "__main__":
    app = pg.mkQApp()
    settings = FrameSettings()
    settings.addButton()
    w = QWidget()
    w.setLayout(settings)
    w.show()
    pg.exec()
