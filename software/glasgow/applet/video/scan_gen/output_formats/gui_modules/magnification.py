import pyqtgraph as pg
from pyqtgraph.Qt import QtCore

from PyQt6.QtWidgets import (QHBoxLayout, QMainWindow,
                             QMessageBox, QPushButton, QComboBox,
                             QVBoxLayout, QWidget, QLabel, QGridLayout,
                             QSpinBox)



class MagSettings(QHBoxLayout):
    def __init__(self):
        super().__init__()
        self.spinbox = QSpinBox()
        self.spinbox.setRange(100,100000)
        self.addWidget(self.spinbox)
        self.spinbox.valueChanged.connect(self.printval)
    def printval(self):
        print(int(self.spinbox.cleanText()))


if __name__ == "__main__":
    app = pg.mkQApp()
    settings = MagSettings()
    w = QWidget()
    w.setLayout(settings)
    w.show()
    pg.exec()