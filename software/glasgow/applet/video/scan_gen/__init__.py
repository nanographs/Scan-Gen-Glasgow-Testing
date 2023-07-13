import logging
import asyncio
from amaranth import *
from amaranth.sim import Simulator
import csv
import matplotlib.pyplot as plt
import os, datetime
import numpy as np
from tifffile import imread, imwrite, TiffFile
import random
import time
import threading
from rich import print

from .scan_gen_components.bus_state_machine import ScanIOBus
#from .scan_gen_components import pg_gui 
from .output_formats import ScanDataRun, CommandLine


from ... import *

BUS_WRITE_X = 0x01
BUS_WRITE_Y = 0x02
BUS_READ = 0x03
BUS_FIFO_1 = 0x04
BUS_FIFO_2 = 0x05
FIFO_WAIT = 0x06
A_RELEASE = 0x07


######################
###### DATA BUS ######
######################



class DataBusAndFIFOSubtarget(Elaboratable):
    def __init__(self, pads, in_fifo, out_fifo, resolution_bits, dwell_time):
        self.pads     = pads
        self.in_fifo  = in_fifo
        self.out_fifo = out_fifo

        self.resolution_bits = resolution_bits ## 9x9 = 512, etc.
        self.dwell_time = dwell_time

        self.datain = Signal(14)

        self.running_average_two = Signal(14)

    def elaborate(self, platform):
        m = Module()

        m.submodules.scan_bus = scan_bus = ScanIOBus(self.resolution_bits, self.dwell_time)

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
            #scan_bus.fifo_ready.eq(0)
            scan_bus.fifo_ready.eq(self.in_fifo.w_rdy)
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
                # self.datain[0].eq(scan_bus.x_data[6]),
                # self.datain[2].eq(scan_bus.x_data[8]),
                # self.datain[1].eq(scan_bus.x_data[7]),
                # self.datain[3].eq(scan_bus.x_data[9]),
                # self.datain[4].eq(scan_bus.x_data[10]),
                # self.datain[5].eq(scan_bus.x_data[11]),
                # self.datain[6].eq(scan_bus.x_data[12]),
                # self.datain[7].eq(scan_bus.x_data[13]),


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
                self.datain[0].eq(self.pads.g_t.i), 
                self.datain[1].eq(self.pads.h_t.i),
                self.datain[2].eq(self.pads.i_t.i),
                self.datain[3].eq(self.pads.j_t.i),
                self.datain[4].eq(self.pads.k_t.i),
                self.datain[5].eq(self.pads.l_t.i),
                self.datain[6].eq(self.pads.m_t.i),
                self.datain[7].eq(self.pads.n_t.i),## MSB

                ### Only reading 8 bits right now
                ### so just ignore the rest
                self.datain[8].eq(0),
                self.datain[9].eq(0),
                self.datain[10].eq(0),
                self.datain[11].eq(0),
                self.datain[12].eq(0),
                self.datain[13].eq(0),
            ]

        with m.If(scan_bus.bus_state == A_RELEASE):
            with m.If(scan_bus.dwell_ctr_ovf):
                m.d.sync += [
                    self.running_average_two.eq(self.datain),
                ]
            with m.Else():
                m.d.sync += [
                    self.running_average_two.eq((self.running_average_two + self.datain)//2),
                ]

        with m.If(scan_bus.dwell_ctr_ovf):
            with m.If(scan_bus.bus_state == BUS_FIFO_1):
                with m.If(self.in_fifo.w_rdy):
                    with m.If(self.running_average_two <= 1): #restrict image data to 2-255, save 0-1 for frame/line sync
                        m.d.comb += [
                            self.in_fifo.din.eq(2),
                            self.in_fifo.w_en.eq(1),
                        ]
                    with m.Else():
                        m.d.comb += [
                            self.in_fifo.din.eq(self.running_average_two[0:8]),
                            self.in_fifo.w_en.eq(1),
                        ]

            with m.If(scan_bus.bus_state == BUS_FIFO_2):
                with m.If(self.in_fifo.w_rdy):
                    with m.If(scan_bus.line_sync & scan_bus.frame_sync):
                        m.d.comb += [
                            self.in_fifo.din.eq(0),
                            self.in_fifo.w_en.eq(1),
                        ]
                # with m.Elif(scan_bus.line_sync):
                #     m.d.comb += [
                #         self.in_fifo.din.eq(1),
                #         self.in_fifo.w_en.eq(1),
                #     ]

        # with m.If(scan_bus.bus_state == FIFO_WAIT):
        #     with m.If(self.in_fifo.w_rdy):
        #         m.d.comb += [
        #                     scan_bus.fifo_ready.eq(1)
        #                 ]
        #     with m.Else():
        #         m.d.comb += [
        #                     self.in_fifo.flush.eq(1)
        #                 ]
        
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
            "-d", "--dwell", type=int, default=1,
            help="dwell time in clock cycles (default: %(default)s)")
        parser.add_argument(
            "-c", "--captures", type=int, default=1,
            help="number of captures (default: %(default)s)")


    def build(self, target, args):
        self.mux_interface = iface = target.multiplexer.claim_interface(self, args)
        iface.add_subtarget(DataBusAndFIFOSubtarget(
            pads=iface.get_pads(args, pins=self.__pins),
            in_fifo = iface.get_in_fifo(auto_flush=False),
            out_fifo = iface.get_out_fifo(),
            resolution_bits = args.res,
            dwell_time = args.dwell
        ))
    
    @classmethod
    def add_run_arguments(cls, parser, access):
        super().add_run_arguments(parser, access)

    async def run(self, device, args):
        iface = await device.demultiplexer.claim_interface(self, self.mux_interface, args)

        resolution_bits = args.res
        dimension = pow(2,resolution_bits)
        
        current = ScanDataRun(dimension)
        cli = CommandLine() 
        
        np.savetxt(f'Scan Capture/current_display_setting', [dimension])

        buf = np.memmap(f'Scan Capture/current_frame', np.uint8, shape = (dimension*dimension), mode = "w+")

        def display_data(data): ## use to create a basic live display in terminal
            if len(data) > 0:
                first = data[0] ## just read the first byte of every packet
                display = "#"*round(first/5) ## scale it to fit in one line in the terminal
                print(display)




        # def image_array(data): ## this could be moved to output_formats
        #     ## but leaving it here for now, for context
        #     for index in range(0,len(data)):
        #         pixel = data[index]
        #         if pixel == 0: # frame sync
        #             current.x = 0
        #             current.y = 0
        #             #print(f'frame {current.n}')
        #             #print(current.frame_data)
        #             current.n += 1 #count frames for unique file names
        #             ## save frame as .tif
        #             #imwrite(f'{current.save_dir}/frame {current.n}.tif', current.frame_data.astype(np.uint8), photometric='minisblack') 
        #             ## display frame using matplotlib
        #             #current.frame_display_mpl()
        #         elif pixel == 1: #line sync
        #             current.x = 0 ## reset x position to beginning of line
        #             current.y += 1 ## move to next line
        #         else:
        #             ## if there are more than {dimension} data points in one line, ignore them
        #             if (current.x < dimension) and (current.y < dimension):
        #                 current.frame_data[current.y][current.x] = pixel
        #                 #current.frame_data[current.y][current.x] = random.randint(2,255) #use randomly generated data instead
        #                 current.x += 1 ## move to the next pixel in line




        async def get_limited_output():
            ## get approx the number of packets you need 
            # to contain {captures} images
            ## and then some more

            for n in range((args.captures+1)*(round(dimension*dimension/2000)+1)): 
                if current.n < args.captures:
                    #print("Reading...")
                    raw_data = await iface.read()
                    data = raw_data.tolist()
                    #current.text_file = open(f'{current.save_dir}/fifo_output.txt', "w")
                    #current.packet_to_txt_file(data) 
                    #packets_to_waveforms(raw_data)
                    image_array(data) 
                    cli.show_progress_bar(current)
                ## at minimum you are going to get the number of images that fit in one packet

        #await get_limited_output()

        current.last_x = 0
        current.last_y = 0

        empty_frame = np.zeros(shape = dimension*dimension)

        def fn(raw_data):
            # print("-----------")
            # print("frame", current.n)
            data = raw_data.tolist()
            #current.packet_to_txt_file(data)
            d = np.array(data)
            zero_index = np.nonzero(d < 1)[0]
            # print("buffer length:", len(buf))
            # print("last pixel:",current.last_pixel)
            # print("d length:", len(d))
            # print("d:",d)
            
            if len(zero_index) > 0: #if a zero was found
                # current.n += 1
                # print("zero index:",zero_index)
                zero_index = int(zero_index)
                ## save frame as .tif
                # print("saving frame")
                # current.n += 1
                # current.frame_data = np.reshape(buf,(dimension,dimension))
                # imwrite(f'{current.save_dir}/frame {current.n}.tif', current.frame_data.astype(np.uint8), photometric='minisblack') 

                #rem = len(buf) - len(d[zero_index:])
                buf[:d[zero_index+1:].size] = d[zero_index+1:]
                # print(buf[:d[zero_index+1:].size])
                # print(d[:zero_index+1].size)
                buf[dimension * dimension - zero_index:] = d[:zero_index]
                # print(buf[dimension * dimension - zero_index:])
                current.last_pixel = d[zero_index+1:].size
                

            else: 
                # if len(buf[current.last_pixel:current.last_pixel+len(d)]) < len(d):
                #     print("data too long to fit in end of frame, but no zero")
                #     print(d[:dimension])
                buf[current.last_pixel:current.last_pixel + d.size] = d
                # print(buf[current.last_pixel:current.last_pixel + d.size])
                current.last_pixel = current.last_pixel + d.size
            
            

        background_tasks = set()

        start_time = time.perf_counter()
        
        while True:
        #     start = time.perf_counter()
        #     if (start-start_time) > .01:
        #         self.logger.error(msg = ("Raw read start:",start-start_time))
        #     start_time = start
        # for i in range(20):
            raw_data = await iface.read()
            # data = raw_data.tolist()
            # current.packet_to_txt_file(data)
            # end1 = time.perf_counter()
            # print("raw data read", end1-start)
            # if (end1-start) > .01:
            #     self.logger.error(msg = ("Raw read:",end1-start))
            #display_data(data)
            #thread = threading.get_ident()
            #print("A THREAD:", thread)

            threading.Thread(target=fn(raw_data)).start()

            
            # task = asyncio.create_task(fn(raw_data))
            # background_tasks.add(task)
            # task.add_done_callback(background_tasks.discard)

            # end2 = time.perf_counter()
            # print("Task set",end2-end1)
            # if (end2-end1) > .01:
            #     self.logger.error(msg = ("Task set:",end2-end1))


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