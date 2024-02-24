import numpy as np
from PIL import Image, ImageChops
import os
import time


def window(pixel):
    if pixel <= 1:
        pixel = 2
    return pixel


def bmp_import(filename):
    #img_path = os.path.join(os.getcwd(), 'software/glasgow/applet/video/scan_gen/', filename)
    im = Image.open(filename)
    im = im.convert("L")
    return im



def bmp_to_bitstream(filename, x_width=None, y_height=None, invert_color = False):
    im = Image.open(filename)
    height, width = im.size
    if x_width == None:
        x_width = width
    if y_height == None:
        y_height = height
    im = im.convert("L")
    if invert_color:
        im = ImageChops.invert(im)
    #im = im.point(lambda i: window(i))
    pattern_array = np.array(im).astype(np.uint8)

    ## pad the array to fit the full frame resolution
    padding_tb = y_height - height ## difference between height of frame and full resolution
    padding_lr = x_width - width ## difference between width of frame and full resolution
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
    #return pattern_loop(x_width*y_height, pattern_stream)
    return list(pattern_stream), x_width, y_height


def pattern_loop(dimension, pattern_stream):
    while 1:
        for n in range(dimension):
            yield pattern_stream[n]
        print("pattern complete")


if __name__ == "__main__":
    bmp_to_bitstream("Nanographs Pattern Test Logo and Gradients.bmp", 2048, invert_color=False)