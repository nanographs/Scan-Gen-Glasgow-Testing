import numpy as np

data = [0,2,2,2,3,4,5,6,7,1,2,2,2,3,4,5,6,7,1,2,2,2,3,4,5,6,7,1,2,2,2,3,4,5,6,7,1,2,2,2,3,4,5,6,7,1,2,2,2,3,4,5,6,7,1,2,2,2,3,4,5,6,7,1,2,2,2,3,4,5,6,7,1]


frame_data = np.zeros([9,9])

x = 0
y = 0

def image_array():
    for index in range(0,len(data)):
        pixel = data[index]
        if pixel == 0: # frame sync
            x = 0
            y = 0
        elif pixel == 1: #line sync
            x = 0
            y += 1
        else:
            x += 1
            frame_data[y][x] = pixel
    print(frame_data)

image_array()