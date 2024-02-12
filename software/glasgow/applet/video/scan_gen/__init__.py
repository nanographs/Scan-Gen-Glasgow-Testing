import os
import sys
import subprocess
import functools
import types
import time
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
import asyncio
import numpy as np
import threading

from amaranth import *
from amaranth.build import *
from ....support.endpoint import *
from ....support.task_queue import *
from ....support.chunked_fifo import *
from ....support.bits import *
from amaranth.sim import Simulator

from asyncio.exceptions import TimeoutError
from amaranth.lib import data, enum
from amaranth.lib.fifo import SyncFIFO

from ..scan_gen.gateware.main_iobus import IOBus
from ..scan_gen.gateware.structs import *
from ..scan_gen.gateware.test_streams import *
from ..scan_gen.interface.scan_server import ServerHost
from ..scan_gen.interface.scan_stream import ScanStream
from ..scan_gen.interface.microscope import MicroscopeInterface
from ..scan_gen.pattern_generators.hilbert import hilbert
from ..scan_gen.pattern_generators.rectangles import vector_rectangle, vector_gradient_rectangle
from ..scan_gen.pattern_generators.patterngen_utils import packet_from_generator, in2_out1_byte_stream
from ..scan_gen.pattern_generators.bmp_utils import bmp_to_bitstream
from ..scan_gen.gateware.resources import obi_resources

from ... import *


import pyqtgraph as pg

class IOBusSubtarget(Elaboratable):
    def __init__(self, data, power_ok, in_fifo, out_fifo, scan_mode,
                x_full_resolution_b1, x_full_resolution_b2, 
                y_full_resolution_b1, y_full_resolution_b2,
                x_upper_limit_b1, x_upper_limit_b2,
                x_lower_limit_b1, x_lower_limit_b2,
                y_upper_limit_b1, y_upper_limit_b2,
                y_lower_limit_b1, y_lower_limit_b2,
                eight_bit_output, do_frame_sync, do_line_sync,
                const_dwell_time, configuration, unpause, step_size, test_mode, board_version):
        self.board_version = board_version
        if self.board_version == 0:
            self.data = data
            self.power_ok = power_ok
        self.in_fifo = in_fifo
        self.out_fifo = out_fifo
        self.scan_mode = scan_mode
        

        self.io_bus = IOBus(self.in_fifo, self.out_fifo, scan_mode, 
                            x_full_resolution_b1, x_full_resolution_b2,
                            y_full_resolution_b1, y_full_resolution_b2,
                            x_upper_limit_b1, x_upper_limit_b2,
                            x_lower_limit_b1, x_lower_limit_b2,
                            y_upper_limit_b1, y_upper_limit_b2,
                            y_lower_limit_b1, y_lower_limit_b2,
                            eight_bit_output, do_frame_sync, do_line_sync,
                            const_dwell_time, configuration, unpause, step_size,
                            test_mode = test_mode, 
                            is_simulation = False)

        self.pins = Signal(14)

    def elaborate(self, platform):
        m = Module()

        m.submodules["IOBus"] = self.io_bus

        if self.board_version == 0:
            x_latch = platform.request("X_LATCH")
            x_enable = platform.request("X_ENABLE")
            y_latch = platform.request("Y_LATCH")
            y_enable = platform.request("Y_ENABLE")
            a_latch = platform.request("A_LATCH")
            a_enable = platform.request("A_ENABLE")

            a_clock = platform.request("A_CLOCK")
            d_clock = platform.request("D_CLOCK")
        if self.board_version == 1:
            control_signals = platform.request("control")
            power_good = control_signals.D17
            x_latch = control_signals.D19
            y_latch = control_signals.D20
            a_enable = control_signals.D21
            a_latch = control_signals.D22
            d_clock = control_signals.D23
            a_clock = control_signals.D24

        m.d.comb += x_latch.o.eq(self.io_bus.x_latch)
        m.d.comb += y_latch.o.eq(self.io_bus.y_latch)
        m.d.comb += a_latch.o.eq(self.io_bus.a_latch)
        m.d.comb += a_enable.o.eq(self.io_bus.a_enable)

        if self.board_version == 0:
            m.d.comb += x_enable.o.eq(self.io_bus.x_enable)
            m.d.comb += y_enable.o.eq(self.io_bus.y_enable)


        m.d.comb += a_clock.o.eq(self.io_bus.a_clock)
        m.d.comb += d_clock.o.eq(self.io_bus.d_clock)

        if self.board_version == 1:
            # data = platform.request("data")
            power_ok = platform.request("power_ok")
            data_lines = platform.request("data")

            data = [
                data_lines.D1,
                data_lines.D2,
                data_lines.D3,
                data_lines.D4,
                data_lines.D5,
                data_lines.D6,
                data_lines.D7,
                data_lines.D8,
                data_lines.D9,
                data_lines.D10,
                data_lines.D11,
                data_lines.D12,
                data_lines.D13,
                data_lines.D14
            ]


        
        with m.If(self.io_bus.bus_multiplexer.is_x):
            if self.board_version == 0:
                for i, pad in enumerate(self.data):
                    m.d.comb += [
                        pad.oe.eq(self.power_ok.i),
                        pad.o.eq(self.io_bus.pins_o[i]),
                    ]
            if self.board_version == 1:
                for i, pad in enumerate(data):
                    # print(pad)
                    #with m.If(power_ok.i):
                    m.d.comb += pad.oe.eq(1)
                    m.d.comb += pad.o.eq(self.io_bus.pins_o[i])
        with m.If(self.io_bus.bus_multiplexer.is_y):
            if self.board_version == 0:
                for i, pad in enumerate(self.data):
                    m.d.comb += [
                        pad.oe.eq(self.power_ok.i),
                        pad.o.eq(self.io_bus.pins_o[i]),
                    ]
            if self.board_version == 1:
                for i, pad in enumerate(data):
                    #with m.If(power_ok.i):
                    m.d.comb += pad.oe.eq(1)
                    m.d.comb += pad.o.eq(self.io_bus.pins_o[i])
        with m.If(self.io_bus.bus_multiplexer.is_a):
            if self.board_version == 0:
                for i, pad in enumerate(self.data):
                    m.d.comb += [
                        self.io_bus.pins_i[i].eq(pad.i)
                    ]
            if self.board_version == 1:
                for i, pad in enumerate(data):
                    m.d.comb += self.io_bus.pins_i[i].eq(pad.i)

        return m

class ScanGenInterface(MicroscopeInterface):
    def __init__(self, iface, logger, device, __addr_scan_mode,
                __addr_x_full_resolution_b1, __addr_x_full_resolution_b2,
                __addr_y_full_resolution_b1,__addr_y_full_resolution_b2,
                __addr_x_upper_limit_b1, __addr_x_upper_limit_b2,
                __addr_x_lower_limit_b1, __addr_x_lower_limit_b2,
                __addr_y_upper_limit_b1, __addr_y_upper_limit_b2,
                __addr_y_lower_limit_b1, __addr_y_lower_limit_b2,
                __addr_8_bit_output, __addr_do_frame_sync, __addr_do_line_sync,
                __addr_configuration, __addr_unpause, __addr_step_size,
                __addr_const_dwell_time,
                is_simulation = False):
        self.iface = iface
        self._logger = logger
        self.logging = True
        self._level  = logging.DEBUG if self._logger.name == __name__ else logging.TRACE
        self._device = device

        self.logging = True
        self.text_file = open("packets.txt","w")
        self.is_simulation = is_simulation
        self.eight_bit_output = False

        ### ======= Registers =========
        self.__addr_scan_mode = __addr_scan_mode
        self.scan_mode = 0
        self.__addr_x_full_resolution_b1 = __addr_x_full_resolution_b1
        self.__addr_x_full_resolution_b2 = __addr_x_full_resolution_b2
        self.__addr_y_full_resolution_b1 = __addr_y_full_resolution_b1
        self.__addr_y_full_resolution_b2 = __addr_y_full_resolution_b2

        self.__addr_x_upper_limit_b1 = __addr_x_upper_limit_b1
        self.__addr_x_upper_limit_b2 = __addr_x_upper_limit_b2
        self.__addr_x_lower_limit_b1 = __addr_x_lower_limit_b1
        self.__addr_x_lower_limit_b2 = __addr_x_lower_limit_b2

        self.__addr_y_upper_limit_b1 = __addr_y_upper_limit_b1
        self.__addr_y_upper_limit_b2 = __addr_y_upper_limit_b2
        self.__addr_y_lower_limit_b1 = __addr_y_lower_limit_b1
        self.__addr_y_lower_limit_b2 = __addr_y_lower_limit_b2

        self.__addr_8_bit_output = __addr_8_bit_output
        self.__addr_do_frame_sync = __addr_do_frame_sync
        self.__addr_do_line_sync = __addr_do_line_sync

        self.__addr_configuration = __addr_configuration
        self.__addr_unpause = __addr_unpause
        self.__addr_step_size = __addr_step_size
        self.__addr_const_dwell_time = __addr_const_dwell_time
        ## ======= end registers =======

        self.x_width = 0
        self.y_height = 0
    
    async def write(self, *args, **kwargs):
        return await self.iface.write(*args, **kwargs)
    
    async def read(self, *args, **kwargs):
        return await self.iface.read(*args, **kwargs)

    def fifostats(self):
        iface = self.iface
        self._logger.debug(f'in tasks: {len(iface._in_tasks._live)}')
        self._logger.debug(f'out tasks: {len(iface._out_tasks._live)}')
        self._logger.debug(f'in rtotal: {iface._in_buffer._rtotal}')
        self._logger.debug(f'in wtotal: {iface._in_buffer._wtotal}')
        self._logger.debug(f'out rtotal {iface._out_buffer._rtotal}')
        self._logger.debug(f'out wtotal: {iface._out_buffer._wtotal}')
        self._logger.debug(f'out inflight: {iface._out_inflight}')
        self._logger.debug(f'out threshold: {iface._out_threshold}')
        self._logger.debug(f'write buffer size: {iface._write_buffer_size}')
        self._logger.debug(f'read buffer size: {iface._read_buffer_size}')

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

    async def set_2byte_register(self,val,addr_b1, addr_b2):
        b1, b2 = get_two_bytes(val)
        b1 = int(bits(b1))
        b2 = int(bits(b2))
        #print("writing", b1, b2)
        await asyncio.gather(self._device.write_register(addr_b1, b1),
        self._device.write_register(addr_b2, b2))

    async def set_8bit_output(self, val=1):
        await self._device.write_register(self.__addr_8_bit_output, val)
        if val == 1:
            self.eight_bit_output = True
        else:
            self.eight_bit_output = False
    
    async def set_frame_sync(self, val=1):
        await self._device.write_register(self.__addr_do_frame_sync, val)

    async def set_line_sync(self,val):
        await self._device.write_register(self.__addr_do_line_sync, val)

    async def set_ROI(self, x_lower, x_upper, y_lower, y_upper):
        await self.set_x_lower_limit(x_lower)
        await self.set_x_upper_limit(x_upper)
        await self.set_y_lower_limit(y_lower)
        await self.set_y_upper_limit(y_upper)

    async def set_x_resolution(self,val):
        assert(val > 0)
        self.x_width = val
        ## subtract 1 to account for 0-indexing
        await self.set_2byte_register(val-1,self.__addr_x_full_resolution_b1,self.__addr_x_full_resolution_b2)
        await self.set_step_size()
        print("set x resolution:", val)

    async def set_y_resolution(self,val):
        assert(val > 0)
        self.y_height = val
        ## subtract 1 to account for 0-indexing
        await self.set_2byte_register(val-1,self.__addr_y_full_resolution_b1,self.__addr_y_full_resolution_b2)
        await self.set_step_size()
        print("set y resolution:", val)

    async def set_x_upper_limit(self, val):
        assert(val >= 0)
        if val == 0:
            val = self.x_width
        self.x_upper_limit = val
        await self.set_2byte_register(val,self.__addr_x_upper_limit_b1,self.__addr_x_upper_limit_b2)

    async def set_x_lower_limit(self, val):
        assert(val >= 0)
        self.x_lower_limit = val
        await self.set_2byte_register(val,self.__addr_x_lower_limit_b1,self.__addr_x_lower_limit_b2)

    async def set_y_upper_limit(self, val):
        assert(val >= 0)
        if val == 0:
            val = self.y_height
        self.y_upper_limit = val
        await self.set_2byte_register(val,self.__addr_y_upper_limit_b1,self.__addr_y_upper_limit_b2)

    async def set_y_lower_limit(self, val):
        assert(val >= 0)
        self.y_lower_limit = val
        await self.set_2byte_register(val,self.__addr_y_lower_limit_b1,self.__addr_y_lower_limit_b2)

    async def set_frame_resolution(self,xval,yval):
        await self.set_x_resolution(xval)
        await self.set_y_resolution(yval)
        print("set frame resolution x:", xval, "y:", yval)

    async def set_scan_mode(self, val):
        assert(3 >= val > 0)
        await self._device.write_register(self.__addr_scan_mode, val)
        self.scan_mode = val
        if self.logging:
            self._logger.info("set scan mode " + str(val))
        print("set scan mode", val)

    async def set_config_flag(self, val):
        assert(1 >= val >= 0)
        await self._device.write_register(self.__addr_configuration, val)
        print("set config flag", val)

    async def set_dwell_time(self, val):
        assert(val > 0)
        ## subtract 1 to account for 0-indexing
        await self._device.write_register(self.__addr_const_dwell_time, val-1)
        print("set dwell time", val)

    async def pause(self):
        await self._device.write_register(self.__addr_unpause, 0)
        print("paused")

    async def unpause(self):
        await self._device.write_register(self.__addr_unpause, 1)
        print("unpaused")

    async def set_raster_mode(self):
        await self._device.write_register(self.__addr_scan_mode, 1)
        print("set raster mode")

    async def set_vector_mode(self):
        await self._device.write_register(self.__addr_scan_mode, 3)
        print("set vector mode")

    async def set_step_size(self):
        step_size = (16384//(max(self.x_width, self.y_height)))
        await self._device.write_register(self.__addr_step_size, step_size)
        print("set step size", step_size)

    async def benchmark(self):
        await self.set_frame_resolution(2048,2048)
        await self.set_raster_mode()
        await self.iface.reset()
        start_time = time.time()
        length = 8388608
        await self.iface.read(length)
        end_time = time.time()
        print(((length/(1000000))/(end_time-start_time)), "MB/s")


class SG_EndpointInterface(ScanGenInterface):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_queue = TaskQueue()
        self.server_host = ServerHost(self.process_cmd)
        self.streaming = None
        self.logging = True
        print(f'logging? {self.logging}')

        self.write_buffer = ChunkedFIFO()
        self.in_tasks = TaskQueue()
        

    def start_servers(self, close_future):
        self.close_future = close_future
        loop = asyncio.get_event_loop()
        self.data_server_future = loop.create_future()
        self.server_host.start_servers(self.data_server_future)
        self.streaming = asyncio.ensure_future(self.stream_data())

    def close(self):
        self.close_future.set_result("Closed")

    def launch_gui(self):
        ## using sys.prefix instead of "python3" results in a PermissionError
        ## because pipx isn't supposed to be used that way
        ## would be nice to stay in the same environment though
        subprocess.Popen(["python3", "software/glasgow/applet/video/scan_gen/output_formats/streaming_gui.py"],
                        start_new_session = True)

    # async def send_packet(self, future_data,n):
    #     loop = asyncio.get_event_loop()
    #     future_future_data = loop.create_future()
    #     await self.rcv_future_data(future_future_data,n)
    #     data = future_future_data.result()
    #     if self.logging:
    #         self._logger.info(f'received future data {n}, length: {str(len(data))}' )
    #     print("writing", data)
    #     if data is not None:
    #         self.server_host.data_writer.write(data)
    #         await self.server_host.data_writer.drain()
    #         self._logger.info(f'wrote future data to socket {n}, length: {str(len(data))}')
    #         self.text_file.write(str(data.tolist()))
    #         print("send complete")
    #     future_data.set_result(n)

    async def recv_packet(self, n):
        print(f'standing by to recieve pattern packet {n}...')
        await self.data_server_future
        print(f'reading from data server {n}')
        if self.logging:
            self._logger.info(f'reading from data server {n}')
        print(self.server_host.data_reader)
        print("data reader at eof?", self.server_host.data_reader.at_eof())
        print(len(self.server_host.data_reader._buffer))
        try:
            data = await self.server_host.data_reader.readexactly(16384*3)
            #data = await self.server_host.data_reader.read()
            print(f'recieved {len(data)} points, {n}')
            if self.logging:
                self._logger.info(f'recieved points from server {n}')
            await self.iface.write(list(data))
            print(f'wrote data to iface {n}')
            if self.logging:
                self._logger.info(f'wrote data to iface {n}')
            #await self.iface.flush()
        except Exception as err:
            print(f'error: {err}')

    async def stream_data(self):
        n = 0
        while True:
            try:
                if (self.scan_mode == 3) | (self.scan_mode == 2):
                    await self.recv_packet(n)
                if self.logging:
                    self._logger.info(f'awaiting read {n}')
                data = await self.iface.read(16384)
                n += 1
                if self.logging:
                    self._logger.info(f'got read data {n}')
                    self.text_file.write(str(data.tolist()))
                self.server_host.data_writer.write(data)
                await self.server_host.data_writer.drain()
                if self.logging:
                    self._logger.info(f'wrote data to socket {n}')
            except Exception as exc:
                print(f'error streaming: {exc}')
                break

    async def process_cmd(self, cmd):
        c = str(cmd[0:2])
        val = int(cmd[2:])
        if self.logging:
            self._logger.info(f'cmd recieved: {cmd} - {val}')
        if c == "ps":
            if val == 0:
                #await self.pause()
                self.task_queue.submit(self.pause())
                print("pause")
            if val == 1:
                #await self.unpause()
                self.task_queue.submit(self.unpause())
                print("unpaused")
                if (self.scan_mode == 3) | (self.scan_mode == 2):
                    if self.logging:
                        self._logger.info("created recv_packet task")
                    #await self.recv_packet("*")
                    self.task_queue.submit(self.recv_packet("*"))
        elif c == "sc":
            #await self.set_scan_mode(val)
            self.task_queue.submit(self.set_scan_mode(val))
            print("set scan mode done")
        elif c == "dw":
            #await self.set_dwell_time(val)
            self.task_queue.submit(self.set_dwell_time(val))
        elif c == "rx":
            #await self.set_x_resolution(val)
            self.task_queue.submit(self.set_x_resolution(val))
        elif c == "ry":
            #await self.set_y_resolution(val)
            self.task_queue.submit(self.set_y_resolution(val))
        elif c == "ux":
            #await self.set_x_upper_limit(val)
            self.task_queue.submit(self.set_x_upper_limit(val))
        elif c == "lx":
            #await self.set_x_lower_limit(val)
            self.task_queue.submit(self.set_x_lower_limit(val))
        elif c == "uy":
            #await self.set_y_upper_limit(val)
            self.task_queue.submit(self.set_y_upper_limit(val))
        elif c == "ly":
            #await self.set_y_lower_limit(val)
            self.task_queue.submit(self.set_y_lower_limit(val))
        elif c == "8b":
            #await self.set_8bit_output(val)
            self.task_queue.submit(self.set_8bit_output(val))
        elif c == "cf":
            #await self.set_config_flag(val)
            self.task_queue.submit(self.set_config_flag(val))
        
        await self.task_queue.poll()


class SG_LocalBufferInterface(ScanGenInterface):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cwd = os.getcwd()
        self.dimension, self.dimension_path = self.save_dimension(512)
        self.buf, self.buf_path = self.create_buf_file()
        self.last_pixel = 0
    def save_dimension(self, dimension):
        path = f'{self.cwd}/current_display_setting'
        np.savetxt(path, [dimension])
        return dimension, path
    def create_buf_file(self):
        path = f'{self.cwd}/current_frame'
        buf = np.memmap(path, np.uint8, shape = (self.dimension*self.dimension), mode = "w+")
        return buf, path
    def stream_to_buf(self, raw_data):
        # print("-----------")
        data = raw_data.tolist()
        d = np.array(data)
        print(d)
        # print(buf)
        zero_index = np.nonzero(d < 1)[0]
        # print("buffer length:", len(buf))
        # print("last pixel:",current.last_pixel)
        #print("d length:", len(d))
        # print("d:",d)
        
        if len(zero_index) > 0: #if a zero was found
            # current.n += 1
            # print("zero index:",zero_index)
            zero_index = int(zero_index)

            self.buf[:d[zero_index+1:].size] = d[zero_index+1:]
            # print(buf[:d[zero_index+1:].size])
            # print(d[:zero_index+1].size)
            self.buf[self.dimension * self.dimension - zero_index:] = d[:zero_index]
            # print(buf[dimension * dimension - zero_index:])
            self.last_pixel = d[zero_index+1:].size
            
        else: 
            if len(self.buf[self.last_pixel:self.last_pixel+len(d)]) < len(d):
                pass
            #     print("data too long to fit in end of frame, but no zero")
            #     print(d[:dimension])
            self.buf[self.last_pixel:self.last_pixel + d.size] = d
            # print(buf[current.last_pixel:current.last_pixel + d.size])
            self.last_pixel = self.last_pixel + d.size
    async def stream_video(self):
        print("getting data")
        raw_data = await self.iface.read(16384)
        print("got data")
        threading.Thread(target=self.stream_to_buf(raw_data)).start()
    def launch_gui(self):
        ## using sys.prefix instead of "python3" results in a PermissionError
        ## because pipx isn't supposed to be used that way
        ## would be nice to stay in the same environment though
        subprocess.Popen(["python3", "software/glasgow/applet/video/scan_gen/output_formats/local_gui.py"],
                        start_new_session = True)
        


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
        "-R", "--vers", type=int,
        help="OBI board revision: 0, 1", default = "0")
        parser.add_argument(
        "-T", "--test_mode", type=str,
        help="gateware build configuration: loopback, data loopback", default = None)
        parser.add_argument(
        "-B", "--buf", type=str,
        help="local, endpoint", default = "None")

    def build(self, target, args):
        ### LVDS Header (Not used as LVDS)
        if args.vers == 0:
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
        
        if args.vers == 1:
            target.platform.add_resources(obi_resources)

        self.mux_interface = iface = target.multiplexer.claim_interface(self, args, throttle = "none")

        #==================Registers=================
        scan_mode,             self.__addr_scan_mode  = target.registers.add_rw(2, reset=0)
        x_full_resolution_b1,  self.__addr_x_full_resolution_b1  = target.registers.add_rw(8, reset=0)
        x_full_resolution_b2,  self.__addr_x_full_resolution_b2  = target.registers.add_rw(8, reset=0)
        y_full_resolution_b1,  self.__addr_y_full_resolution_b1  = target.registers.add_rw(8, reset=0)
        y_full_resolution_b2,  self.__addr_y_full_resolution_b2  = target.registers.add_rw(8, reset=0)

        x_upper_limit_b1,      self.__addr_x_upper_limit_b1  = target.registers.add_rw(8, reset=0)
        x_upper_limit_b2,      self.__addr_x_upper_limit_b2  = target.registers.add_rw(8, reset=0)
        x_lower_limit_b1,      self.__addr_x_lower_limit_b1  = target.registers.add_rw(8, reset=0)
        x_lower_limit_b2,      self.__addr_x_lower_limit_b2  = target.registers.add_rw(8, reset=0)

        y_upper_limit_b1,      self.__addr_y_upper_limit_b1  = target.registers.add_rw(8, reset=0)
        y_upper_limit_b2,      self.__addr_y_upper_limit_b2  = target.registers.add_rw(8, reset=0)
        y_lower_limit_b1,      self.__addr_y_lower_limit_b1  = target.registers.add_rw(8, reset=0)
        y_lower_limit_b2,      self.__addr_y_lower_limit_b2  = target.registers.add_rw(8, reset=0)

        eight_bit_output,      self.__addr_8_bit_output  = target.registers.add_rw(1, reset=0)
        do_frame_sync,         self.__addr_do_frame_sync  = target.registers.add_rw(1, reset=0)
        do_line_sync,          self.__addr_do_line_sync  = target.registers.add_rw(1, reset=0)

        const_dwell_time,      self.__addr_const_dwell_time = target.registers.add_rw(8, reset=0)

        configuration,         self.__addr_configuration = target.registers.add_rw(1, reset=0)

        unpause,                 self.__addr_unpause = target.registers.add_rw(1, reset = 0)
        step_size,              self.__addr_step_size = target.registers.add_rw(8, reset = 1)
        #===============================================

        iface.add_subtarget(IOBusSubtarget(
            data=[iface.get_pin(pin) for pin in args.pin_set_data],
            power_ok=iface.get_pin(args.pin_power_ok),
            in_fifo = iface.get_in_fifo(auto_flush = False),
            out_fifo = iface.get_out_fifo(),
            scan_mode = scan_mode,
            x_full_resolution_b1 = x_full_resolution_b1, x_full_resolution_b2 = x_full_resolution_b2,
            y_full_resolution_b1 = y_full_resolution_b1, y_full_resolution_b2 = y_full_resolution_b2,
            x_upper_limit_b1 = x_upper_limit_b1, x_upper_limit_b2 = x_upper_limit_b2,
            x_lower_limit_b1 = x_lower_limit_b1, x_lower_limit_b2 = x_lower_limit_b2,
            y_upper_limit_b1 = y_upper_limit_b1, y_upper_limit_b2 = y_upper_limit_b2,
            y_lower_limit_b1 = y_lower_limit_b1, y_lower_limit_b2 = y_lower_limit_b2,
            eight_bit_output = eight_bit_output, do_frame_sync = do_frame_sync, do_line_sync = do_line_sync,
            const_dwell_time = const_dwell_time, configuration = configuration, unpause = unpause, step_size = step_size,
            test_mode = args.test_mode, board_version = args.vers
        ))
        
    @classmethod
    def add_run_arguments(cls, parser, access):
        super().add_run_arguments(parser, access)

    async def run(self, device, args):
        iface = await device.demultiplexer.claim_interface(self, self.mux_interface, args)
                                    # read_buffer_size = 10*16384,
                                    # write_buffer_size = 10*16384)

        if args.buf == "local":
            scan_iface = SG_LocalBufferInterface(iface, self.logger, device, self.__addr_scan_mode,
            self.__addr_x_full_resolution_b1, self.__addr_x_full_resolution_b2,
            self.__addr_y_full_resolution_b1, self.__addr_y_full_resolution_b2,
            self.__addr_x_upper_limit_b1, self.__addr_x_upper_limit_b2,
            self.__addr_x_lower_limit_b1, self.__addr_x_lower_limit_b2,
            self.__addr_y_upper_limit_b1, self.__addr_y_upper_limit_b2,
            self.__addr_y_lower_limit_b1, self.__addr_y_lower_limit_b2,
            self.__addr_8_bit_output, self.__addr_do_frame_sync, self.__addr_do_line_sync,
            self.__addr_configuration, self.__addr_unpause, self.__addr_step_size,
            self.__addr_const_dwell_time
            )
        if args.buf == "endpoint":
            scan_iface = SG_EndpointInterface(iface, self.logger, device, self.__addr_scan_mode,
            self.__addr_x_full_resolution_b1, self.__addr_x_full_resolution_b2,
            self.__addr_y_full_resolution_b1, self.__addr_y_full_resolution_b2,
            self.__addr_x_upper_limit_b1, self.__addr_x_upper_limit_b2,
            self.__addr_x_lower_limit_b1, self.__addr_x_lower_limit_b2,
            self.__addr_y_upper_limit_b1, self.__addr_y_upper_limit_b2,
            self.__addr_y_lower_limit_b1, self.__addr_y_lower_limit_b2,
            self.__addr_8_bit_output, self.__addr_do_frame_sync, self.__addr_do_line_sync,
            self.__addr_configuration, self.__addr_unpause, self.__addr_step_size,
            self.__addr_const_dwell_time
            )
        else:
            scan_iface = ScanGenInterface(iface, self.logger, device, self.__addr_scan_mode,
            self.__addr_x_full_resolution_b1, self.__addr_x_full_resolution_b2,
            self.__addr_y_full_resolution_b1, self.__addr_y_full_resolution_b2,
            self.__addr_x_upper_limit_b1, self.__addr_x_upper_limit_b2,
            self.__addr_x_lower_limit_b1, self.__addr_x_lower_limit_b2,
            self.__addr_y_upper_limit_b1, self.__addr_y_upper_limit_b2,
            self.__addr_y_lower_limit_b1, self.__addr_y_lower_limit_b2,
            self.__addr_8_bit_output, self.__addr_do_frame_sync, self.__addr_do_line_sync,
            self.__addr_configuration, self.__addr_unpause, self.__addr_step_size,
            self.__addr_const_dwell_time
            )

        return scan_iface
        
    @classmethod
    def add_interact_arguments(cls, parser):
        parser.add_argument("--gui", default=False, action="store_true")
        #ServerEndpoint.add_argument(parser, "endpoint")

    async def interact(self, device, args, scan_iface):
        if args.buf == "None":
            pass

        if args.buf == "local":
            await scan_iface.set_8bit_output()
            await scan_iface.set_frame_sync()
            await scan_iface.set_frame_resolution(512,512)
            await scan_iface.set_raster_mode()
            scan_iface.launch_gui()

        if args.buf == "test_raster":
            await scan_iface.pause()
            await scan_iface.set_raster_mode()
            await scan_iface.set_frame_resolution(512, 512)
            await scan_iface.set_8bit_output(1)
            await scan_iface.set_config_flag(1)
            await scan_iface.set_config_flag(0)
            await scan_iface.unpause()
            data = await scan_iface.iface.read(16384)
            scan_iface.text_file.write(str(data.tolist()))
            # await scan_iface.set_frame_resolution(512,512)
            # await scan_iface.set_config_flag(1)
            # await scan_iface.set_config_flag(0)
            # data = await scan_iface.iface.read(16384)
            # scan_iface.text_file.write(str(data.tolist()))

        ## tests that vector mode works
        if args.buf == "test_vector":
            scan_stream = ScanStream()
            scan_stream.change_buffer(1024, 1024)
            r = vector_gradient_rectangle(1024, 512 ,3)
            patterngen = packet_from_generator(r)
            r2 = vector_gradient_rectangle(1024, 512 ,3)
            #patterngen_check_against = in2_out1_byte_stream(r2)
            await scan_iface.set_vector_mode()
            await scan_iface.set_frame_resolution(1024,1024)
            await scan_iface.set_config_flag(1)
            await scan_iface.set_config_flag(0)
            await scan_iface.unpause()
            for n in range(2):
                for i in range(3):
                    pattern = next(patterngen)
                    scan_iface.text_file.write("\n=====Sent=====\n")
                    scan_iface.text_file.write(str(list(pattern)))
                    await scan_iface.write(pattern)
                data = await scan_iface.read(16384)
                scan_iface.text_file.write("\n=====Received=====\n")
                scan_iface.text_file.write(str(data.tolist()))
                print("wrote data to text file")
                if n == 0:
                    config = data[0:18]
                    print(f'config: {config.tolist()}')
                    data = memoryview(bytes(data[18:])).cast('H').tolist()
                else:
                    data = memoryview(bytes(data)).cast('H').tolist()
                print(len(data))
                for d in data:
                    x = next(r2)
                    y = next(r2)
                    check_against = next(r2)
                    print(f'x: {x}, y: {y}, d: {check_against}')
                    print(f'{d} == {check_against}?')
                    try:
                        assert(d == check_against)
                    except AssertionError:
                        print("NOT A MATCH")
                
            #     scan_stream.parse_config_from_data(bytes(data))
            # pg.image(scan_stream.buffer)
            # pg.exec()
            #scan_iface.text_file.write(scan_stream.buffer)

        if args.buf == "test_raster_pattern":
            file = "/Users/isabelburgos/Scan-Gen-Glasgow-Testing/software/glasgow/applet/video/scan_gen/input_formats/Nanographs Pattern Test Logo and Gradients.bmp"
            stream = bmp_to_bitstream(file, 2048, 2048)
            patterngen = packet_from_generator(stream)
            await scan_iface.set_8bit_output(1)
            await scan_iface.set_scan_mode(2)
            await scan_iface.set_frame_resolution(2048, 2048)
            await scan_iface.set_config_flag(1)
            await scan_iface.set_config_flag(0)
            await scan_iface.unpause()
            for n in range(10):
                pattern = next(patterngen)
                scan_iface.text_file.write("\n SENT: \n")
                scan_iface.text_file.write(str(list(pattern)))
                await scan_iface.write(pattern)
                pattern = next(patterngen)
                scan_iface.text_file.write("\n SENT: \n")
                scan_iface.text_file.write(str(list(pattern)))
                await scan_iface.write(pattern)
                data = await scan_iface.read(16384)
                scan_iface.text_file.write("\n RCVD: \n")
                scan_iface.text_file.write(str(data.tolist()))

        if args.buf == "hilbert":
            await scan_iface.hilbert_loop()

        if args.buf == "endless":
            await scan_iface.pause()
            await scan_iface.set_raster_mode()
            await scan_iface.set_frame_resolution(100,100)
            await scan_iface.set_config_flag(1)
            await scan_iface.set_config_flag(0)
            await scan_iface.unpause()
            while True:
                data = await scan_iface.iface.read(16384)

        
            
        if args.buf == "endpoint":
            if args.gui:
                scan_iface.launch_gui()
            await scan_iface.pause()
            await scan_iface.set_8bit_output(1)
            loop = asyncio.get_event_loop()
            #loop.set_debug(True)
            close_future = loop.create_future()
            scan_iface.start_servers(close_future)
            try:
                await close_future
            except Exception as err:
                await scan_iface.pause()
                print(f'close error: {err}')
                #await iface.flush()




        
                



# -------------------------------------------------------------------------------------------------

class ScanGenAppletTestCase(GlasgowAppletTestCase, applet=ScanGenApplet):
    @synthesis_test
    def test_build(self):
        self.assertBuilds()