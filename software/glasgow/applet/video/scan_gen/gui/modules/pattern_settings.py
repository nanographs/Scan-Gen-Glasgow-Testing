import numpy as np
import pyqtgraph as pg
from pyqtgraph.exporters import Exporter
from pyqtgraph.Qt import QtCore

from PyQt6.QtWidgets import (QHBoxLayout, QMainWindow,
                             QMessageBox, QPushButton, QComboBox,
                             QVBoxLayout, QWidget, QLabel, QGridLayout,
                             QSpinBox)

if "glasgow" in __name__:
    from .pattern_generators.hilbert import hilbert
    from .pattern_generators.rectangles import vector_rectangle, vector_gradient_rectangle
else:
    from pattern_generators.hilbert import hilbert
    from pattern_generators.rectangles import vector_rectangle, vector_gradient_rectangle

    
class PatternGen:
    def __init__(self, label, gen):
        self.label = label
        self.gen = gen
    def create(self, *args):
        return self.gen(*args), self.gen(*args)


class PatternSettings(QVBoxLayout):
    def __init__(self):
        super().__init__()
        self.patterns = []
        self.dropdown = QComboBox()
        self.addWidget(QLabel("Select Pattern:"))
        self.addWidget(self.dropdown)
        #h = PatternGen("Hilbert", hilbert())
        rec1 = PatternGen("Solid Rect", vector_rectangle)
        rec2 = PatternGen("Gradient Rect", vector_gradient_rectangle)
        self.addOption(rec1)
        self.addOption(rec2)

    def addOption(self, patterngen):
        self.dropdown.addItem(patterngen.label)
        self.patterns.append(patterngen)
    



if __name__ == "__main__":
    app = pg.mkQApp()
    settings = PatternSettings()
    w = QWidget()
    w.setLayout(settings)
    w.show()
    pg.exec()
