import numpy as np
from PIL import Image


def bmp_to_bitstream(filename, boolean=False, invert_color=False, flip_lr=False):
    pattern_img = Image.open(os.path.join(os.getcwd(), 'software/glasgow/applet/video/scan_gen/', filename))
    print(pattern_img)
    ## boolean images will have pixel values of True or False
    ## this will convert that to 1 or 0
    pattern_array = np.array(pattern_img).astype(np.uint8)
    
    height, width = pattern_array.shape[0], pattern_array.shape[1]

    if invert_color:
        for i in range(height):
            for j in range(width):
                pattern_array[i][j] = 255 - pattern_array[i][j]

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

    if flip_lr:
        pattern_array = np.flip(pattern_array, axis=1)
    
    for i in range(dimension):
        for j in range(dimension):
            if not boolean: ## pixel values are from 0 to 255
                if pattern_array[i][j] < 2:
                    pattern_array[i][j] = 2
            if boolean: ## pixel values are 1 or 0 only
                if pattern_array[i][j] == 1:
                    pattern_array[i][j] = 2
                if pattern_array[i][j] == 0:
                    pattern_array[i][j] = 254

    

    #pattern_array[dimension-1][dimension-1] = 0
    print(pattern_array)
    pattern_array.tofile("patternbytes_v4.txt", sep = ", ")

    ## "cut the deck" - move some bits from the beginning of the stream to the end
    pattern_stream_og = np.ravel(pattern_array)
    offset_px = 0
    pattern_stream = np.concatenate((pattern_stream_og[offset_px:],pattern_stream_og[0:offset_px]),axis=None)

    
    return pattern_stream