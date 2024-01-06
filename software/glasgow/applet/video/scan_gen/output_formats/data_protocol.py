import asyncio
import sys
from threading import Thread

# sys.path.append("/Users/isabelburgos/Scan-Gen-Glasgow-Testing/software")
# from glasgow.support.aobject import aobject

from microscope import ScanCtrl
from encoding_test import ScanStream
from tests import generate_hilbert_packet
from data_client import DataClient

sys.path.append("/Users/isabelburgos/Scan-Gen-Glasgow-Testing/software")
from glasgow.support.task_queue import TaskQueue
from glasgow.support.chunked_fifo import ChunkedFIFO


_max_packets_per_ep = 1024
_packets_per_xfer = 32
_xfers_per_queue = min(16, _max_packets_per_ep // _packets_per_xfer)

buffer_size = _max_packets_per_ep*16384

class DataBuffer:
    def __init__(self, protocol):
        self._protocol = protocol
        self._write_buffer_size = buffer_size
        self._read_buffer_size  = buffer_size
        self._in_packet_size = 16384
        self._out_packet_size = 16384

        self._in_pushback  = asyncio.Condition()
        self._out_inflight = 0

        self._in_tasks   = TaskQueue()
        self._in_buffer  = ChunkedFIFO()
        self._out_tasks  = TaskQueue()
        self._out_buffer = ChunkedFIFO()

        self._in_stalls  = 0
        self._out_stalls = 0

        self.scan_stream = ScanStream()

        #loop = asyncio.get_event_loop()
        self.data_processed = asyncio.Barrier(2) #asyncio.Condition()

    
    async def cancel(self):
        if self._in_tasks or self._out_tasks:
            logger.trace("data_server: cancelling operations")
            await self._in_tasks .cancel()
            await self._out_tasks.cancel()

    async def reset(self):
        await self.cancel()

        logger.trace("data_server: asserting reset")
        logger.trace("data_server: synchronizing buffers")
        self._in_buffer .clear()
        self._out_buffer.clear()

        # Pipeline reads
        logger.trace("data_server: pipelining reads")
        #print("pipelining reads")
        for _ in range(_xfers_per_queue):
            self._in_tasks.submit(self._in_task())
        # Give the IN tasks a chance to submit their transfers
        await asyncio.sleep(0)
        #print(f'in tasks: {vars(self._in_tasks)}')
        logger.trace("data_server: deasserting reset")

    # async def _in_task(self):
    #     if self._read_buffer_size is not None:
    #         async with self._in_pushback:
    #             while len(self._in_buffer) > self._read_buffer_size:
    #                 logger.trace("data_server: read pushback")
    #                 await self._in_pushback.wait()

    #     size = self._in_packet_size * _packets_per_xfer
    #     data = await self.iface.read(size)
    #     if not data == None:
    #         self._in_buffer.write(data)
    #         self._in_tasks.submit(self._in_task())
    
    # async def read(self, length=None, *, flush=True):
    #     print("reading")
    #     if flush and len(self._out_buffer) > 0:
    #         print("flushing")
    #         # Flush the buffer, so that everything written before the read reaches the device.
    #         await self.flush(wait=False)

    #     if length is None and len(self._in_buffer) > 0:
    #         # Just return whatever is in the buffer.
    #         length = len(self._in_buffer)
    #     elif length is None:
    #         # Return whatever is received in the next transfer, even if it's nothing.
    #         # (Gateware doesn't normally submit zero-length packets, so, unless that changes
    #         # or customized gateware is used, we'll always get some data here.)
    #         self._in_stalls += 1
    #         await self._in_tasks.wait_one()
    #         length = len(self._in_buffer)
    #     else:
    #         # Return exactly the requested length.
    #         self._in_stalls += 1
    #         while len(self._in_buffer) < length:
    #             print("data_server: need %d bytes", length - len(self._in_buffer))
    #             logger.trace("data_server: need %d bytes", length - len(self._in_buffer))
    #             await self._in_tasks.wait_one()
    #     print("in pushback?")
    #     async with self._in_pushback:
    #         result = self._in_buffer.read(length)
    #         print(f'read result from in buffer')
    #         self._in_pushback.notify_all()
    #     print(f'len(result): {len(result)} < length: {length}?')
    #     if len(result) < length:
    #         chunks  = [result]
    #         length -= len(result)
    #         while length > 0:
    #             async with self._in_pushback:
    #                 chunk = self._in_buffer.read(length)
    #                 self._in_pushback.notify_all()
    #             chunks.append(chunk)
    #             length -= len(chunk)
    #         # Always return a memoryview object, to avoid hard to detect edge cases downstream.
    #         result = memoryview(b"".join(chunks))

    #     print("writing to socket", result.tolist()[0:10])
    #     self.writer.write(result)
    #     await self.writer.drain()
    #     return result

    async def run_buffer(self):
        while True:
            #print("waiting for data")
            await self._protocol._waiter
            print("got data")
            self._protocol._transport.pause_reading()      
            #print("paused reading")
            chunk_len = 16384
            #print(f'buffer: {self._protocol.buffer}')
            while not len(self._protocol.buffer) == 0 and self._protocol._transport is not None:
                #print("chunk")
                data = self._protocol.buffer[:chunk_len]
                self._protocol.buffer = self._protocol.buffer[chunk_len:]
                #print(f'chunk starts with {data[0:10]}')
                print("waiting")
                await asyncio.sleep(0)
                print("!", self.data_processed)
                async with self.data_processed:
                    await self.data_processed.wait()
                    print("!!", self.data_processed)
                    print("notified")
                    await self.write(data)
                    print("wrote")
            #self._protocol._transport._buffer = bytearray(16384) #reset buffer
            #print("reset buffer")
            loop = asyncio.get_event_loop()
            self._protocol._waiter = loop.create_future()
            await asyncio.sleep(0)
            self._protocol._transport.resume_reading()
            print("resume reading")



    def _out_slice(self):
        size = self._out_packet_size * _packets_per_xfer
        data = self._out_buffer.read(size)

        if len(data) < self._out_packet_size:
            data = bytearray(data)
            while len(data) < self._out_packet_size and self._out_buffer:
                data += self._out_buffer.read(self._out_packet_size - len(data))

        self._out_inflight += len(data)
        return data

    @property
    def _out_threshold(self):
        out_xfer_size = self._out_packet_size * _packets_per_xfer
        if self._write_buffer_size is None:
            return out_xfer_size
        else:
            return min(self._write_buffer_size, out_xfer_size)

    async def _out_task(self, data):
        assert len(data) > 0
        
        try:
            print("parsing config")
            self.scan_stream.parse_config_from_data(data)
            #print("notifying")
                

        
            
            # self.data_processed.set_result("done")
            # loop = asyncio.get_event_loop()
            # self.data_processed = loop.create_future()
            # print("data processed future reset")

        finally:
            print("passed")
            self._out_inflight -= len(data)

        if len(self._out_buffer) >= self._out_threshold:
            self._out_tasks.submit(self._out_task(self._out_slice()))

    async def write(self, data):
        #print(f'data processed future: {self.data_processed}')
        if self._write_buffer_size is not None:
            # If write buffer is bounded, and we have more inflight requests than the configured
            # write buffer size, then wait until the inflight requests arrive before continuing.
            if self._out_inflight >= self._write_buffer_size:
                self._out_stalls += 1
            while self._out_inflight >= self._write_buffer_size:
                logger.trace("data_server: write pushback")
                #print("write pushback")
                print("waiting one")
                await self._out_tasks.wait_one()

        # Eagerly check if any of our previous queued writes errored out.
        print("polling out tasks")
        await self._out_tasks.poll()

        print("write to out buffer")
        self._out_buffer.write(data)

        while len(self._out_tasks) < _xfers_per_queue and \
                    len(self._out_buffer) >= self._out_threshold:
            print("submitting out task")
            self._out_tasks.submit(self._out_task(self._out_slice()))
    

    async def flush(self, wait=True):
        logger.trace("data_server: flush")

        if len(self._out_tasks) >= _xfers_per_queue:
            self._out_stalls += 1
        while len(self._out_tasks) >= _xfers_per_queue:
            await self._out_tasks.wait_one()

        assert len(self._out_buffer) <= self._out_packet_size * _packets_per_xfer
        if self._out_buffer:
            data = bytearray()
            while self._out_buffer:
                data += self._out_buffer.read()
            self._out_inflight += len(data)
            self._out_tasks.submit(self._out_task(data))

        if wait:
            logger.trace("data_server: wait for flush")
            if self._out_tasks:
                self._out_stalls += 1
            while self._out_tasks:
                await self._out_tasks.wait_all()



class ScanClient(asyncio.Protocol):
    def __init__(self, on_con_lost:asyncio.Future):
        self._transport = None
        self._new_transport = None
        self.on_con_lost = on_con_lost

    def connection_made(self, transport):
        peername = transport.get_extra_info("peername")
        if peername:
            #print("new connection from:", *peername[0:2])
            self.peername = peername
        else:
            #print("new connection")
            self.peername = ""

        if self._transport is None:
            self._transport = transport
        else:
            #print("closing old connection")
            self._transport.close()
            self._new_transport = transport

    def connection_lost(self, exc):
        #print(f'server closed connection {self.peername}')
        self.on_con_lost.set_result(True)


class ScanDataClient(ScanClient):
    def __init__(self, on_con_lost):
        super().__init__(on_con_lost)
        self.streaming = True
        self.patterning = True
        self.scan_mode = 0
        self.patterngen = generate_hilbert_packet()
        
        #self.scan_stream = ScanStream()
        self.buffer = bytearray()
        loop = asyncio.get_event_loop()
        self._waiter = loop.create_future()
        self._buffer = DataBuffer(self)

    def _wakeup_waiter(self):
        """Wakeup read*() functions waiting for data or EOF."""
        waiter = self._waiter
        if waiter is not None:
            self._waiter = None
            if not waiter.cancelled():
                waiter.set_result(None)


    def connection_made(self, transport):
        super().connection_made(transport)

    # def get_buffer(self, sizehint):
    #     return memoryview(self.buffer)

    def data_received(self, data):
        #print("received", len(data))
        self.buffer.extend(data)
        self._wakeup_waiter()
    #     #print(list(data)[0:10])
    #     #self._transport.pause_reading()
    #     #self._transport.resume_reading()
        if self.scan_mode == 3:
            self.write_pattern()
        
    # def buffer_updated(self, nbytes:int):
    #     print("got data",nbytes)
    #     self._wakeup_waiter()

        # chunk_len = 16384
        # while not len(self.buffer) == 0 and self._transport is not None:
        #     #print("chunk")
        #     data = self.buffer [:chunk_len]
        #     self.buffer = self.buffer [chunk_len:]
        #     self.scan_stream.parse_config_from_data(data)
        # self.buffer = bytearray(16384) #reset buffer


    def write_pattern(self):
        print("writing pattern data")
        data = next(self.patterngen)
        self._transport.write(data)
        #print("wrote data")


class ScanCmdClient(ScanClient):
    def __init__(self, on_con_lost):
        super().__init__(on_con_lost)

    def write(self, cmd):
        self._transport.write(cmd.encode())



class ConnectionClient:
    def __init__(self, close_future):
        self.close_future = close_future
        loop = asyncio.get_event_loop()
        self.data_con_lost = loop.create_future()
        self.cmd_con_lost = loop.create_future()

        self.cmd_client = None
        self.data_client = None

    
    async def start(self):
        loop = asyncio.get_event_loop()
        cmd_connect_future = loop.create_future()
        data_connect_future = loop.create_future()
        loop.create_task(self.open_cmd_client(cmd_connect_future))
        loop.create_task(self.open_data_client(data_connect_future))
        await cmd_connect_future
        await data_connect_future
        loop.create_task(self.data_client._buffer.run_buffer())
               
    async def open_o_data_client(self, connect_future):
        self.data_client = DataClient()
        await self.data_client.open(connect_future)
        await self.data_client.reset()
        self.streaming = asyncio.create_task(self.data_client.read_continously)

    async def open_data_client(self, connect_future):
        print("opening data client")
        loop = asyncio.get_event_loop()
        transport, protocol = await loop.create_connection(
            lambda: ScanDataClient(self.data_con_lost), 
            "127.0.0.1",1238)
        self.data_client = protocol
        self.data_transport = transport
        print(f'transport: {transport}')
        print(f'protocol: {protocol}')
        self.data_transport.pause_reading()
        connect_future.set_result("done")
        try:
            await self.data_con_lost
        except ConnectionRefusedError:
            print("Could not make connection")
        finally:
            transport.close()
    
    async def open_cmd_client(self, connect_future):
        print("opening cmd client")
        loop = asyncio.get_event_loop()
        transport, protocol = await loop.create_connection(
            lambda: ScanCmdClient(self.cmd_con_lost), 
            "127.0.0.1",1237)
        self.cmd_client = protocol
        #print(f'transport: {transport}')
        #print(f'protocol: {protocol}')
        connect_future.set_result("done")
        try:
            await self.cmd_con_lost
        except ConnectionRefusedError:
            print("Could not make connection")
        finally:
            transport.close()
    
    
class ScanInterface(ConnectionClient):
    def __init__(self, close_future):
        super().__init__(close_future)
        self.scan_ctrl = ScanCtrl()

    def strobe_config(self):
        self.cmd_client.write(self.scan_ctrl.raise_config_flag())
        self.cmd_client.write(self.scan_ctrl.lower_config_flag())

    def set_x_resolution(self, xval):
        self.cmd_client.write(self.scan_ctrl.set_x_resolution(xval))

    def set_y_resolution(self, yval):
        self.cmd_client.write(self.scan_ctrl.set_y_resolution(yval))

    def set_dwell_time(self, dval):
        self.cmd_client.write(self.scan_ctrl.set_dwell_time(dval))

    def set_scan_mode(self, mode):
        self.cmd_client.write(self.scan_ctrl.set_scan_mode(mode))
        self.data_client.scan_mode = mode
        if mode == 3:
            self.data_client.write_pattern()

    def set_8bit_output(self):
        self.cmd_client.write(self.scan_ctrl.set_8bit_output())
    
    def set_16bit_output(self):
        self.cmd_client.write(self.scan_ctrl.set_16bit_output())
    
    def pause(self):
        self.cmd_client.write(self.scan_ctrl.pause())
        self.data_transport.pause_reading()


    def unpause(self):
        self.cmd_client.write(self.scan_ctrl.unpause())
        self.data_transport.resume_reading()


    def set_ROI(self, x_upper, x_lower, y_upper, y_lower):
        self.cmd_client.write(self.scan_ctrl.set_ROI(x_upper, x_lower, y_upper, y_lower))




if __name__ == "__main__":
    async def main():
        loop = asyncio.get_event_loop()
        close_future = loop.create_future()
        con = ScanInterface(close_future)
        await con.start()
        async def raster():
            print("setting resolution")
            con.set_x_resolution(512)
            con.set_y_resolution(512)
            con.set_scan_mode(1)
            con.strobe_config()
            con.unpause()
            
            #await asyncio.sleep(5)
        #await raster()
        #con.pause()
        async def vector():
            con.set_x_resolution(1024)
            con.set_y_resolution(1024)
            con.set_scan_mode(3)
            con.strobe_config()
            #con.unpause()
            await asyncio.sleep(10)
        # await vector()
        await raster()
        #con.pause()
        await close_future
        
    def run():
        asyncio.run(main())
    