"""
Demonstrates very basic use of ImageItem to display image data inside a ViewBox.
"""


import numpy as np

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore

app = pg.mkQApp("ImageItem Example")

## Create window with GraphicsView widget
win = pg.GraphicsLayoutWidget()
win.show()  ## show widget alone in its own window
win.setWindowTitle('/|/|/|/| scanning /|/|/|/|')
view = win.addViewBox()

## lock the aspect ratio so pixels are always square
view.setAspectLocked(True)

## Create image item
img = pg.ImageItem(border='w')
view.addItem(img)
## Set initial view bounds
view.setRange(QtCore.QRectF(0, 0, 512, 512))
pg.exec()

