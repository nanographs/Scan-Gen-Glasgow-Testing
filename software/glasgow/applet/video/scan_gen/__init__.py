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
from ....support.bits import *
from amaranth.sim import Simulator

from asyncio.exceptions import TimeoutError
from amaranth.lib import data, enum
from amaranth.lib.fifo import SyncFIFO

from ..scan_gen.output_formats.control_gui import run_gui
from ..scan_gen.output_formats.new_server_test import ServerHost

from ... import *

## dealing with relative imports
if "glasgow" in __name__: ## running as applet
    from ..scan_gen.scan_gen_components.main_iobus import IOBus
    from ..scan_gen.scan_gen_components.addresses import *
    from ..scan_gen.scan_gen_components.test_streams import *


class IOBusSubtarget(Elaboratable):
    def __init__(self, data, power_ok, in_fifo, out_fifo, scan_mode,
                x_full_resolution_b1, x_full_resolution_b2, 
                y_full_resolution_b1, y_full_resolution_b2,
                x_upper_limit_b1, x_upper_limit_b2,
                x_lower_limit_b1, x_lower_limit_b2,
                y_upper_limit_b1, y_upper_limit_b2,
                y_lower_limit_b1, y_lower_limit_b2,
                eight_bit_output, do_frame_sync, do_line_sync,
                const_dwell_time, configuration, unpause):
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
                            const_dwell_time, configuration, unpause,
                            test_mode = "data loopback", use_config_handler = True, 
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

        m.d.comb += a_clock.o.eq(self.io_bus.a_clock)
        m.d.comb += d_clock.o.eq(self.io_bus.d_clock)
        
        with m.If(self.io_bus.bus_multiplexer.is_x):
            for i, pad in enumerate(self.data):
                m.d.comb += [
                    pad.oe.eq(self.power_ok.i),
                    pad.o.eq(self.io_bus.pins_o[i]),
                ]
        with m.If(self.io_bus.bus_multiplexer.is_y):
            for i, pad in enumerate(self.data):
                m.d.comb += [
                    pad.oe.eq(self.power_ok.i),
                    pad.o.eq(self.io_bus.pins_o[i]),
                ]
        with m.If(self.io_bus.bus_multiplexer.is_a):
            for i, pad in enumerate(self.data):
                m.d.comb += [
                    self.io_bus.pins_i[i].eq(pad.i)
                ]

        return m

class ScanGenInterface:
    def __init__(self, iface, logger, device, __addr_scan_mode,
                __addr_x_full_resolution_b1, __addr_x_full_resolution_b2,
                __addr_y_full_resolution_b1,__addr_y_full_resolution_b2,
                __addr_x_upper_limit_b1, __addr_x_upper_limit_b2,
                __addr_x_lower_limit_b1, __addr_x_lower_limit_b2,
                __addr_y_upper_limit_b1, __addr_y_upper_limit_b2,
                __addr_y_lower_limit_b1, __addr_y_lower_limit_b2,
                __addr_8_bit_output, __addr_do_frame_sync, __addr_do_line_sync,
                __addr_configuration, __addr_unpause,
                is_simulation = False):
        self.iface = iface
        self._logger = logger
        self._level  = logging.DEBUG if self._logger.name == __name__ else logging.TRACE
        self._device = device
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

        self.text_file = open("packets.txt","w")
        self.is_simulation = is_simulation

        self.eight_bit_output = False


    def fifostats(self):
        iface = self.iface
        iface.statistics()
        self._logger.debug("in tasks:", len(iface._in_tasks._live))
        self._logger.debug("out tasks:", len(iface._out_tasks._live))
        print(len(iface._in_tasks._live))
        print(len(iface._out_tasks._live))
        self._logger.debug("in rtotal:", iface._in_buffer._rtotal)
        self._logger.debug("in wtotal:", iface._in_buffer._wtotal)
        self._logger.debug("out rtotal:", iface._out_buffer._rtotal)
        self._logger.debug("out wtotal:", iface._out_buffer._wtotal)
        self._logger.debug("in pushback:", iface._in_pushback)
        print(iface._in_buffer._rtotal)
        print(iface._in_buffer._wtotal)
        print(iface._out_buffer._rtotal)
        print(iface._out_buffer._wtotal)
        print(iface._in_pushback)
        #print(iface._out_pushback)
    
    def set_endpoint(self, endpoint):
        self.endpoint = endpoint

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

    def decode_vpoint_packet(self, raw_data):
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
    
    def decode_rdwell(self, n):
        a2, a1 = n
        a = int("{0:08b}".format(a1) + "{0:08b}".format(a2),2)
        return a
    
    def decode_rdwell_packet(self, raw_data):
        if isinstance(raw_data, bytes):
            data = list(raw_data)
        else:
            data = raw_data.tolist()
        if self.eight_bit_output:
            return data
        else:
            packet = []
            for n in range(0,len(data),2):
                dwell = self.decode_rdwell(data[n:n+2])
                packet.append(dwell)
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

    async def set_8bit_output(self, val=1):
        await self._device.write_register(self.__addr_8_bit_output, val)
        if val == 1:
            self.eight_bit_output = True
        else:
            self.eight_bit_output = False
        #self.buffer = self.init_buffer()
    
    async def set_frame_sync(self, val=1):
        await self._device.write_register(self.__addr_do_frame_sync, val)

    async def set_line_sync(self,val):
        await self._device.write_register(self.__addr_do_line_sync, val)

    async def set_2byte_register(self,val,addr_b1, addr_b2):
        b1, b2 = get_two_bytes(val)
        b1 = int(bits(b1))
        b2 = int(bits(b2))
        await self._device.write_register(addr_b1, b1)
        await self._device.write_register(addr_b2, b2)

    async def set_x_resolution(self,val):
        print("set x resolution:", val)
        self.x_width = val
        ## subtract 1 to account for 0-indexing
        await self.set_2byte_register(val-1,self.__addr_x_full_resolution_b1,self.__addr_x_full_resolution_b2)
        #self.buffer = self.init_buffer()

    async def set_y_resolution(self,val):
        print("set y resolution:", val)
        self.y_height = val
        ## subtract 1 to account for 0-indexing
        await self.set_2byte_register(val-1,self.__addr_y_full_resolution_b1,self.__addr_y_full_resolution_b2)
        #self.buffer = self.init_buffer()

    async def set_x_upper_limit(self, val):
        self.x_upper_limit = val
        await self.set_2byte_register(val,self.__addr_x_upper_limit_b1,self.__addr_x_upper_limit_b2)

    async def set_x_lower_limit(self, val):
        self.x_lower_limit = val
        await self.set_2byte_register(val,self.__addr_x_lower_limit_b1,self.__addr_x_lower_limit_b2)

    async def set_y_upper_limit(self, val):
        self.y_upper_limit = val
        await self.set_2byte_register(val,self.__addr_y_upper_limit_b1,self.__addr_y_upper_limit_b2)

    async def set_y_lower_limit(self, val):
        self.y_lower_limit = val
        await self.set_2byte_register(val,self.__addr_y_lower_limit_b1,self.__addr_y_lower_limit_b2)

    async def set_frame_resolution(self,xval,yval):
        await self.set_x_resolution(xval)
        await self.set_y_resolution(yval)
        print("set frame resolution x:", xval, "y:", yval)

    async def set_scan_mode(self, val):
        await self._device.write_register(self.__addr_scan_mode, val)
        self.scan_mode = val
        self._logger.info("set scan mode " + str(val))
        print("set scan mode", val)

    async def set_config_flag(self, val):
        await self._device.write_register(self.__addr_configuration, val)
        print("set config flag", val)

    async def pause(self):
        await self._device.write_register(self.__addr_unpause, 0)

    async def unpause(self):
        await self._device.write_register(self.__addr_unpause, 1)

    async def set_raster_mode(self):
        await self._device.write_register(self.__addr_scan_mode, 1)
        print("set raster mode")

    async def set_vector_mode(self):
        await self._device.write_register(self.__addr_scan_mode, 3)
        print("set vector mode")

    async def stream_video(self):
        print("getting data :3")
        data = await self.iface.read(16384)
        self.stream_to_buffer(data)
        # print("sending")
        # await self.endpoint.send(data)

    async def future_packet(self, fut):
        print("getting data")
        data = await self.iface.read()
        print("got data")
        output = self.decode_vpoint_packet(data)
        print(output)
        self.text_file.write(output)
        fut.set_result(data)

    async def future_vpoint(self, fut):
        print("getting data")
        data = await self.iface.read(6)
        print("got data")
        output = self.decode_vpoint_packet(data)
        print(output)
        self.text_file.write(output)
        fut.set_result(data)

    async def rcv_future_data(self, future, n):
        print("waiting for iface read...")
        self._logger.info(f'waiting for read {n}')
        data = await self.iface.read(16384)
        self._logger.info(f'got future data {n}')
        print("got future data", data)
        future.set_result(data)

    async def read_r_packet(self, length = 16384):
        loop = asyncio.get_running_loop()
        logger.debug("Loop:"+ repr(loop))
        output = await self.iface.read(length)
        return self.decode_rdwell_packet(output)

    async def try_read_vpoint(self, n_points):
        try:
            output = await asyncio.wait_for(self.iface.read(6*n_points), timeout = 1)
            print("got data")
            return self.decode_vpoint_packet(output)
        except TimeoutError:
            return "timeout"

    async def send_vec_stream_and_recieve_data(self):
        i = 0
        while i < 16384:
            for n in test_vector_points[0:3]:
                i+=6
                await self.write_vpoint(n)
                asyncio.sleep(0)
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        loop.create_task(
            self.future_packet(fut)
        )
        data = await fut
        print(data)

    async def benchmark(self):
        await self.set_frame_resolution(2048,2048)
        await self.set_raster_mode()
        await self.iface.reset()
        start_time = time.time()
        length = 8388608
        await self.iface.read(length)
        end_time = time.time()
        print(((length/(1000000))/(end_time-start_time)), "MB/s")

    async def scan_frame(self):
        await self.set_frame_resolution(2048,2048)
        await self.set_raster_mode()
        data = await self.read_r_packet()
        print(data)

    async def hilbert(self):
        await self.set_frame_resolution(16384,16384)
        await self.set_vector_mode()
        stream = open("hilbert.txt")
        while True:
            for n in stream:
                data = n.strip(",\n")
                #await asyncio.sleep(0)
                #try:
                await self.write_vpoint(eval(data))
                #except:
                    #await asyncio.sleep(10)

    async def hilbert_loop(self):
        await self.set_frame_resolution(16384,16384)
        await self.set_vector_mode()
        stream = open("hilbert.txt")
        while i < 16384:
            for n in stream:
                data = n.strip(",\n")
                i += 6
                await self.write_vpoint(eval(data))
            data = await self.iface.read()
            print(self.decode_vpoint_packet(data))
            i = 0


class SG_EndpointInterface(ScanGenInterface):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_queue = TaskQueue()
        self.server_host = ServerHost(self.task_queue, self.process_cmd)
        self.streaming = None
        

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


    async def send_packet(self, future_data,n):
        loop = asyncio.get_event_loop()
        future_future_data = loop.create_future()
        await self.rcv_future_data(future_future_data,n)
        data = future_future_data.result()
        self._logger.info(f'recieved future data {n}, length: {str(len(data))}' )
        print("writing", data)
        if data is not None:
            self.server_host.data_writer.write(data)
            await self.server_host.data_writer.drain()
            self._logger.info(f'wrote future data to socket {n}, length: {str(len(data))}')
            self.text_file.write(str(data.tolist()))
            print("send complete")
        future_data.set_result(n)

    async def recv_packet(self):
        print("standing by to recieve packet...")
        await self.data_server_future
        print("reading from server")
        self._logger.info("reading from server")
        print(self.server_host.data_reader)
        while True:
            try:
                data = await self.server_host.data_reader.readexactly(16384)
                print(type(data))
                print("recieved points!", len(data))
                self._logger.info("recieved points from server")
                await self.iface.write(list(data))
                print("wrote data to iface")
                self._logger.info("wrote data to iface")
            except:
                print("err")
                break


    async def stream_data(self):
        n = 0
        while True:
            n += 1
            # loop = asyncio.get_event_loop()
            # future_data = loop.create_future()
            self._logger.info(f'awaiting read {n}')
            if self.scan_mode == 3:
                self._logger.info("created recv_packet task")
                loop.create_task(self.recv_packet())
            data = await self.iface.read(16384)
            self._logger.info(f'got read data {n}')
            self.text_file.write(str(data.tolist()))
            self.server_host.data_writer.write(data)
            await self.server_host.data_writer.drain()
            self._logger.info(f'wrote data to socket {n}')
            #await future_data
            #loop.create_task(self.send_packet(future_data,n))
            #n_fut = await future_data
            #self._logger.info(f'future awaited {n}, future {n_fut}')
            #await asyncio.sleep(0)
            # print("awaiting read")
            # self._logger.info("awaiting read")
            # data = await self.iface.read(16384)
            # print("writing", data)
            # self.server_host.data_writer.write(data)
            # await self.server_host.data_writer.drain()
            # self.text_file.write(str(data.tolist()))
            # print("send complete")

    async def process_cmd(self, cmd):
        c = str(cmd[0:2])
        val = int(cmd[2:])
        self._logger.info(f'cmd recieved: {cmd} - {val}')
        if c == "ps":
            if val == 0:
                await self.pause()
                print("pause")
            if val == 1:
                await self.unpause()
                print("unpaused")
                if self.scan_mode == 3:
                    self._logger.info("created recv_packet task")
                    await self.recv_packet()
                #tasks = asyncio.all_tasks()
                # for task in tasks:
                #     print(task.get_name(), ":", task.get_coro())
                # if self.scan_mode == 3:
                #     await self.recv_packet()
                #     tasks = asyncio.all_tasks()
                #     for task in tasks:
                #         print(task.get_name(), ":", task.get_coro())
                #         task.print_stack()
        elif c == "sc":
            await self.set_scan_mode(val)
            print("set scan mode done")
            
            # print("streaming?", self.stream_data)
            # print("current task:", asyncio.current_task())
            # tasks = asyncio.all_tasks()
            # for task in tasks:
            #     print(task.get_name(), ":", task.get_coro())
        elif c == "rx":
            await self.set_x_resolution(val)
        elif c == "ry":
            await self.set_y_resolution(val)
        elif c == "ux":
            await self.set_x_upper_limit(val)
        elif c == "lx":
            await self.set_x_lower_limit(val)
        elif c == "uy":
            await self.set_y_upper_limit(val)
        elif c == "ly":
            await self.set_y_lower_limit(val)
        elif c == "fs":
            await self.set_frame_sync(val)
        elif c == "ls":
            await self.set_line_sync(val)
        elif c == "8b":
            await self.set_8bit_output(val)
        elif c == "cf":
            await self.set_config_flag(val)


class SG_2DBufferInterface(ScanGenInterface):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.y_height = 2048
        self.x_width = 2048

        self.x_lower_limit = 0
        self.x_upper_limit = self.x_width

        self.y_lower_limit = 0
        self.y_upper_limit = self.y_height

        self.current_x = 0
        self.current_y = 0

        self.buffer = self.init_buffer()

        self.a = self.testpattern()

    def testpattern(self):
        L = [255, 255, 0]
        def gentr_fn(alist):
            while 1:
                for j in alist:
                    yield j
        a = gentr_fn(L)
        return a

    def init_buffer(self):
        if self.eight_bit_output:
            return np.zeros(shape=(self.y_height, self.x_width),
                    dtype = np.uint8)

        else:
            return np.zeros(shape=(self.y_height, self.x_width),
                                dtype = np.uint16)
    
    def stream_to_buffer(self, raw_data):
        data = self.decode_rdwell_packet(raw_data)
        #print("cur x,y", self.current_x, self.current_y)
        
        if self.current_x > 0:
            
            partial_start_points = self.x_width - self.current_x
            #print("psp", partial_start_points)
            full_lines = ((len(data) - partial_start_points)//self.x_width)
            partial_end_points = ((len(data) - partial_start_points)%self.x_width)

            self.buffer[self.current_y][self.current_x:self.x_width] = data[0:partial_start_points]
            # print("rollover index", 0, ":", partial_start_points)
            # print("rollover data", data[0:partial_start_points])
            # print("top rollover")
            # print("top row", self.buffer[self.current_y])
            #print(self.buffer[self.current_y][self.current_x:self.x_width] )
            if self.current_y >= self.y_height - 1:
                self.current_y = 0
                #print("cy 0")
            else:
                self.current_y += 1
                #print("cy+1")
        else:
            #print("no top rollover")
            partial_start_points = 0
            partial_end_points = ((len(data))%self.x_width)
            full_lines = ((len(data))//self.x_width)
            
        for i in range(0,full_lines):
            
            #print("cy", self.current_y)
            #print("mid index", partial_start_points + i*self.x_width, ":",partial_start_points + (i+1)*self.x_width)
            self.buffer[self.current_y] = data[partial_start_points + i*self.x_width:partial_start_points + (i+1)*self.x_width]
            #print("midline", data[partial_start_points + i*self.x_width:partial_start_points + (i+1)*self.x_width])
            if self.current_y >= self.y_height - 1:
                self.current_y = 0
                #print("cy 0")
            else:
                self.current_y += 1
                #print("cy+1")
        
        self.buffer[self.current_y][0:partial_end_points] = data[self.x_width*full_lines + partial_start_points:self.x_width*full_lines + partial_start_points + partial_end_points]
        #print("bottom rollover", partial_end_points)
        #print("rollover index", self.x_width*full_lines + partial_start_points,":",self.x_width*full_lines + partial_start_points + partial_end_points)
        #print(self.buffer[self.current_y][0:partial_end_points])
        #print("last row")
        #print(self.buffer[self.current_y])
        
        self.current_x = partial_end_points
        #assert (self.buffer[self.current_y][0] == 0)

        print(self.buffer.shape)
        #print("=====")

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
        "-B", "--buf", type=str,
        help="local, streaming, 2D", default = "2D")

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

        self.mux_interface = iface = target.multiplexer.claim_interface(self, args, throttle = "none")

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
        print("configuration register:", self.__addr_configuration)

        unpause,                 self.__addr_unpause = target.registers.add_rw(1, reset = 0)

        iface.add_subtarget(IOBusSubtarget(
            data=[iface.get_pin(pin) for pin in args.pin_set_data],
            power_ok=iface.get_pin(args.pin_power_ok),
            in_fifo = iface.get_in_fifo(auto_flush = True),
            out_fifo = iface.get_out_fifo(),
            scan_mode = scan_mode,
            x_full_resolution_b1 = x_full_resolution_b1, x_full_resolution_b2 = x_full_resolution_b2,
            y_full_resolution_b1 = y_full_resolution_b1, y_full_resolution_b2 = y_full_resolution_b2,
            x_upper_limit_b1 = x_upper_limit_b1, x_upper_limit_b2 = x_upper_limit_b2,
            x_lower_limit_b1 = x_upper_limit_b1, x_lower_limit_b2 = x_lower_limit_b2,
            y_upper_limit_b1 = y_upper_limit_b1, y_upper_limit_b2 = y_upper_limit_b2,
            y_lower_limit_b1 = y_upper_limit_b1, y_lower_limit_b2 = y_lower_limit_b2,
            eight_bit_output = eight_bit_output, do_frame_sync = do_frame_sync, do_line_sync = do_line_sync,
            const_dwell_time = const_dwell_time, configuration = configuration, unpause = unpause
        ))
        
    @classmethod
    def add_run_arguments(cls, parser, access):
        super().add_run_arguments(parser, access)

    async def run(self, device, args):
        iface = await device.demultiplexer.claim_interface(self, self.mux_interface, args)

        if args.buf == "2D":
            scan_iface = SG_2DBufferInterface(iface, self.logger, device, self.__addr_scan_mode,
            self.__addr_x_full_resolution_b1, self.__addr_x_full_resolution_b2,
            self.__addr_y_full_resolution_b1, self.__addr_y_full_resolution_b2,
            self.__addr_x_upper_limit_b1, self.__addr_x_upper_limit_b2,
            self.__addr_x_lower_limit_b1, self.__addr_x_lower_limit_b2,
            self.__addr_y_upper_limit_b1, self.__addr_y_upper_limit_b2,
            self.__addr_y_lower_limit_b1, self.__addr_y_lower_limit_b2,
            self.__addr_8_bit_output, self.__addr_do_frame_sync, self.__addr_do_line_sync,
            self.__addr_configuration, self.__addr_unpause
            )
        if args.buf == "local":
            scan_iface = SG_LocalBufferInterface(iface, self.logger, device, self.__addr_scan_mode,
            self.__addr_x_full_resolution_b1, self.__addr_x_full_resolution_b2,
            self.__addr_y_full_resolution_b1, self.__addr_y_full_resolution_b2,
            self.__addr_x_upper_limit_b1, self.__addr_x_upper_limit_b2,
            self.__addr_x_lower_limit_b1, self.__addr_x_lower_limit_b2,
            self.__addr_y_upper_limit_b1, self.__addr_y_upper_limit_b2,
            self.__addr_y_lower_limit_b1, self.__addr_y_lower_limit_b2,
            self.__addr_8_bit_output, self.__addr_do_frame_sync, self.__addr_do_line_sync,
            self.__addr_configuration, self.__addr_unpause
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
            self.__addr_configuration, self.__addr_unpause
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
            self.__addr_configuration, self.__addr_unpause
            )

        return scan_iface
        
    @classmethod
    def add_interact_arguments(cls, parser):
        parser.add_argument("--gui", default=False, action="store_true")
        #ServerEndpoint.add_argument(parser, "endpoint")
        #pass

    async def interact(self, device, args, scan_iface):
        # await scan_iface.set_8bit_output()
        # await scan_iface.set_frame_resolution(512,512)
        # await scan_iface.set_config_flag(1)
        # await scan_iface.set_raster_mode()
        # await scan_iface.set_config_flag(0)
        # for n in range(10):
        #     data = await scan_iface.iface.read(16384)
        #     scan_iface.text_file.write(str(data.tolist()))

        # await scan_iface.set_8bit_output(0)
        # await scan_iface.set_vector_mode()
        # n = 0

        # #https://stackoverflow.com/questions/12944882/how-can-i-infinitely-loop-an-iterator-in-python-via-a-generator-or-other




        # futures = []

        # for i in range(5):
        #     n = 0
        #     while True:
        #         #print("writing")
        #         n += 2
        #         await scan_iface.write_2bytes(next(a))
                
        #         if n >= 16384:
        #             break
        #     print("wrote", n)
        #     #print("reading")
        #     try:
        #         #print(scan_iface.iface._in_buffer._wtotal)
        #         #await scan_iface.iface.flush()
        #         loop = asyncio.get_event_loop()
        #         future = loop.create_future()
        #         futures.append(future)
        #         loop.create_task(rcv_future_data(future))
        #         #data = await asyncio.wait_for(scan_iface.iface.read(16384),timeout=10)
        #         #print("read", len(data.tolist()))
        #         #print(data.tolist())
        #         #scan_iface.text_file.write(str(data.tolist()))
        #     except:
        #         #print("timeout")
        #         pass
        
        # for future in futures:
        #     data = await future
        #     print("recieved", len(data.tolist()))
        #     scan_iface.text_file.write(str(data.tolist()))
        #     #print(data.tolist())

        # await scan_iface.set_vector_mode()
        # for n in range(3):
        #     await scan_iface.write_points()

        # if args.buf == "local":
        #     await scan_iface.set_8bit_output()
        #     await scan_iface.set_frame_sync()
        #     await scan_iface.set_frame_resolution(512,512)
        #     await scan_iface.set_raster_mode()
        #     scan_iface.launch_gui()

        # await scan_iface.set_8bit_output(1)
        # await scan_iface.set_frame_resolution(512,512)
        # await scan_iface.set_config_flag(1)
        # await scan_iface.set_config_flag(0)
        # await scan_iface.set_raster_mode()
        # await scan_iface.unpause()
        data = await scan_iface.iface.read(16384)
        scan_iface.text_file.write(str(data.tolist()))
        # await scan_iface.set_frame_resolution(5120,512)
        # await scan_iface.set_config_flag(1)
        # await scan_iface.set_config_flag(0)
        # data = await scan_iface.iface.read(16384)
        # scan_iface.text_file.write(str(data.tolist()))
        # #await scan_iface.pause()

        
            
        # if args.buf == "endpoint":
        #     #scan_iface.launch_gui()
        #     await scan_iface.pause()
        #     await scan_iface.set_8bit_output(1)
        #     loop = asyncio.get_event_loop()
        #     #loop.set_debug(True)
        #     close_future = loop.create_future()
        #     scan_iface.start_servers(close_future)
        #     try:
        #         await close_future
        #     except Exception as err:
        #         await scan_iface.pause()
        #         print(f'close error: {err}')
        #         #await iface.flush()




        
                



# -------------------------------------------------------------------------------------------------

class ScanGenAppletTestCase(GlasgowAppletTestCase, applet=ScanGenApplet):
    @synthesis_test
    def test_build(self):
        self.assertBuilds()