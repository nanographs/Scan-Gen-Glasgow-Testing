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
        m.submodules.scan_bus = scan_bus = ScanIOBus(self.resolution, self.dwell, 
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

            

                    






# -------------------------------------------------------------------------------------------------

class ScanGenAppletTestCase(GlasgowAppletTestCase, applet=ScanGenApplet):
    @synthesis_test
    def test_build(self):
        self.assertBuilds()