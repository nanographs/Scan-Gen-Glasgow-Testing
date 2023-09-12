import numpy as np
from PIL import Image, ImageChops
import os
import time


def window(pixel):
    if pixel <= 1:
        pixel = 2
    return pixel


def bmp_to_bitstream(filename, dimension, invert_color = False):
    img_path = os.path.join(os.getcwd(), 'software/glasgow/applet/video/scan_gen/', filename)
    im = Image.open(img_path)
    height, width = im.size
    im = im.convert("L")
    if invert_color:
        im = ImageChops.invert(im)
    im = im.point(lambda i: window(i))
    pattern_array = np.array(im).astype(np.uint8)

    ## pad the array to fit the full frame resolution
    padding_tb = dimension - height ## difference between height of frame and full resolution
    padding_lr = dimension - width ## difference between width of frame and full resolution
    #   dimension
    # ───────┬──────┐
    #        │      │
    #        │ top  │
    #    ┌───┴───┐  │
    #  l │       │r │
    # ◄──┤       ├──┤
    #    │       │  │
    #    └───┬───┘  │
    #        │      │
    #        ▼ btm  │
    padding_top = round(padding_tb/2) 
    padding_bottom = padding_tb - padding_top
    padding_left = round(padding_lr/2)
    padding_right = padding_lr - padding_left
    padding = ((padding_top, padding_bottom),(padding_left,padding_right))

    pattern_array = np.pad(pattern_array,pad_width = padding, constant_values = 2)
    print(pattern_array)

    pattern_stream = np.ravel(pattern_array)
    return pattern_stream
