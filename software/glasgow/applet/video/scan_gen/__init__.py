import os
import types
import logging
import asyncio
import numpy as np

from amaranth import *
from amaranth.build import *
from ....support.endpoint import *
from ....support.bits import *
from amaranth.sim import Simulator

from asyncio.exceptions import TimeoutError
from amaranth.lib import data, enum
from amaranth.lib.fifo import SyncFIFO

from ..scan_gen.output_formats.even_newer_gui import run_gui


from ... import *

## dealing with relative imports
if "glasgow" in __name__: ## running as applet
    from ..scan_gen.scan_gen_components.main_iobus import IOBus
    from ..scan_gen.scan_gen_components.addresses import *
    from ..scan_gen.scan_gen_components.test_streams import *


class IOBusSubtarget(Elaboratable):
    def __init__(self, data, power_ok, in_fifo, out_fifo, scan_mode,
                x_full_resolution_b1, x_full_resolution_b2, 
                y_full_resolution_b1, y_full_resolution_b2 ):
        self.data = data
        self.power_ok = power_ok
        self.in_fifo = in_fifo
        self.out_fifo = out_fifo
        self.scan_mode = scan_mode

        self.io_bus = IOBus(self.in_fifo, self.out_fifo, scan_mode, 
                            x_full_resolution_b1, x_full_resolution_b2,
                            y_full_resolution_b1, y_full_resolution_b2,
                            is_simulation = False)

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
                __addr_x_full_resolution_b1, __addr_x_full_resolution_b2,
                __addr_y_full_resolution_b1,__addr_y_full_resolution_b2,
                is_simulation = False):
        self.iface = iface
        self._logger = logger
        self._level  = logging.DEBUG if self._logger.name == __name__ else logging.TRACE
        self._device = device
        self.__addr_scan_mode = __addr_scan_mode
        self.__addr_x_full_resolution_b1 = __addr_x_full_resolution_b1
        self.__addr_x_full_resolution_b2 = __addr_x_full_resolution_b2
        self.__addr_y_full_resolution_b1 = __addr_y_full_resolution_b1
        self.__addr_y_full_resolution_b2 = __addr_y_full_resolution_b2

        self.text_file = open("packets.txt","w")
        self.is_simulation = is_simulation

        self.y_height = 2048
        self.x_width = 2048
        self.buffer = np.zeros(shape=(self.y_height, self.x_width),
                            dtype = np.uint16)
        self.current_x = 0
        self.current_y = 0

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
    
    def decode_vpoint(self, n):
        try:
            x2, x1, y2, y1, a2, a1 = n
            x = int("{0:08b}".format(x1) + "{0:08b}".format(x2),2)
            y = int("{0:08b}".format(y1) + "{0:08b}".format(y2),2)
            a = int("{0:08b}".format(a1) + "{0:08b}".format(a2),2)
            return [x, y, a]
        except ValueError:
            pass ## 16384 isn't divisible by 3...
            #ignore those pesky extra values.... just for new

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
            print("point", point)
            packet.append(point)
        return packet
    
    @types.coroutine
    def sim_write_2bytes(self, val):
        b1, b2 = get_two_bytes(val)
        print("writing", b1, b2)
        yield from self.iface.write(bits(b2))
        yield from self.iface.write(bits(b1))
        
    async def write_2bytes(self, val):
        b1, b2 = get_two_bytes(val)
        print("writing", b1, b2)
        await self.iface.write(bits(b2))
        await self.iface.write(bits(b1))

    @types.coroutine
    def sim_write_vpoint(self, point):
        x, y, d = point
        yield from self.sim_write_2bytes(x)
        yield from self.sim_write_2bytes(y)
        yield from self.sim_write_2bytes(d)

    async def write_vpoint(self, point):
        x, y, d = point
        print("x:", x, "y:", y, "d:", d)
        await self.write_2bytes(x)
        await self.write_2bytes(y)
        await self.write_2bytes(d)

    async def read_r_packet(self):
        output = await self.iface.read(16384)
        return self.decode_rdwell_packet(output)

    async def try_read_vpoint(self, n_points):
        try:
            output = await asyncio.wait_for(self.iface.read(6*n_points), timeout = 1)
            print("got data")
            return self.decode_vpoint_packet(output)
        except TimeoutError:
            return "timeout"

    async def future_packet(self, future):
        output = await self.iface.read(16384)
        data = self.decode_vpoint_packet(output)
        print(data)
        future.set_result(data)

    async def send_vec_stream_and_recieve_data(self):
        i = 0
        while i < 16384:
            for n in test_vector_points:
                i+=6
                await self.write_vpoint(n)
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        loop.create_task(
            self.future_packet(fut)
        )

    async def set_2byte_register(self,val,addr_b1, addr_b2):
        b1, b2 = get_two_bytes(val)
        b1 = int(bits(b1))
        b2 = int(bits(b2))
        await self._device.write_register(addr_b1, b1)
        await self._device.write_register(addr_b2, b2)

    async def set_x_resolution(self,val):
        self.x_width = val
        ## subtract 1 to account for 0-indexing
        await self.set_2byte_register(val-1,self.__addr_x_full_resolution_b1,self.__addr_x_full_resolution_b2)

    async def set_y_resolution(self,val):
        self.y_height = val
        ## subtract 1 to account for 0-indexing
        await self.set_2byte_register(val-1,self.__addr_y_full_resolution_b1,self.__addr_y_full_resolution_b2)

    async def set_frame_resolution(self,xval,yval):
        await self.set_x_resolution(xval)
        await self.set_y_resolution(yval)
        self.buffer = np.zeros(shape=(self.y_height, self.x_width),
                            dtype = np.uint16)

    async def stream_video(self):
        
        return await self.read_r_packet()

    async def stream_to_buffer(self):
        data = await self.stream_video()
        print(len(data))
        
        partial_start_points = self.current_x
        partial_end_points = ((len(data) - partial_start_points)%self.x_width)
        full_lines = ((len(data) - partial_start_points)//self.x_width)
        if partial_start_points > 0:
            self.buffer[self.current_y][partial_start_points:self.x_width] = data[0:self.x_width-partial_start_points]
            self.current_y += 1
            
        for i in range(0,full_lines):
            self.buffer[self.current_y + i] = data[partial_start_points + i*self.x_width:partial_start_points + (i+1)*self.x_width]
        self.buffer[full_lines+self.current_y][0:partial_end_points] = data[self.x_width*full_lines:self.x_width*full_lines + partial_end_points]
        self.current_y += full_lines
        self.current_x = partial_end_points


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

        scan_mode,             self.__addr_scan_mode  = target.registers.add_rw(2, reset=0)
        x_full_resolution_b1,  self.__addr_x_full_resolution_b1  = target.registers.add_rw(8, reset=0)
        x_full_resolution_b2,  self.__addr_x_full_resolution_b2  = target.registers.add_rw(8, reset=0)
        y_full_resolution_b1,  self.__addr_y_full_resolution_b1  = target.registers.add_rw(8, reset=0)
        y_full_resolution_b2,  self.__addr_y_full_resolution_b2  = target.registers.add_rw(8, reset=0)

        iface.add_subtarget(IOBusSubtarget(
            data=[iface.get_pin(pin) for pin in args.pin_set_data],
            power_ok=iface.get_pin(args.pin_power_ok),
            in_fifo = iface.get_in_fifo(auto_flush = False),
            out_fifo = iface.get_out_fifo(),
            scan_mode = scan_mode,
            x_full_resolution_b1 = x_full_resolution_b1, x_full_resolution_b2 = x_full_resolution_b2,
            y_full_resolution_b1 = y_full_resolution_b1, y_full_resolution_b2 = y_full_resolution_b2
        ))

        

    @classmethod
    def add_run_arguments(cls, parser, access):
        super().add_run_arguments(parser, access)

    async def run(self, device, args):
        iface = await device.demultiplexer.claim_interface(self, self.mux_interface, args)
        scan_iface = ScanGenInterface(iface, self.logger, device, self.__addr_scan_mode,
        self.__addr_x_full_resolution_b1, self.__addr_x_full_resolution_b2,
        self.__addr_y_full_resolution_b1, self.__addr_y_full_resolution_b2)
        return scan_iface
        

    @classmethod
    def add_interact_arguments(cls, parser):
        parser.add_argument("--gui", default=False, action="store_true")

    async def interact(self, device, args, scan_iface):
        # await device.write_register(self.__addr_scan_mode, 3)
        # for j in range(5):
        #     await scan_iface.send_vec_stream_and_recieve_data()

        if args.gui:
            run_gui(scan_iface)
        else:
            #data = await scan_iface.stream_video()
            await scan_iface.set_frame_resolution(2000,1000)
            await device.write_register(self.__addr_scan_mode, 1)
            for n in range(3):
                await scan_iface.stream_to_buffer()
            #print(data)
            #pass



            

                



# -------------------------------------------------------------------------------------------------

class ScanGenAppletTestCase(GlasgowAppletTestCase, applet=ScanGenApplet):
    @synthesis_test
    def test_build(self):
        self.assertBuilds()