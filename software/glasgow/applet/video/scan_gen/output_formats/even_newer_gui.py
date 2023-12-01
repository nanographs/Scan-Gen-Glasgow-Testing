import sys
import asyncio
import numpy as np

from PyQt6.QtWidgets import QWidget, QGridLayout, QLabel

import pyqtgraph as pg
from pyqtgraph.exporters import Exporter
from pyqtgraph.Qt import QtCore


from qasync import QEventLoop, QApplication, asyncSlot, asyncClose



class MainWindow(QWidget):

    def __init__(self):
        super().__init__()
        data = np.random.randint(low = 1, high = 255, size = (2048,2048))

        self.setWindowTitle("Scan Control")
        self.layout = QGridLayout()
        self.setLayout(self.layout)

        #self.plot_item = pg.PlotItem()
        self.image_display = pg.plot(title="image")
        test_vector_points = [
            [2000, 1000, 30], ## X, Y, D
            [1000, 2000, 40],
            [3000, 2500, 50],
        ]

        self.scatter = pg.ScatterPlotItem()
        for n in test_vector_points:
            self.add_point(n)
            
        self.layout.addWidget(self.image_display)
        self.image_display.addItem(self.scatter)

    def add_point(self,n):
        x, y, d, = n
        brush=pg.mkBrush(d)
        self.scatter.addPoints([x], [y], brush = brush)


def run():
    app = QApplication(sys.argv)

    event_loop = QEventLoop(app)
    asyncio.set_event_loop(event_loop)

    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)

    main_window = MainWindow()
    main_window.show()

    with event_loop:
        event_loop.run_until_complete(app_close_event.wait())

if __name__ == "__main__":
    run()