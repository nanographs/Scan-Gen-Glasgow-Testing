import numpy as np
import pyqtgraph as pg
from pyqtgraph.exporters import Exporter
from pyqtgraph.Qt import QtCore

from PyQt6.QtWidgets import (QHBoxLayout, QMainWindow,
                             QMessageBox, QPushButton,
                             QVBoxLayout, QWidget, QLabel, QGridLayout,
                             QSpinBox)


class Setting:
    def __init__(self, label, values):
        self.label = label
        self.values = values

class SettingsArray:
    def __init__(self, registers, values):
        self.registers = registers ## list of RegisterUpdateBox
        self.values = values ## array of values


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
    
    def setval(self, val):
        self.spinbox.setValue(val)


class FrameSettings(QHBoxLayout):
    def __init__(self, boxType = RegisterUpdateBox):
        super().__init__()
        self.boxType = boxType
        self.registers = []

        self.rx = self.addRegister("X Resolution", 1, 16384, 400)
        self.ry = self.addRegister("Y Resolution", 1, 16384, 400)

    def addRegister(self, label, lower_limit, upper_limit, initial_val):
        register_box = self.boxType(label, lower_limit, upper_limit, initial_val)
        self.registers.append(register_box)
        self.addLayout(register_box)
        return register_box

    def addButtonPanel(self, s: SettingsArray):
        self.buttons = ButtonPanel(s)
        self.addLayout(self.buttons)

    def getframe(self):
        x_width = self.rx.getval()
        y_height = self.ry.getval()
        return x_width, y_height


class SettingsButton(QPushButton):
    def __init__(self, label:str, settings, registers):
        super().__init__(label)
        self.label = label
        self.settings = settings
        self.registers = registers #RegisterUpdateBox
        self.clicked.connect(self.updateRegister)

    def updateRegister(self):
        for n in range(len(self.registers)):
            self.registers[n].setval(self.settings[n])


class ButtonPanel(QGridLayout):
    def __init__(self, settings:SettingsArray):
        super().__init__()
        self.btns = []
        self.settings = settings
        print(self.settings.values)
        for row in range(len(self.settings.values)):
            for column in range(len(self.settings.values[row])):
                setting = self.settings.values[row][column]
                self.addBtn(setting.label, setting.values, self.settings.registers, row, column)
                print(row, column)
        # self.addBtn("512", 512, register, 0, 0)
        # self.addBtn("1024", 1024, register, 0, 1)
        # self.addBtn("2048", 2048, register, 0, 2)
    
    def addBtn(self, label, settings, register, row, col):
        btn = SettingsButton(label, settings, register)
        self.addWidget(btn, row, col)
        self.btns.append(btn)



if __name__ == "__main__":
    app = pg.mkQApp()
    settings = FrameSettings()
    s = SettingsArray(
        [settings.rx, settings.ry],
        [
            [Setting("512", [512, 512]), Setting("1024", [1024, 1024])],
            [Setting("2048", [2048, 2048]), Setting("4096", [4096, 4096])],
        ]
    )
    settings.addButtonPanel(s)
    w = QWidget()
    w.setLayout(settings)
    w.show()
    pg.exec()
