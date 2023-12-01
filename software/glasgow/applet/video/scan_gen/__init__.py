import os
import types
import logging
import asyncio
from amaranth import *
from amaranth.build import *
from ....support.endpoint import *
from ....support.bits import *
from amaranth.sim import Simulator

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
    def __init__(self, data, power_ok, in_fifo, out_fifo, scan_mode):
        self.data = data
        self.power_ok = power_ok
        self.in_fifo = in_fifo
        self.out_fifo = out_fifo
        self.scan_mode = scan_mode

        self.io_bus = IOBus(self.out_fifo, self.in_fifo, scan_mode, is_simulation = False)

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

class ScanGenInterface:
    def __init__(self, iface, logger, device, __addr_scan_mode,
                is_simulation = False):
        self.iface = iface
        self._logger = logger
        self._level  = logging.DEBUG if self._logger.name == __name__ else logging.TRACE
        self._device = device
        self.__addr_scan_mode = __addr_scan_mode


        self.text_file = open("packets.txt","w")
        self.is_simulation = is_simulation

    def fifostats(self):
        iface = self.iface
        iface.statistics()
        print(len(iface._in_tasks._live))
        print(len(iface._out_tasks._live))
        print(iface._in_buffer._rtotal)
        print(iface._in_buffer._wtotal)
        print(iface._out_buffer._rtotal)
        print(iface._out_buffer._wtotal)
        print(iface._in_pushback)
        #print(iface._out_pushback)

    @types.coroutine
    def sim_write_2bytes(self, val):
        b1, b2 = get_two_bytes(val)
        print("writing", b1, b2)
        yield from self.iface.write(bits(b1))
        yield from self.iface.write(bits(b2))
        
    async def write_2bytes(self, val):
        b1, b2 = get_two_bytes(val)
        print("writing", b1, b2)
        await self.iface.write(bits(b1))
        await self.iface.write(bits(b2))

    @types.coroutine
    def sim_write_vpoint(self, point):
        x, y, d = point
        yield from self.sim_write_2bytes(x)
        yield from self.sim_write_2bytes(y)
        yield from self.sim_write_2bytes(d)

    async def write_vpoint(self, point):
        x, y, d = point
        await self.write_2bytes(x)
        await self.write_2bytes(y)
        await self.write_2bytes(d)

    async def read_r_packet(self):
        output = await self.iface.read(16384)
        return read_rdwell_packet(output)

    async def try_read_vpoint(self, n_points):
        try:
            output = await asyncio.wait_for(self.iface.read(6*n_points), timeout = 1)
            print("got data")
            return self.decode_vpoint_packet(output)
        except TimeoutError:
            return "timeout"
    
    def decode_vpoint(self, n):
        x1, x2, y1, y2, a1, a2 = n
        x = int("{0:08b}".format(x1) + "{0:08b}".format(x2),2)
        y = int("{0:08b}".format(y1) + "{0:08b}".format(y2),2)
        a = int("{0:08b}".format(a1) + "{0:08b}".format(a2),2)
        return [x, y, a]

    def decode_rdwell(self, n):
        a2, a1 = n
        a = int("{0:08b}".format(a1) + "{0:08b}".format(a2),2)
        return a
    
    def decode_rdwell_packet(self, raw_data):
        print(type(raw_data))
        if isinstance(raw_data, bytes):
            data = list(raw_data)
        else:
            data = raw_data.tolist()
        packet = []
        for n in range(0,len(data),2):
            dwell = self.decode_rdwell(data[n:n+2])
            packet.append(dwell)
        return packet

    def decode_vpoint_packet(self, raw_data):
        print(type(raw_data))
        if isinstance(raw_data, bytes):
            data = list(raw_data)
        else:
            data = raw_data.tolist()
        packet = []
        for n in range(0,len(data),6):
            point = self.decode_vpoint(data[n:n+6])
            packet.append(point)
        return packet



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
        scan_mode,  self.__addr_scan_mode  = target.registers.add_rw(2)

        iface.add_subtarget(IOBusSubtarget(
            data=[iface.get_pin(pin) for pin in args.pin_set_data],
            power_ok=iface.get_pin(args.pin_power_ok),
            in_fifo = iface.get_in_fifo(),
            out_fifo = iface.get_out_fifo(),
            scan_mode = scan_mode
        ))

    @classmethod
    def add_run_arguments(cls, parser, access):
        super().add_run_arguments(parser, access)

    async def run(self, device, args):
        iface = await device.demultiplexer.claim_interface(self, self.mux_interface, args)
        scan_iface = ScanGenInterface(iface, self.logger, device, self.__addr_scan_mode)
        return scan_iface
        

    @classmethod
    def add_interact_arguments(cls, parser):
        pass

    async def interact(self, device, args, scan_iface):
        test_vector_points = [
            [2000, 1000, 30], ## X, Y, D
            [1000, 2000, 40],
            [3000, 2500, 50],
            ]

        for n in range(10):
            for n in test_vector_points:
                await scan_iface.write_vpoint(n)
            
            output = await scan_iface.try_read_vpoint(3)
            print(output)

            

                



# -------------------------------------------------------------------------------------------------

class ScanGenAppletTestCase(GlasgowAppletTestCase, applet=ScanGenApplet):
    @synthesis_test
    def test_build(self):
        self.assertBuilds()