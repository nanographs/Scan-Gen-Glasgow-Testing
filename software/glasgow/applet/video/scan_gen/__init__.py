import logging
import asyncio
from amaranth import *
from amaranth.sim import Simulator
import csv
import matplotlib.pyplot as plt
import os, datetime
import numpy as np
from PIL import Image
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
OUT_FIFO = 0x08


######################
###### DATA BUS ######
######################



class DataBusAndFIFOSubtarget(Elaboratable):
    def __init__(self, pads, in_fifo, out_fifo, resolution_bits, dwell_time, mode, loopback):
        self.pads     = pads
        self.in_fifo  = in_fifo
        self.out_fifo = out_fifo
        self.mode = mode #image or pattern
        self.loopback = loopback #True if in loopback 

        self.resolution_bits = resolution_bits ## 9x9 = 512, etc.
        self.dwell_time = dwell_time

        self.datain = Signal(14)

        self.running_average_two = Signal(14)

        self.out_fifo_f = Signal(8)

    def elaborate(self, platform):
        m = Module()

        m.submodules.scan_bus = scan_bus = ScanIOBus(self.resolution_bits, self.dwell_time, self.mode)

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
            scan_bus.in_fifo_ready.eq(self.in_fifo.w_rdy),
            scan_bus.out_fifo_ready.eq(self.out_fifo.r_rdy),
            

            
        ]

        # m.d.sync += [scan_bus.out_fifo.eq(20)]
        if self.loopback:
            m.d.sync += [scan_bus.out_fifo.eq(5)] ## don't actually use the dwell times
            ## this way the pattern is returned faster for debugging
        else:
            m.d.sync += [scan_bus.out_fifo.eq(self.out_fifo.r_data)]
        # m.d.sync += [self.datain.eq(2)]

        with m.If(scan_bus.bus_state == BUS_WRITE_X):
            m.d.sync += [scan_bus.out_fifo.eq(6)]
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
            if self.loopback:
                    if self.mode == "image":
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
                        ]
            if self.mode == "pattern":
                ## in pattern mode, currently, the transmitted data will always loop back
                ## todo: a mode that returns live signal instead
                m.d.sync += [
                    # self.datain[0].eq(scan_bus.x_data[6]),
                    # self.datain[1].eq(scan_bus.x_data[7]),
                    # self.datain[2].eq(scan_bus.x_data[8]),
                    # self.datain[3].eq(scan_bus.x_data[9]),
                    # self.datain[4].eq(scan_bus.x_data[10]),
                    # self.datain[5].eq(scan_bus.x_data[11]),
                    # self.datain[6].eq(scan_bus.x_data[12]),
                    # self.datain[7].eq(scan_bus.x_data[13]),

                    # self.datain[0].eq(scan_bus.out_fifo[0]),
                    # self.datain[1].eq(scan_bus.out_fifo[1]),
                    # self.datain[2].eq(scan_bus.out_fifo[2]),
                    # self.datain[3].eq(scan_bus.out_fifo[3]),
                    # self.datain[4].eq(scan_bus.out_fifo[4]),
                    # self.datain[5].eq(scan_bus.out_fifo[5]),
                    # self.datain[6].eq(scan_bus.out_fifo[6]),
                    # self.datain[7].eq(scan_bus.out_fifo[7]),

                    self.datain[0].eq(self.out_fifo_f[0]),
                    self.datain[1].eq(self.out_fifo_f[1]),
                    self.datain[2].eq(self.out_fifo_f[2]),
                    self.datain[3].eq(self.out_fifo_f[3]),
                    self.datain[4].eq(self.out_fifo_f[4]),
                    self.datain[5].eq(self.out_fifo_f[5]),
                    self.datain[6].eq(self.out_fifo_f[6]),
                    self.datain[7].eq(self.out_fifo_f[7]),
                ]


                ## Fixed Value
                # self.datain[0].eq(1),
                # self.datain[1].eq(1),
                # self.datain[2].eq(1),
                # self.datain[3].eq(1),
                # self.datain[4].eq(1),
                # self.datain[5].eq(1),
                # self.datain[6].eq(1),
                # self.datain[7].eq(0),

            else:
                    m.d.sync += [
                    # Actual input
                    self.datain[0].eq(self.pads.g_t.i), 
                    self.datain[1].eq(self.pads.h_t.i),
                    self.datain[2].eq(self.pads.i_t.i),
                    self.datain[3].eq(self.pads.j_t.i),
                    self.datain[4].eq(self.pads.k_t.i),
                    self.datain[5].eq(self.pads.l_t.i),
                    self.datain[6].eq(self.pads.m_t.i),
                    self.datain[7].eq(self.pads.n_t.i),## MSB
                    ]

                ### Only reading 8 bits right now
                ### so just ignore the rest

            m.d.sync += [
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
        
            with m.If(scan_bus.bus_state == OUT_FIFO):
                if self.mode == "pattern":
                    #m.d.sync += [scan_bus.out_fifo.eq(self.dwell_time)]
                    m.d.comb += [self.out_fifo.r_en.eq(1)]
                    with m.If(self.out_fifo.r_rdy):
                        m.d.sync += [
                            #self.out_fifo_f.eq(5),
                            self.out_fifo_f.eq(self.out_fifo.r_data),
                            #scan_bus.out_fifo.eq(20),
                            #scan_bus.out_fifo.eq(self.out_fifo.r_data),
                            
                        ]
                if self.mode == "image":
                    m.d.sync += [scan_bus.out_fifo.eq(self.dwell_time)]



        
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
            "-m", "--mode", type=str, default="image",
            help="image or pattern  (default: %(default)s)")
        parser.add_argument(
            "-l", "--loopback", type=bool, default=False,
            help="loopback  (default: %(default)s)")
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
            dwell_time = args.dwell,
            mode = args.mode,
            loopback = args.loopback
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


        async def get_limited_output():
            ## get approx the number of packets you need 
            # to contain {captures} images
            ## and then some more

            for n in range((args.captures+1)*(round(dimension*dimension/2000)+1)): 
                if current.n < args.captures:
                    #print("Reading...")0                    raw_data = await iface.read()
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



        def imgout(raw_data):
            # print("-----------")
            # print("frame", current.n)
            data = raw_data.tolist()
            current.packet_to_txt_file(data)
            #current.packet_to_waveform(data)
            d = np.array(data)
            # print(d)
            # print(buf)
            zero_index = np.nonzero(d < 1)[0]
            # print("buffer length:", len(buf))
            # print("last pixel:",current.last_pixel)
            print("d length:", len(d))
            # print("d:",d)
            
            if len(zero_index) > 0: #if a zero was found
                # current.n += 1
                # print("zero index:",zero_index)
                zero_index = int(zero_index)

                buf[:d[zero_index+1:].size] = d[zero_index+1:]
                # print(buf[:d[zero_index+1:].size])
                # print(d[:zero_index+1].size)
                buf[dimension * dimension - zero_index:] = d[:zero_index]
                # print(buf[dimension * dimension - zero_index:])
                current.last_pixel = d[zero_index+1:].size
                

            else: 
                if len(buf[current.last_pixel:current.last_pixel+len(d)]) < len(d):
                    pass
                #     print("data too long to fit in end of frame, but no zero")
                #     print(d[:dimension])
                buf[current.last_pixel:current.last_pixel + d.size] = d
                # print(buf[current.last_pixel:current.last_pixel + d.size])
                current.last_pixel = current.last_pixel + d.size
            

        start_time = time.perf_counter()
        
        #while True:

        def bmp_to_bitstream(filename, boolean=False):
            pattern_img = Image.open(os.path.join(os.getcwd(), 'software/glasgow/applet/video/scan_gen/', filename))
            ## boolean images will have pixel values of True or False
            ## this will convert that to 1 or 0
            pattern_array = np.array(pattern_img).astype(np.uint8)
            
            height, width = pattern_array.shape

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

        
        
        if args.mode == "pattern":
            #filename = "Nanographs Pattern Test Logo and Gradients.bmp"
            filename = "tanishq 02.bmp"
            pattern_stream = bmp_to_bitstream(filename, boolean=True)
            



            #print(pattern_array)

        
        
        def patternin(pattern_slice):
            current.n += 1
            current.packet_to_txt_file(pattern_slice, "o")
            #current.packet_to_waveform(pattern_slice, "o")


        while True:
            for n in range(int(dimension*dimension/16384)): #packets per frame
                #time.sleep(.05)
                
                # print("writing")
                #await iface.write([n]*16384)
                if n == dimension*dimension/16384:
                    ## add a frame sync bit at the end of the pattern
                    pattern_slice = pattern_stream[n*16384:(n+1)*16384] + [0]
                else:
                    pattern_slice = pattern_stream[n*16384:(n+1)*16384]
                #pattern_slice = ([3]*256 + [254]*256)*32
                await iface.write(pattern_slice)
                threading.Thread(target=patternin(pattern_slice)).start()
                #await iface.flush()
                # print("done")
                #print("reading", current.n)
                raw_data = await iface.read(16384)
                # print("start thread")
                threading.Thread(target=imgout(raw_data)).start()
            print("pattern complete", current.n)




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