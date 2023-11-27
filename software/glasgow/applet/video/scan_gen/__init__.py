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


class IOBusSubtarget(Elaboratable):
    def __init__(self, data, power_ok, in_fifo, out_fifo):
        self.data = data
        self.power_ok = power_ok
        self.in_fifo = in_fifo
        self.out_fifo = out_fifo

        self.io_bus = IOBus(is_simulation = False,
        out_fifo = self.out_fifo, in_fifo = self.in_fifo)

    def elaborate(self, platform):
        m = Module()

        x_latch = platform.request("X_LATCH")
        x_enable = platform.request("X_ENABLE")
        y_latch = platform.request("Y_LATCH")
        y_enable = platform.request("Y_ENABLE")
        a_latch = platform.request("A_LATCH")
        a_enable = platform.request("A_ENABLE")

        a_clock = platform.request("A_CLOCK")
        d_clock = platform.request("D_CLOCK")

        m.d.comb += x_latch.o.eq(self.io_bus.bus_multiplexer.x_dac.latch.le)
        m.d.comb += x_enable.o.eq(self.io_bus.bus_multiplexer.x_dac.latch.oe)
        m.d.comb += y_latch.o.eq(self.io_bus.bus_multiplexer.y_dac.latch.le)
        m.d.comb += y_enable.o.eq(self.io_bus.bus_multiplexer.y_dac.latch.oe)
        m.d.comb += a_latch.o.eq(self.io_bus.bus_multiplexer.a_adc.latch.le)
        m.d.comb += a_enable.o.eq(self.io_bus.bus_multiplexer.a_adc.latch.oe)

        m.d.comb += a_clock.o.eq(~self.io_bus.bus_multiplexer.sample_clock)
        m.d.comb += d_clock.o.eq(self.io_bus.bus_multiplexer.sample_clock)
        
        with m.If(self.io_bus.bus_multiplexer.is_x):
            for i, pad in enumerate(self.data):
                m.d.comb += [
                    pad.oe.eq(self.power_ok.i),
                    pad.o.eq(self.pins[i]),
                ]
            m.d.comb += self.pins.eq(self.io_bus.pins)
        with m.If(self.io_bus.bus_multiplexer.is_y):
            for i, pad in enumerate(self.data):
                m.d.comb += [
                    pad.oe.eq(self.power_ok.i),
                    pad.o.eq(self.pins[i]),
                ]
            m.d.comb += self.pins.eq(self.io_bus.pins)
        with m.If(self.bus_multiplexer.is_a):
            for i, pad in enumerate(self.data):
                m.d.comb += [
                    self.pins[i].eq(pad.i)
                ]
            m.d.comb += self.io_bus.pins.eq(self.pins)

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

        iface.add_subtarget(IOBus(
            data=[iface.get_pin(pin) for pin in args.pin_set_data],
            power_ok=iface.get_pin(args.pin_power_ok),
            in_fifo = iface.get_in_fifo(),
            out_fifo = iface.get_out_fifo(),
        ))

    @classmethod
    def add_run_arguments(cls, parser, access):
        super().add_run_arguments(parser, access)

    async def run(self, device, args):
        return await device.demultiplexer.claim_interface(self, self.mux_interface, args)

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