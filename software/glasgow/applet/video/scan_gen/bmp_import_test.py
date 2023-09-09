# load and show an image with Pillow
from PIL import Image
import numpy as np
import os
# Open the image form working directory
# image = Image.open(os.path.join(os.getcwd(), 'software/glasgow/applet/video/scan_gen/Nanographs Pattern Test Logo and Gradients.bmp'))
# # summarize some details about the image
# print(image.format)
# print(image.size)
# print(image.mode)
# # show the image

# data = np.asarray(image)
# print(type(data))

# print(data)

# #list = np.ravel(data)

# print(list)


# print(str(list))

# bitstream = str(list(np.ravel(data)))

# #byteslist = bytes(list)
# []
# #print(byteslist)


# with open("patternbytes_v2.txt","w") as file:
#     file.write(bitstream)

# pattern_img = Image.open(os.path.join(os.getcwd(), 'software/glasgow/applet/video/scan_gen/Nanographs Pattern Test Logo and Gradients.bmp'))
# pattern_array = np.asarray(pattern_img)
# pattern_array[0] = [1]*pattern_array.shape[0]
# pattern_array[0][0] = 0
# pattern_stream = np.ravel(pattern_array)
# print(pattern_stream)

dimension = 512

def bmp_to_bitstream(filename, boolean=False):
    pattern_img = Image.open(os.path.join(os.getcwd(), 'software/glasgow/applet/video/scan_gen/', filename))
    pattern_array = np.array(pattern_img).astype(np.uint8)
    height, width = pattern_array.shape

    padding_tb = dimension - height
    padding_lr = dimension - width
    padding_top = round(padding_tb/2)
    padding_bottom = padding_tb - padding_top
    padding_left = round(padding_lr/2)
    padding_right = padding_lr - padding_left
    padding = ((padding_top, padding_bottom),(padding_left,padding_right))

    pattern_array = np.pad(pattern_array,pad_width = padding)
    print(pattern_array)
    
    pattern_array[0] = [2]*width
    pattern_array[0][0] = 2
    for i in range(height):
        for j in range(width):
            if not boolean:
                if pattern_array[i][j] < 2:
                    pattern_array[i][j] = 2
            if boolean:
                if pattern_array[i][j] == 1:
                    pattern_array[i][j] = 2
                if pattern_array[i][j] == 0:
                    pattern_array[i][j] = 254
    pattern_array.tofile("patternbytes_v4.txt", sep = ", ")
    pattern_stream_og = np.ravel(pattern_array)
    offset_px = 0
    pattern_stream = np.concatenate((pattern_stream_og[offset_px:],pattern_stream_og[0:offset_px]),axis=None)
    return pattern_stream




#filename = "Nanographs Pattern Test Logo and Gradients.bmp"
filename = "tanishq 02.bmp"
pattern_stream = bmp_to_bitstream(filename, boolean=True)
    

