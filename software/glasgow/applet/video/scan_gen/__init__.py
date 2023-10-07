import os
import logging
import asyncio
from amaranth import *
from amaranth.build import *
from ....support.endpoint import *
from amaranth.sim import Simulator
import numpy as np
import time
import threading
# import itertools
from rich import print
from asyncio.exceptions import TimeoutError



from .scan_gen_components.bus_state_machine import ScanIOBus, ScanIOBus_Point
#from .scan_gen_components import pg_gui 
from .output_formats import ScanDataRun, CommandLine
from .input_formats import bmp_to_bitstream



from ... import *

BUS_WRITE_X = 0x01
BUS_WRITE_Y = 0x02
BUS_READ = 0x03
BUS_FIFO_1 = 0x04
BUS_FIFO_2 = 0x05
FIFO_WAIT = 0x06
A_RELEASE = 0x07
OUT_FIFO = 0x08

IMAGE = 0
PATTERN = 1
POINT = 2

######################
###### DATA BUS ######
######################



class DataBusAndFIFOSubtarget(Elaboratable):
    def __init__(self, data, power_ok, in_fifo, out_fifo, resolution_bits, 
    dwell_time, mode, loopback, resolution, dwell, reset, enable):
        self.data = data
        self.power_ok = power_ok
        #print(vars(self.pads))
        self.in_fifo  = in_fifo

        self.out_fifo = out_fifo
        self.mode = mode #image or pattern
        self.loopback = loopback #True if in loopback 

        self.resolution_bits = resolution_bits ## cli arg. 9x9 = 512, etc.
        self.resolution = resolution #register

        self.dwell_time = dwell_time #cli arg
        self.dwell = dwell #register

        self.reset = reset
        self.enable = enable

        self.datain = Signal(14)

        self.running_average_two = Signal(14)

        self.out_fifo_f = Signal(8)

    def elaborate(self, platform):
        m = Module()

        # with m.If(self.mode.eq(POINT)):
        #     m.submodules.scan_bus = scan_bus = ScanIOBus_Point(255, 100, 4)
        # with m.Else():
            #m.submodules.scan_bus = scan_bus = ScanIOBus(self.resolution_bits, self.dwell_time, self.mode)
        m.submodules.scan_bus = scan_bus = ScanIOBus(self.resolution, 3, 
                                                        self.mode, self.reset, self.enable)

        x_latch = platform.request("X_LATCH")
        x_enable = platform.request("X_ENABLE")
        y_latch = platform.request("Y_LATCH")
        y_enable = platform.request("Y_ENABLE")
        a_latch = platform.request("A_LATCH")
        a_enable = platform.request("A_ENABLE")

        a_clock = platform.request("A_CLOCK")
        d_clock = platform.request("D_CLOCK")


        m.d.comb += [
            x_latch.o.eq(scan_bus.x_latch),
            x_enable.o.eq(scan_bus.x_enable),
            y_latch.o.eq(scan_bus.y_latch),
            y_enable.o.eq(scan_bus.y_enable),
            a_latch.o.eq(scan_bus.a_latch),
            a_enable.o.eq(scan_bus.a_enable),
            a_clock.o.eq(scan_bus.a_clock),
            d_clock.o.eq(scan_bus.d_clock),
            #scan_bus.fifo_ready.eq(0)
            scan_bus.in_fifo_ready.eq(self.in_fifo.w_rdy),
            scan_bus.out_fifo_ready.eq(self.out_fifo.r_rdy),
        ]

        
        # if self.mode == "pattern":
        with m.If(self.mode == PATTERN):
            # if self.loopback:
            with m.If(self.loopback):
                m.d.sync += [scan_bus.out_fifo.eq(5)] ## don't actually use the dwell times
                ## this way the pattern is returned faster for debugging
            #else:
            with m.Else():
                m.d.sync += [scan_bus.out_fifo.eq(self.out_fifo.r_data)]
            # m.d.sync += [self.datain.eq(2)]
        # if self.mode == "image":
        with m.If(self.mode == IMAGE):
            #m.d.sync += [scan_bus.out_fifo.eq(self.dwell_time)]
            m.d.sync += [scan_bus.out_fifo.eq(self.dwell)]

        with m.If(scan_bus.bus_state == BUS_WRITE_X):
            ## 0: LSB ----> 13: MSB
            for i, pad in enumerate(self.data):
                m.d.comb += [
                    pad.oe.eq(self.power_ok.i),
                    pad.o.eq(scan_bus.x_data[i]),
                ]

            
        
        with m.If(scan_bus.bus_state == BUS_WRITE_Y):
            ## 0: LSB ----> 13: MSB
            for i, pad in enumerate(self.data):
                m.d.comb += [
                    pad.oe.eq(self.power_ok.i),
                    pad.o.eq(scan_bus.y_data[i]),
                ]

        
        with m.If(scan_bus.bus_state == BUS_READ):
            for i in range(8):
                with m.If(self.mode == IMAGE):
                # if self.mode == "image":
                        # if self.loopback:
                        with m.If(self.loopback):
                            ## LOOPBACK
                            m.d.sync += self.datain[i].eq(scan_bus.y_data[i+6])

                            # ## Fixed Value
                            # m.d.sync += self.datain[i].eq(1)
                        
                        with m.Else():
                        # else:
                            # Actual input
                            # MSB = data[13] = datain[7]
                            m.d.sync += self.datain[i].eq(self.data[i+6].i)
    
                with m.If(self.mode == PATTERN):
                # if self.mode == "pattern":
                    with m.If(self.loopback):
                    # if self.loopback:
                        m.d.sync += [
                            self.datain[i].eq(self.out_fifo_f[i])
                            # self.datain[i].eq(scan_bus.y_data[i+6])
                        ]
                    # else:
                    with m.Else():
                        m.d.sync += [
                            self.datain[i].eq(self.data[i+6].i)
                            ]


                
            ### Only reading 8 bits right now
            ### so just ignore the rest
            for i in range(8,14):
                m.d.sync += self.datain[i].eq(0)

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
                            self.in_fifo.w_data.eq(2),
                            self.in_fifo.w_en.eq(1),
                        ]
                    with m.Else():
                        m.d.comb += [
                            self.in_fifo.w_data.eq(self.running_average_two[0:8]),
                            self.in_fifo.w_en.eq(1),
                        ]

            with m.If(scan_bus.bus_state == BUS_FIFO_2):
                with m.If(self.in_fifo.w_rdy):
                    with m.If(scan_bus.line_sync & scan_bus.frame_sync):
                        m.d.comb += [
                            self.in_fifo.w_data.eq(0),
                            self.in_fifo.w_en.eq(1),
                        ]
        
            with m.If(scan_bus.bus_state == OUT_FIFO):
                with m.If(self.mode == PATTERN):
                # if self.mode == "pattern" or self.mode == "pattern_out":
                    #m.d.sync += [scan_bus.out_fifo.eq(self.dwell_time)]
                    m.d.comb += [self.out_fifo.r_en.eq(1)]
                    with m.If(self.out_fifo.r_rdy):
                        m.d.sync += [
                            #self.out_fifo_f.eq(5),
                            self.out_fifo_f.eq(self.out_fifo.r_data),
                            #scan_bus.out_fifo.eq(20),
                            #scan_bus.out_fifo.eq(self.out_fifo.r_data),
                            
                        ]
                

        return m

class PointDataBusAndFIFOSubtarget(Elaboratable):
    def __init__(self, data, power_ok, in_fifo, out_fifo, resolution_bits, 
    dwell_time, mode, loopback, dwell, x_position, y_position):
        self.data = data
        self.power_ok = power_ok
        #print(vars(self.pads))
        self.in_fifo  = in_fifo

        self.out_fifo = out_fifo
        self.mode = mode #image or pattern
        self.loopback = loopback #True if in loopback 

        self.resolution_bits = resolution_bits ## cli arg. 9x9 = 512, etc.

        self.dwell_time = dwell_time #cli arg
        self.dwell = dwell #register

        self.x_position = x_position
        self.y_position = y_position

        self.datain = Signal(14)

        self.running_average_two = Signal(14)

        self.out_fifo_f = Signal(8)

    def elaborate(self, platform):
        m = Module()

        m.submodules.scan_bus = scan_bus = ScanIOBus_Point(self.x_position, self.y_position, self.dwell)


        x_latch = platform.request("X_LATCH")
        x_enable = platform.request("X_ENABLE")
        y_latch = platform.request("Y_LATCH")
        y_enable = platform.request("Y_ENABLE")
        a_latch = platform.request("A_LATCH")
        a_enable = platform.request("A_ENABLE")

        a_clock = platform.request("A_CLOCK")
        d_clock = platform.request("D_CLOCK")


        m.d.comb += [
            x_latch.o.eq(scan_bus.x_latch),
            x_enable.o.eq(scan_bus.x_enable),
            y_latch.o.eq(scan_bus.y_latch),
            y_enable.o.eq(scan_bus.y_enable),
            a_latch.o.eq(scan_bus.a_latch),
            a_enable.o.eq(scan_bus.a_enable),
            a_clock.o.eq(scan_bus.a_clock),
            d_clock.o.eq(scan_bus.d_clock),
            #scan_bus.fifo_ready.eq(0)
            scan_bus.in_fifo_ready.eq(self.in_fifo.w_rdy),
            scan_bus.out_fifo_ready.eq(self.out_fifo.r_rdy),
        ]

        with m.If(scan_bus.bus_state == BUS_WRITE_X):
            ## 0: LSB ----> 13: MSB
            for i, pad in enumerate(self.data):
                m.d.comb += [
                    pad.oe.eq(self.power_ok.i),
                    pad.o.eq(scan_bus.x_data[i]),
                ]
        
        with m.If(scan_bus.bus_state == BUS_WRITE_Y):
            ## 0: LSB ----> 13: MSB
            for i, pad in enumerate(self.data):
                m.d.comb += [
                    pad.oe.eq(self.power_ok.i),
                    pad.o.eq(scan_bus.y_data[i]),
                ]

        
        with m.If(scan_bus.bus_state == BUS_READ):

                
            ### Only reading 8 bits right now
            ### so just ignore the rest
            for i in range(8,14):
                m.d.sync += self.datain[i].eq(0)

        with m.If(scan_bus.bus_state == A_RELEASE):
            m.d.sync += [
                    self.running_average_two.eq(self.datain),
                ]

        with m.If(scan_bus.dwell_ctr_ovf):
            with m.If(scan_bus.bus_state == BUS_FIFO_1):
                with m.If(self.in_fifo.w_rdy):
                    with m.If(self.running_average_two <= 1): #restrict image data to 2-255, save 0-1 for frame/line sync
                        m.d.comb += [
                            self.in_fifo.w_data.eq(3),
                            self.in_fifo.w_en.eq(1),
                        ]
                    with m.Else():
                        m.d.comb += [
                            self.in_fifo.w_data.eq(self.running_average_two[0:8]),
                            self.in_fifo.w_en.eq(1),
                        ]

                

        return m


class ScanGenApplet(GlasgowApplet):
    logger = logging.getLogger(__name__)
    help = "boilerplate applet"
    preview = True
    description = """
    /|/|/|/|/|/|/|/|
    /|/|/|/|/|/|/|/|
    /|/|/|/|/|/|/|/|
    /|/|/|/|/|/|/|/|
    """


    @classmethod
    def add_build_arguments(cls, parser, access):
        super().add_build_arguments(parser, access)
        access.add_pin_set_argument(parser, "data", width=14, default=range(0,14))
        access.add_pin_argument(parser, "power_ok", default=15)
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


    def build(self, target, args):
        ### LVDS Header (Not used as LVDS)
        LVDS = [
            Resource("X_ENABLE", 0, Pins("B1", dir="o"), Attrs(IO_STANDARD="SB_LVCMOS33")),
            Resource("X_LATCH", 0, Pins("C4", dir="o"), Attrs(IO_STANDARD="SB_LVCMOS33")),
            Resource("Y_ENABLE", 0, Pins("C2", dir="o"), Attrs(IO_STANDARD="SB_LVCMOS33")),
            Resource("Y_LATCH", 0, Pins("E1", dir="o"), Attrs(IO_STANDARD="SB_LVCMOS33")),
            Resource("A_ENABLE", 0, Pins("D2", dir="o"), Attrs(IO_STANDARD="SB_LVCMOS33")),
            Resource("A_LATCH", 0, Pins("E2", dir="o"), Attrs(IO_STANDARD="SB_LVCMOS33")),
            Resource("D_CLOCK", 0, Pins("F1", dir="o"), Attrs(IO_STANDARD="SB_LVCMOS33")),
            Resource("A_CLOCK", 0, Pins("F4", dir="o"), Attrs(IO_STANDARD="SB_LVCMOS33")),]

        target.platform.add_resources(LVDS)
        dwell, self.dwell = target.registers.add_rw(8, reset = 1)


        self.mux_interface = iface = target.multiplexer.claim_interface(self, args)

        if args.mode == "point":
            x_position, self.x_position = target.registers.add_rw(8)
            print("x position:", self.x_position)
            y_position, self.y_position = target.registers.add_rw(8)
            print("y position:", self.y_position)
            iface.add_subtarget(PointDataBusAndFIFOSubtarget(
                data=[iface.get_pin(pin) for pin in args.pin_set_data],
                power_ok=iface.get_pin(args.pin_power_ok),
                in_fifo = iface.get_in_fifo(),
                out_fifo = iface.get_out_fifo(),
                resolution_bits = args.res,
                dwell_time = args.dwell,
                mode = args.mode,
                loopback = args.loopback,
                dwell = dwell,
                x_position = x_position,
                y_position = y_position
            ))
        else:
            resolution, self.resolution = target.registers.add_rw(4, reset = 9)
            reset, self.reset = target.registers.add_rw()
            print("reset:", self.reset)
            enable, self.enable = target.registers.add_rw(reset=0)
            print("enable:", self.enable)
            mode, self.mode = target.registers.add_rw(3,reset=0)
            print("mode:", self.mode)
            loopback, self.loopback = target.registers.add_rw(reset=0)
            print("loopback:", self.loopback)

            iface.add_subtarget(DataBusAndFIFOSubtarget(
                data=[iface.get_pin(pin) for pin in args.pin_set_data],
                power_ok=iface.get_pin(args.pin_power_ok),
                in_fifo = iface.get_in_fifo(),
                out_fifo = iface.get_out_fifo(),
                resolution_bits = args.res,
                dwell_time = args.dwell,
                # mode = args.mode,
                mode = mode,
                loopback = loopback,
                # loopback = args.loopback,
                resolution = resolution,
                dwell = dwell,
                reset = reset,
                enable = enable
            ))

            
    
    @classmethod
    def add_run_arguments(cls, parser, access):
        super().add_run_arguments(parser, access)

    async def run(self, device, args):
        iface = await device.demultiplexer.claim_interface(self, self.mux_interface, args)
        if args.mode != "point":
            await device.write_register(self.enable, 0)
            await device.write_register(self.reset, 1) # force reset
            await device.write_register(self.resolution, args.res)
            await device.write_register(self.loopback, 0)
            self.looping = False
            await device.write_register(self.mode, 0)
            self.mode_is = IMAGE
        else:
            await device.write_register(self.dwell, args.dwell)

        return iface



    @classmethod
    def add_interact_arguments(cls, parser):
        ServerEndpoint.add_argument(parser, "endpoint")

    async def interact(self, device, args, iface):
        resolution_bits = args.res
        dimension = pow(2,resolution_bits)
        
        current = ScanDataRun(dimension)
        cli = CommandLine() 

        def display_data(data): ## use to create a basic live display in terminal
            if len(data) > 0:
                first = data[0] ## just read the first byte of every packet
                display = "#"*round(first/5) ## scale it to fit in one line in the terminal
                print(display)

        
        # # if args.mode == "pattern" or args.mode == "pattern_out":
        # #pattern_stream = bmp_to_bitstream("monalisa.bmp", dimension, invert_color=True)
        # pattern_stream = bmp_to_bitstream("Nanographs Pattern Test Logo and Gradients.bmp", dimension, invert_color=False)
        # #pattern_stream = bmp_to_bitstream("tanishq 02.bmp", dimension)
        # #pattern_stream = bmp_to_bitstream("green.bmp", invert_color=True)
        # #pattern_stream = bmp_to_bitstream("isabelle.bmp", dimension, invert_color=True)
        
        # print(len(pattern_stream))

        # # https://stackoverflow.com/questions/12944882/how-can-i-infinitely-loop-an-iterator-in-python-via-a-generator-or-other
        # def pattern_loop():
        #     while 1:
        #         for n in range(int(dimension*dimension/16384)): #packets per frame
        #             print(n)
        #             yield pattern_stream[n*16384:(n+1)*16384]
        #         print("pattern complete")
        # pattern = pattern_loop()

        buffer_size = 16384
        endpoint = await ServerEndpoint("socket", self.logger, args.endpoint, queue_size=buffer_size)

        txt_file = open("frames.txt", "w")

        async def scan_continously():
            print("scan continous")
            while True: 
                data = await single_bidirectional_transfer_remote()
                await endpoint.send(data)
                print("sent", (data.tolist())[0], ":", (data.tolist())[-1], "-", len(data.tolist()))

        async def single_bidirectional_transfer():
            if args.mode == "pattern":
                txt_file.write("\nSENT:\n")
                pattern_slice = next(pattern)
                txt_file.write(", ".join([str(x) for x in pattern_slice]))
                await iface.write(pattern_slice)
            await device.write_register(self.enable, 1)
            data = await iface.read(16384)
            await device.write_register(self.enable, 0)
            txt_file.write("\nRCVD:\n")
            txt_file.write(", ".join([str(x) for x in data.tolist()]))
            return data

        # await single_bidirectional_transfer()

        async def single_bidirectional_transfer_remote():
            print("SBDTR")
            #if args.mode == "pattern":
            if self.mode_is == PATTERN:
                txt_file.write("\nSENT:\n")
                print("awaiting endpt read")
                pattern_slice = await endpoint.recv(16384)
                txt_file.write(", ".join([str(x) for x in pattern_slice]))
                print("rcvd", pattern_slice[0], ":", pattern_slice[-1], "-", len(pattern_slice))
                print("writing")
                await iface.write(pattern_slice)
                print("wrote")
            await device.write_register(self.enable, 1)
            print("awaiting iface read")
            data = await iface.read(16384)
            print("read")
            await device.write_register(self.enable, 0)
            txt_file.write("\nRCVD:\n")
            txt_file.write(", ".join([str(x) for x in data.tolist()]))
            return data

        async def read_and_ignore():
            data = await iface.read()
            if data is not None:
                if len(data) == 0:
                    print("empty packet")
                else:
                    print("discarded", (data.tolist())[0], ":", (data.tolist())[-1])

        async def read_until_empty():
            while True:
                ## clear all the in-transit packets out of the buffer
                try:
                    await asyncio.wait_for(read_and_ignore(), timeout=1)
                except TimeoutError:
                    print('read timeout')
                    break



        await read_until_empty() 
        ## sometimes on startup there's still packets in the buffer?
        ## idk why, but this is to deal with that
        state = "init"

        ispatterning = False

        while True:
                try: 
                    ## get 4 bytes
                    if not ispatterning:
                        cmd = await asyncio.shield(endpoint.recv(4))
                        cmd = cmd.decode(encoding='utf-8', errors='strict')
                        print("cmd:", cmd)
                        if cmd == "scan":
                            if (state == "new_scan") or (state == "init"):
                                print("un-resetting")
                                await device.write_register(self.reset, 0)
                            print("starting scan...")
                            scan = asyncio.ensure_future(scan_continously()) ## start async task
                            print(scan)
                            if self.mode_is == PATTERN:
                                ispatterning = True
                                print("ispatterning")
                            try:
                                await scan
                            except asyncio.CancelledError:
                                print("Scan cancelled") ## make sure its canceled?
                                pass
                        else: ## if any other command is recieved, pause the scan
                            await device.write_register(self.enable, 0)
                            print("else state", state)
                            if cmd == "stop": ## sent when pause button is clicked
                                state = "paused"
                                if scan is None:
                                    print("No scan exists to be stopped")
                                    pass
                                scan.cancel()
                                try:
                                    await scan
                                except asyncio.CancelledError:
                                    print("Scan cancelled") ## make sure its canceled?
                                    pass
                            ## this will leave some packets in the buffer
                            ## which is fine if you want to resume the scan with the same resolution etc.
                            ## but if you want a new scan, then:
                            else:
                                ## any command will trigger this behavior
                                ## the new scan button sends "eeee"
                                if (state == "paused") or (state == "init"): ## transitioning between pausing the scan, and recieving commands
                                    await read_until_empty()
                                    await device.write_register(self.reset, 1)
                                    state = "new_scan"
                                ## if a resolution or dwell time command was sent
                                ## then write a new value to a register
                                if cmd.startswith("re"): ## Changing resolution
                                    new_bits = int(cmd.strip("re")) 
                                    await device.write_register(self.resolution, new_bits)
                                    print("resolution:",new_bits)
                                elif cmd.startswith("d"): ## Changing dwell time
                                    new_dwell = int(cmd.strip("d"))
                                    await device.write_register(self.dwell, new_dwell)
                                    print("dwell time", new_dwell)
                                elif cmd.startswith("m"): ## Changing mode
                                    if self.mode_is == IMAGE:
                                        await device.write_register(self.mode, 1)
                                        print("switched to pattern mode")
                                        self.mode_is = PATTERN
                                        args.mode = "pattern"
                                    else:
                                        await device.write_register(self.mode, 0)
                                        print("switched to image mode")
                                        self.mode_is = IMAGE
                                        args.mode = "image"
                                elif cmd.startswith("l"): ## Changing loopback state
                                    if self.looping:
                                        await device.write_register(self.loopback, 0)
                                        print("loopback off")
                                        self.looping = False
                                    else:
                                        await device.write_register(self.loopback, 1)
                                        print("loopback on")
                                        self.looping = True
                                

                # except (ConnectionResetError, AttributeError, BrokenPipeError) as error:
                #     # basically, if the other port closes, don't stop running
                #     print("Connection lost, trying again...")
                #     pass
                finally:
                    print("finally")






# -------------------------------------------------------------------------------------------------

class ScanGenAppletTestCase(GlasgowAppletTestCase, applet=ScanGenApplet):
    @synthesis_test
    def test_build(self):
        self.assertBuilds()