import matplotlib.pyplot as plt
import csv
import os, datetime
import numpy as np

class ScanDataRun:
    def __init__(self, dimension):
        self.dimension = dimension

        self.n = 0 ### frame number
        self.x = 0 ### pixel number in line
        self.y = 0 ### line number
        self.frame_data = np.zeros([dimension, dimension])

        ### create time stamped folder
        self.save_dir = os.path.join(os.getcwd(), "Scan Capture", datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
        os.makedirs(self.save_dir)

        
        #csvfile = open('waveform.csv', 'w', newline='')
        #csvwriter = csv.writer(csvfile, delimiter=' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        

    ### Methods for one data packet

    def packet_to_waveform(self,data):
        packet_length = len(data)

        ## break down data into smaller chunks
        for index in range (0,len(data), 500):
            data_chunk = data[index:index+500]

            fig, ax = plt.subplots()
            ax.plot(data_chunk)
            plt.title(f'capture {self.n}, {index} - {index+500} / {packet_length} bytes')

            ## set aspect ratio of plot
            ratio = .5
            x_left, x_right = ax.get_xlim()
            y_low, y_high = ax.get_ylim()
            ax.set_aspect(abs((x_right-x_left)/(y_low-y_high))*ratio)

            plt.tight_layout()

            plt.savefig(f'{save_dir}/capture {self.n}: {index} - {index+500}.png',
                dpi=300
            )
            plt.close() #clear figure

    def packet_to_txt_file(self,data):
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