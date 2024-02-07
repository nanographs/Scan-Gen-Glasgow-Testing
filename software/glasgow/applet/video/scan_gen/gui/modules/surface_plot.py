import numpy as np

import pyqtgraph as pg
import pyqtgraph.opengl as gl
from pyqtgraph.Qt import QtCore

from ..pattern_generators.bmp_utils import *

## Create a GL View widget to display data
app = pg.mkQApp("GLSurfacePlot Example")
w = gl.GLViewWidget()
w.show()
w.setWindowTitle('pyqtgraph example: GLSurfacePlot')
w.setCameraPosition(distance=1000)


## Simple surface plot example
## x, y values are not specified, so assumed to be 0:50
#z = pg.gaussianFilter(np.random.normal(size=(50,50)), (1,1))
img = bmp_import("software/glasgow/applet/video/scan_gen/output_formats/Nanographs Pattern Test Logo and Gradients.bmp")
array_img = np.array(img)
print(array_img)
#array_img = pg.isosurface(, level =255)
# print(array_img)

#z = pg.gaussianFilter(array_img, (1,1))
p1 = gl.GLSurfacePlotItem(z=array_img, shader='shaded', color=(0.5, 0.5, 1, 1))
#p1 = gl.GLVolumeItem(a)
#p1 = gl.GLImageItem(array_img)
p1.scale(49./49., 49./49., 4.0)
p1.translate(-25, -25, 0)
w.addItem(p1)

if __name__ == '__main__':
    pg.exec()