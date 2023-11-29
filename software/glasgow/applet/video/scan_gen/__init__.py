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
from amaranth.lib import data, enum
from amaranth.lib.fifo import SyncFIFO


from ... import *

## dealing with relative imports
if "glasgow" in __name__: ## running as applet
    from ..scan_gen.scan_gen_components.main_iobus import IOBus
    from ..scan_gen.scan_gen_components.addresses import *
    from ..scan_gen.scan_gen_components.test_streams import *


class IOBusSubtarget(Elaboratable):
    def __init__(self, data, power_ok, in_fifo, out_fifo):
        self.data = data
        self.power_ok = power_ok
        self.in_fifo = in_fifo
        self.out_fifo = out_fifo

        self.io_bus = IOBus(is_simulation = False,
        out_fifo = self.out_fifo, in_fifo = self.in_fifo)

        self.pins = Signal(14)

    def elaborate(self, platform):
        m = Module()

        m.submodules["IOBus"] = self.io_bus

        x_latch = platform.request("X_LATCH")
        x_enable = platform.request("X_ENABLE")
        y_latch = platform.request("Y_LATCH")
        y_enable = platform.request("Y_ENABLE")
        a_latch = platform.request("A_LATCH")
        a_enable = platform.request("A_ENABLE")

        a_clock = platform.request("A_CLOCK")
        d_clock = platform.request("D_CLOCK")

        m.d.comb += x_latch.o.eq(self.io_bus.x_latch)
        m.d.comb += x_enable.o.eq(self.io_bus.x_enable)
        m.d.comb += y_latch.o.eq(self.io_bus.y_latch)
        m.d.comb += y_enable.o.eq(self.io_bus.y_enable)
        m.d.comb += a_latch.o.eq(self.io_bus.a_latch)
        m.d.comb += a_enable.o.eq(self.io_bus.a_enable)

        m.d.comb += a_clock.o.eq(~self.io_bus.a_clock)
        m.d.comb += d_clock.o.eq(self.io_bus.d_clock)
        
        with m.If(self.io_bus.bus_multiplexer.is_x):
            for i, pad in enumerate(self.data):
                m.d.comb += [
                    pad.oe.eq(self.power_ok.i),
                    pad.o.eq(self.io_bus.pins[i]),
                ]
            #m.d.comb += self.pins.eq(self.io_bus.pins)
        with m.If(self.io_bus.bus_multiplexer.is_y):
            for i, pad in enumerate(self.data):
                m.d.comb += [
                    pad.oe.eq(self.power_ok.i),
                    pad.o.eq(self.io_bus.pins[i]),
                ]
            #m.d.comb += self.pins.eq(self.io_bus.pins)
        with m.If(self.io_bus.bus_multiplexer.is_a):
            for i, pad in enumerate(self.data):
                m.d.comb += [
                    self.io_bus.pins[i].eq(pad.i)
                ]
            #m.d.comb += self.io_bus.pins.eq(self.pins)

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

        self.mux_interface = iface = target.multiplexer.claim_interface(self, args)

        iface.add_subtarget(IOBusSubtarget(
            data=[iface.get_pin(pin) for pin in args.pin_set_data],
            power_ok=iface.get_pin(args.pin_power_ok),
            in_fifo = iface.get_in_fifo(),
            out_fifo = iface.get_out_fifo(),
        ))

    @classmethod
    def add_run_arguments(cls, parser, access):
        super().add_run_arguments(parser, access)

    async def run(self, device, args):
        iface = await device.demultiplexer.claim_interface(self, self.mux_interface, args)
        text_file = open("packets.txt","w")
        n = 0
        print(Constant_Raster_Address.X.value)
        print(Constant_Raster_Address.Y.value)
        print(Constant_Raster_Address.D.value)

        while n < 16384:
            n += 1
            await iface.write([Constant_Raster_Address.X.value])
            n += 1
            await iface.write([200])
            n += 1
            await iface.write([55])
            n += 1
            await iface.write([Constant_Raster_Address.Y.value])
            n += 1
            await iface.write([55])
            n += 1
            await iface.write([200])
            n += 1
            await iface.write([Constant_Raster_Address.D.value])
            n += 1
            await iface.write([3])
            n += 1
            await iface.write([3])

        output = await iface.read(16384)
        text_file.write(str(output.tolist()))

        # for n in range(10):
        #     for n in range(10):
        #         for n in basic_vector_stream:
        #             address, data = n
        #             address_b = bytes('{0:08b}'.format(address.value),encoding="utf8")
        #             data_bits = '{0:016b}'.format(address.value)
        #             data_1 = bytes(data_bits[0:8],encoding="utf8")
        #             data_2 = bytes(data_bits[8:16],encoding="utf8")
        #             print("writing", address_b, data_1, data_2)
        #             await iface.write(bytes(address_b))
        #             await iface.write(bytes(data_1))
        #             await iface.write(bytes(data_2))
        #         for n in basic_vector_stream:
        #             address, data = n
        #             address_b = bytes('{0:08b}'.format(address.value),encoding="utf8")
        #             data_bits = '{0:016b}'.format(address.value)
        #             data_1 = bytes(data_bits[0:8],encoding="utf8")
        #             data_2 = bytes(data_bits[8:16],encoding="utf8")
        #             print("writing", address_b[::-1], data_1, data_2)
        #             await iface.write(bytes(address_b[::-1]))
        #             await iface.write(bytes(data_1))
        #             await iface.write(bytes(data_2))
        #             #`
        #     iface.flush()
        #     print("reading")
        #     try:
        #         output = await asyncio.wait_for(iface.read(16384), timeout=5)
        #         print("got data")
                
        #         data = output.tolist()
        #         text_file.write(str(data))
        #     except TimeoutError:
        #         print('timeout')  

        

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