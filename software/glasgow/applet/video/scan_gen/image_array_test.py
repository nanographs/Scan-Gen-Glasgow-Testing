import numpy as np



dimension = 9
frame_data = np.zeros([dimension, dimension])



def image_array():
    x = 0
    y = 0
    
    for index in range(0,len(data)):
        pixel = data[index]
        if pixel == 0: # frame sync
            x = 0
            y = 0
            print(frame_data)
        elif pixel == 1: #line sync
            x = 0
            y += 1
        else:
            #print(f'x: {x}, y: {y}')
            if (x < dimension) and (y < dimension):
                frame_data[y][x] = pixel
                x += 1
            

image_array()