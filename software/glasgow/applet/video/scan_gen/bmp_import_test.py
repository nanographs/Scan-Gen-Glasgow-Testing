# load and show an image with Pillow
from PIL import Image
import numpy as np
import os
# Open the image form working directory
image = Image.open(os.path.join(os.getcwd(), 'software/glasgow/applet/video/scan_gen/Nanographs Pattern Test Logo and Gradients.bmp'))
# summarize some details about the image
print(image.format)
print(image.size)
print(image.mode)
# show the image

data = np.asarray(image)
print(type(data))

print(data)

#list = np.ravel(data)

print(list)


print(str(list))

bitstream = str(list(np.ravel(data)))

#byteslist = bytes(list)

#print(byteslist)


with open("patternbytes_v2.txt","w") as file:
    file.write(bitstream)