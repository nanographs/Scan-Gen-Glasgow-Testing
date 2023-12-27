import csv
import os, datetime
import numpy as np

class ScanDataRun:
    def __init__(self, dimension):
        self.dimension = dimension

        self.n = 0 ### frame number
        self.x = 0 ### pixel number in line
        self.y = 0 ### line number
        #self.frame_data = np.zeros([dimension, dimension])

        self.last_pixel = 0
        self.frame_data = np.zeros([dimension * dimension])

        ### create time stamped folder
        self.save_dir = os.path.join(os.getcwd(), "Scan Capture", datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
        os.makedirs(self.save_dir)

        self.text_file = open(self.save_dir + "/" + "packets.txt","w")
        #csvfile = open('waveform.csv', 'w', newline='')
        #csvwriter = csv.writer(csvfile, delimiter=' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        

    ### Methods for one data packet

    def packet_to_waveform(self,data,direction="i"):
        packet_length = len(data)

        # ## break down data into smaller chunks
        # for index in range (0,len(data), 2048):
        #     data_chunk = data[index:index+2048]

        fig, ax = plt.subplots()
            #ax.plot(data_chunk)
        ax.plot(data)
            #plt.title(f'capture {self.n}, {index} - {index+2048} / {packet_length} bytes')
        plt.title(f'capture {self.n}, {packet_length} bytes')

        ## set aspect ratio of plot
        ratio = .5
        x_left, x_right = ax.get_xlim()
        y_low, y_high = ax.get_ylim()
        ax.set_aspect(abs((x_right-x_left)/(y_low-y_high))*ratio)

        plt.tight_layout()

        if direction == "i":
            plt.savefig(f'{self.save_dir}/capture {self.n}.png',
                dpi=300
            )
            # plt.savefig(f'{self.save_dir}/capture {self.n}: {index} - {index+500}.png',
            #     dpi=300
            # )
        elif direction == "o":
            plt.savefig(f'{self.save_dir}/outgoing capture {self.n}.png',
                dpi=300
            )
            # plt.savefig(f'{self.save_dir}/outgoing capture {self.n}: {index} - {index+500}.png',
            #     dpi=300
            # )
        plt.close() #clear figure

    def packet_to_txt_file_xy(self,data):
        packet_length = len(data)
        self.text_file.write("<=======================================================================================================================================>\n")
        self.text_file.write(f'PACKET LENGTH: {packet_length}\n')
        for index in range(0,len(data)):
            pixel = data[index]
            self.text_file.write(f'{pixel} at {self.x}, {self.y}\n')
            if pixel == 0: # frame sync
                self.text_file.write(f'FRAME SYNC: FRAME {self.n}\n')
            elif pixel == 1: #line sync
                self.text_file.write(f'LINE SYNC: Y {self.y}\n')
            else:
                if (self.x < self.dimension) and (self.y < self.dimension):
                    pass
                else:
                    self.text_file.write(f'LINE OVERFLOW\n')

    def packet_to_txt_file(self,data,direction="i"):
        packet_length = len(data)
        self.text_file.write("\n<=======================================================================================================================================>\n")
        if direction == "i":
            self.text_file.write(f'RECIEVED PACKET LENGTH: {packet_length}\n')
        elif direction == "o":
            self.text_file.write(f'SENT PACKET LENGTH: {packet_length}\n')
        self.text_file.write(", ".join([str(x) for x in data]))

    ### Methods for one complete frame


    def frame_display_mpl(self):
        fig, ax = plt.subplots()
        plt.imshow(self.frame_data)
        plt.set_cmap("gray")
        plt.tight_layout()
        #plt.savefig(self.save_dir + "/" + "frame" + str(self.n) + '.png')
        plt.show()
        plt.close()


class color:
    black = '\033[30m'
    red = '\033[31m'
    green = '\033[32m'
    orange = '\033[33m'
    blue = '\033[34m'
    purple = '\033[35m'
    cyan = '\033[36m'
    lightgrey = '\033[37m'
    end = '\033[0m'

class CommandLine:
    def __init__(self):
        pass
        
    def show_progress_bar(self, current):
        bar_length = 50
        frame_size = current.dimension*current.dimension
        p = round(bar_length*(current.y*current.dimension + current.x) / frame_size)
        progress = color.green + "#"* p + color.end
        remaining = " "* (bar_length - p)
        print("[" + progress + remaining + "]")

        # for really fast updating text display
        # print("[" + progress + remaining + "]\t"
        #         + color.purple + "Y:" + color.end + "{: >5}".format(current.y) + "\t"
        #         + color.purple + "X:" + color.end + "{: >5}".format(current.x) + "\t/" + "\t"
        #         + "Y:" + "{: >5}".format(current.dimension) + "\t"
        #         + "X:" + "{: >5}".format(current.dimension) + "\t"
        #         )

    
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

if __name__ == "__main__":
    bmp_to_bitstream("Nanographs Pattern Test Logo and Gradients.bmp", 2048, invert_color=False)