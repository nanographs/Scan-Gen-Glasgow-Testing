import numpy as np
import time

data = [2,2,2,3,4,5,6,7,8,9,10,11,12,13]*3 + [0] + [2,2,2,3,4,5,6,7,8,9,10,11,12,13]*5

data_2 = [2,2,2,3,4,5,6,7,8,9,10,11,12,13]*3

dimension = 14
frame_data_1 = np.zeros([dimension, dimension])



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
                frame_data_1[y][x] = pixel
                x += 1
            

#frame_data = np.zeros([dimension, dimension])
frame_data = np.zeros([dimension*dimension])


class Scan:
    def __init__(self):
        last_pixel = 0

scan = Scan()

frame_data = np.zeros([dimension*dimension])
print(frame_data[dimension*dimension-1])
def new_func(data):
    d = np.array(data)
    zero_index = np.nonzero(d < 1)[0]
    if len(zero_index) > 0: #if a zero was found
        zero_index = int(zero_index)
        frame_data[0:zero_index] = d[0:zero_index]
        rem = len(frame_data) - len(d[zero_index:])
        frame_data[rem:] = d[zero_index:]
        scan.last_pixel = zero_index
    else: 
        if len(frame_data[scan.last_pixel:scan.last_pixel+len(data)]) < len(d):
            print("data too long to fit in end of frame, but no zero")
        frame_data[scan.last_pixel:scan.last_pixel+len(data)] = d
        scan.last_pixel = scan.last_pixel+len(data)
    print(frame_data)
    

# start = time.perf_counter()
# image_array()
# end = time.perf_counter()
# print("image array:", end-start)

start = time.perf_counter()
new_func(data)
end = time.perf_counter()
print("new func:", end-start)

start = time.perf_counter()
new_func(data_2)
new_func(data_2)
new_func(data_2)
new_func(data_2)
new_func(data_2)
new_func(data_2)
new_func(data_2)
new_func(data_2)
end = time.perf_counter()
print("new func:", end-start)