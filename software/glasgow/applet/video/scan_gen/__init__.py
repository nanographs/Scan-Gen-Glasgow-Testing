import logging
import asyncio
from amaranth import *
from amaranth.sim import Simulator
import csv
import matplotlib.pyplot as plt
import os, datetime
import numpy as np

from .scan_gen_components.bus_state_machine import ScanIOBus
#from .scan_gen_components import pg_gui 



### GUI
import sys
from math import sin
from threading import Thread
from time import sleep

from PyQt6.QtWidgets import QApplication

from pglive.sources.data_connector import DataConnector
from pglive.sources.live_plot import LiveLinePlot
from pglive.sources.live_plot_widget import LivePlotWidget
###

from ... import *

BUS_WRITE_X = 0x01
BUS_WRITE_Y = 0x02
BUS_READ = 0x03
BUS_FIFO_1 = 0x04
BUS_FIFO_2 = 0x05
FIFO_WAIT = 0x06



######################
###### DATA BUS ######
######################



class DataBusAndFIFOSubtarget(Elaboratable):
    def __init__(self, pads, in_fifo, out_fifo, resolution_bits):
        self.pads     = pads
        self.in_fifo  = in_fifo
        self.out_fifo = out_fifo

        self.resolution_bits = resolution_bits ## 9x9 = 512, etc.

        self.datain = Signal(14)

    def elaborate(self, platform):
        m = Module()

        m.submodules.scan_bus = scan_bus = ScanIOBus(self.resolution_bits)

        x_latch = platform.request("X_LATCH")
        x_enable = platform.request("X_ENABLE")
        y_latch = platform.request("Y_LATCH")
        y_enable = platform.request("Y_ENABLE")
        a_latch = platform.request("A_LATCH")
        a_enable = platform.request("A_ENABLE")

        a_clock = platform.request("A_CLOCK")
        d_clock = platform.request("D_CLOCK")


        m.d.comb += [
            x_latch.eq(scan_bus.x_latch),
            x_enable.eq(scan_bus.x_enable),
            y_latch.eq(scan_bus.y_latch),
            y_enable.eq(scan_bus.y_enable),
            a_latch.eq(scan_bus.a_latch),
            a_enable.eq(scan_bus.a_enable),
            a_clock.eq(scan_bus.a_clock),
            d_clock.eq(scan_bus.d_clock),
            scan_bus.fifo_ready.eq(0)
        ]

        with m.If(scan_bus.bus_state == BUS_WRITE_X):
            m.d.comb += [
                self.pads.a_t.oe.eq(self.pads.p_t.i), 
                self.pads.a_t.o.eq(scan_bus.x_data[0]), ## LSB
                self.pads.b_t.oe.eq(self.pads.p_t.i),
                self.pads.b_t.o.eq(scan_bus.x_data[1]),
                self.pads.c_t.oe.eq(self.pads.p_t.i),
                self.pads.c_t.o.eq(scan_bus.x_data[2]),
                self.pads.d_t.oe.eq(self.pads.p_t.i),
                self.pads.d_t.o.eq(scan_bus.x_data[3]),
                self.pads.e_t.oe.eq(self.pads.p_t.i),
                self.pads.e_t.o.eq(scan_bus.x_data[4]),
                self.pads.f_t.oe.eq(self.pads.p_t.i),
                self.pads.f_t.o.eq(scan_bus.x_data[5]),
                self.pads.g_t.oe.eq(self.pads.p_t.i),
                self.pads.g_t.o.eq(scan_bus.x_data[6]),
                self.pads.h_t.oe.eq(self.pads.p_t.i),
                self.pads.h_t.o.eq(scan_bus.x_data[7]),
                self.pads.i_t.oe.eq(self.pads.p_t.i),
                self.pads.i_t.o.eq(scan_bus.x_data[8]),
                self.pads.j_t.oe.eq(self.pads.p_t.i),
                self.pads.j_t.o.eq(scan_bus.x_data[9]),
                self.pads.k_t.oe.eq(self.pads.p_t.i),
                self.pads.k_t.o.eq(scan_bus.x_data[10]),
                self.pads.l_t.oe.eq(self.pads.p_t.i),
                self.pads.l_t.o.eq(scan_bus.x_data[11]),
                self.pads.m_t.oe.eq(self.pads.p_t.i),
                self.pads.m_t.o.eq(scan_bus.x_data[12]),
                self.pads.n_t.oe.eq(self.pads.p_t.i),
                self.pads.n_t.o.eq(scan_bus.x_data[13]), ## MSB
            ]
        
        with m.If(scan_bus.bus_state == BUS_WRITE_Y):
            m.d.comb += [
                self.pads.a_t.oe.eq(self.pads.p_t.i),
                self.pads.a_t.o.eq(scan_bus.y_data[0]), ## LSB
                self.pads.b_t.oe.eq(self.pads.p_t.i),
                self.pads.b_t.o.eq(scan_bus.y_data[1]),
                self.pads.c_t.oe.eq(self.pads.p_t.i),
                self.pads.c_t.o.eq(scan_bus.y_data[2]),
                self.pads.d_t.oe.eq(self.pads.p_t.i),
                self.pads.d_t.o.eq(scan_bus.y_data[3]),
                self.pads.e_t.oe.eq(self.pads.p_t.i),
                self.pads.e_t.o.eq(scan_bus.y_data[4]),
                self.pads.f_t.oe.eq(self.pads.p_t.i),
                self.pads.f_t.o.eq(scan_bus.y_data[5]),
                self.pads.g_t.oe.eq(self.pads.p_t.i),
                self.pads.g_t.o.eq(scan_bus.y_data[6]),
                self.pads.h_t.oe.eq(self.pads.p_t.i),
                self.pads.h_t.o.eq(scan_bus.y_data[7]),
                self.pads.i_t.oe.eq(self.pads.p_t.i),
                self.pads.i_t.o.eq(scan_bus.y_data[8]),
                self.pads.j_t.oe.eq(self.pads.p_t.i),
                self.pads.j_t.o.eq(scan_bus.y_data[9]),
                self.pads.k_t.oe.eq(self.pads.p_t.i),
                self.pads.k_t.o.eq(scan_bus.y_data[10]),
                self.pads.l_t.oe.eq(self.pads.p_t.i),
                self.pads.l_t.o.eq(scan_bus.y_data[11]),
                self.pads.m_t.oe.eq(self.pads.p_t.i),
                self.pads.m_t.o.eq(scan_bus.y_data[12]),
                self.pads.n_t.oe.eq(self.pads.p_t.i),
                self.pads.n_t.o.eq(scan_bus.y_data[13]), ## MSB
            ]
        
        with m.If(scan_bus.bus_state == BUS_READ):
            m.d.sync += [
                ## LOOPBACK
                self.datain[0].eq(scan_bus.x_data[6]),
                self.datain[1].eq(scan_bus.x_data[7]),
                self.datain[2].eq(scan_bus.x_data[8]),
                self.datain[3].eq(scan_bus.x_data[9]),
                self.datain[4].eq(scan_bus.x_data[10]),
                self.datain[5].eq(scan_bus.x_data[11]),
                self.datain[6].eq(scan_bus.x_data[12]),
                self.datain[7].eq(scan_bus.x_data[13]),


                ## Fixed Value
                # self.datain[0].eq(1),
                # self.datain[1].eq(1),
                # self.datain[2].eq(1),
                # self.datain[3].eq(1),
                # self.datain[4].eq(1),
                # self.datain[5].eq(1),
                # self.datain[6].eq(1),
                # self.datain[7].eq(0),

                ## Actual input
                # self.datain[0].eq(self.pads.g_t.i), 
                # self.datain[1].eq(self.pads.h_t.i),
                # self.datain[2].eq(self.pads.i_t.i),
                # self.datain[3].eq(self.pads.j_t.i),
                # self.datain[4].eq(self.pads.k_t.i),
                # self.datain[5].eq(self.pads.l_t.i),
                # self.datain[6].eq(self.pads.m_t.i),
                # self.datain[7].eq(self.pads.n_t.i),## MSB

                

                ### Only reading 8 bits right now
                ### so just ignore the rest
                self.datain[8].eq(0),
                self.datain[9].eq(0),
                self.datain[10].eq(0),
                self.datain[11].eq(0),
                self.datain[12].eq(0),
                self.datain[13].eq(0),

            ]

        with m.If(scan_bus.bus_state == BUS_FIFO_2):
            with m.If(self.in_fifo.w_rdy):
                with m.If(self.datain <= 1): #restrict image data to 2-255, save 0-1 for frame/line sync
                    m.d.comb += [
                        self.in_fifo.din.eq(2),
                        self.in_fifo.w_en.eq(1),
                    ]
                with m.Else():
                    m.d.comb += [
                        self.in_fifo.din.eq(self.datain[0:8]),
                        self.in_fifo.w_en.eq(1),
                    ]

        with m.If(scan_bus.bus_state == BUS_FIFO_1):
            with m.If(self.in_fifo.w_rdy):
                with m.If(scan_bus.line_sync & scan_bus.frame_sync):
                    m.d.comb += [
                        self.in_fifo.din.eq(0),
                        self.in_fifo.w_en.eq(1),
                    ]
                with m.Elif(scan_bus.line_sync):
                    m.d.comb += [
                        self.in_fifo.din.eq(1),
                        self.in_fifo.w_en.eq(1),
                    ]

        with m.If(scan_bus.bus_state == FIFO_WAIT):
            with m.If(self.in_fifo.w_rdy):
                m.d.comb += [
                            scan_bus.fifo_ready.eq(1)
                        ]
            with m.Else():
                m.d.comb += [
                            self.in_fifo.flush.eq(1)
                        ]
            
            
        return m


class ScanGenApplet(GlasgowApplet, name="scan-gen"):
    logger = logging.getLogger(__name__)
    help = "boilerplate applet"
    preview = True
    description = """
    /|/|/|/|/|/|/|/|
    /|/|/|/|/|/|/|/|
    /|/|/|/|/|/|/|/|
    /|/|/|/|/|/|/|/|
    """

    # An example of the boilerplate code required to implement a minimal Glasgow applet.
    #
    # The only things necessary for an applet are:
    #   * a subtarget class,
    #   * an applet class,
    #   * the `build` and `run` methods of the applet class.
    #
    # Everything else can be omitted and would be replaced by a placeholder implementation that does
    # nothing. Similarly, there is no requirement to use IN or OUT FIFOs, or any pins at all.
#
    __pins = ("a", "b", "c", "d", "e","f","g","h",
    "i","j","k","l","m","n", "o","p")

    @classmethod
    def add_build_arguments(cls, parser, access):
        super().add_build_arguments(parser, access)
        for pin in cls.__pins:
            access.add_pin_argument(parser, pin, default=True)
        parser.add_argument(
            "-r", "--res", type=int, default=9,
            help="resolution bits (default: %(default)s)")
        parser.add_argument(
            "-c", "--captures", type=int, default=1,
            help="number of captures (default: %(default)s)")


    def build(self, target, args):
        self.mux_interface = iface = target.multiplexer.claim_interface(self, args)
        #iface.add_subtarget(LEDBlinker())
        iface.add_subtarget(DataBusAndFIFOSubtarget(
            pads=iface.get_pads(args, pins=self.__pins),
            in_fifo = iface.get_in_fifo(),
            out_fifo = iface.get_out_fifo(),
            resolution_bits = args.res
        ))
    
    @classmethod
    def add_run_arguments(cls, parser, access):
        super().add_run_arguments(parser, access)

    async def run(self, device, args):
        resolution_bits = args.res
        iface = await device.demultiplexer.claim_interface(self, self.mux_interface, args)

        ### create time stamped folder
        save_dir = os.path.join(os.getcwd(), "Scan Capture", datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
        os.makedirs(save_dir)

        text_file = open(f'{save_dir}/fifo_output.txt', "w")
        #csvfile = open('waveform.csv', 'w', newline='')
        #spamwriter = csv.writer(csvfile, delimiter=' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        self.n = 0

        dimension = pow(2,resolution_bits) + 1
        frame_data = np.zeros([dimension, dimension])
        self.x = 0
        self.y = 0



        def packets_to_txt_file(raw_data):
            raw_length = len(raw_data)
            data = raw_data.tolist()
            text_file.write("<=======================================================================================================================================>\n")
            text_file.write(f'PACKET LENGTH: {raw_length}\n')
            #for index in range (0,len(data)):
                #text_file.write(f'{data[index]}\n')
                #spamwriter.writerow([data[index]])
        
        def packets_to_waveforms(raw_data):
            raw_length = len(raw_data)
            data = raw_data.tolist()

            ## break down data into smaller chunks
            for index in range (0,len(data), 500):
                data_chunk = data[index:index+500]

                fig, ax = plt.subplots()
                ax.plot(data_chunk)
                plt.title(f'capture {self.n}, {index} - {index+500} / {raw_length} bytes')

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

        def display_data(raw_data):
            data = raw_data.tolist()
            if len(data) > 0:
                first = data[0]
                display = "#"*round(first/5)
                print(display)

        def image_array(raw_data):

            data = raw_data.tolist()
            
            for index in range(0,len(data)):
                pixel = data[index]
                text_file.write(f'{pixel} at {self.x}, {self.y}\n')
                if pixel == 0: # frame sync
                    self.x = 0
                    self.y = 0
                    text_file.write(f'FRAME SYNC: FRAME {self.n}\n')
                    print(f'frame {self.n}')
                    print(frame_data)
                    self.n += 1 #count frames for unique file names
                    fig, ax = plt.subplots()
                    plt.imshow(frame_data)
                    plt.set_cmap("gray")
                    plt.tight_layout()
                    plt.savefig(save_dir + "/" + "frame" + str(self.n) + '.png')
                    plt.show()
                    plt.close()

                elif pixel == 1: #line sync
                    self.x = 0
                    self.y += 1
                    text_file.write(f'LINE SYNC: Y {self.y}\n')
                else:
                    #print(f'x: {x}, y: {y}')
                    if (self.x < dimension) and (self.y < dimension):
                        frame_data[self.y][self.x] = pixel
                        self.x += 1
                    else:
                        text_file.write(f'LINE OVERFLOW\n')

        def live_signal(raw_data, connector):

            data = raw_data.tolist()
            
            for index in range(0,len(data)):
                pixel = data[index]
                x = 0
                while running:
                    x += 1
                    connector.cb_append_data_point(pixel, x)
                    sleep(0.005)
                text_file.write(f'{pixel} at {self.x}, {self.y}\n')
                if pixel == 0: # frame sync
                    self.x = 0
                    self.y = 0
                    text_file.write(f'FRAME SYNC: FRAME {self.n}\n')
                    print(f'frame {self.n}')
                    print(frame_data)
                    self.n += 1 #count frames for unique file names

                elif pixel == 1: #line sync
                    self.x = 0
                    self.y += 1
                    text_file.write(f'LINE SYNC: Y {self.y}\n')
                else:
                    #print(f'x: {x}, y: {y}')
                    if (self.x < dimension) and (self.y < dimension):
                        frame_data[self.y][self.x] = pixel
                        self.x += 1
                    else:
                        text_file.write(f'LINE OVERFLOW\n')
                    

        #while True:
            #await display_data()

        async def mpl_output():
            ## get approx the number of packets you need 
            # to contain {captures} images
            ## and then some more

            
            for n in range((args.captures+1)*(round(dimension*dimension/2000)+1)): 
                if self.n < args.captures:
                    print("Reading...")
                    raw_data = await iface.read()
                    packets_to_txt_file(raw_data)
                    #packets_to_waveforms(raw_data)
                    image_array(raw_data) 
                ## at minimum you are going to get the number of images that fit in one packet

        await mpl_output()

        ## PGLive output
        # app = QApplication(sys.argv)
        # running = True

        # plot_widget = LivePlotWidget(title="Line Plot @ 100Hz")
        # plot_curve = LiveLinePlot()
        # plot_widget.addItem(plot_curve)
        # # DataConnector holding 600 points and plots @ 100Hz
        # data_connector = DataConnector(plot_curve, max_points=600, update_rate=100)
            
        # plot_widget.show()

        # for n in range(0,100):
        #     raw_data = await iface.read()
        #     Thread(target=live_signal, args=(raw_data, data_connector,)).start()
        
        # app.exec()
        # running = False


                

        



    @classmethod
    def add_interact_arguments(cls, parser):
        pass

    async def interact(self, device, args, iface):
        pass

# -------------------------------------------------------------------------------------------------

class ScanGenAppletTestCase(GlasgowAppletTestCase, applet=ScanGenApplet):
    @synthesis_test
    def test_build(self):
        self.assertBuilds()