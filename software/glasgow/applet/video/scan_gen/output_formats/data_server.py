import asyncio
import sys
sys.path.append("/Users/isabelburgos/Scan-Gen-Glasgow-Testing/software")
from glasgow.support.task_queue import TaskQueue
from glasgow.support.chunked_fifo import ChunkedFIFO

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

logging.basicConfig(filename='otherlogs.txt', filemode='w', level=logging.DEBUG)


_max_packets_per_ep = 1024
_packets_per_xfer = 32
_xfers_per_queue = min(16, _max_packets_per_ep // _packets_per_xfer)

buffer_size = _max_packets_per_ep*16384

class fake_iface:
    def __init__(self):
        self.paused = asyncio.Condition()
        self.scan_mode = 0
    async def read(self, size):
        print("iface read...")
        async with self.paused():
            await self.paused.wait()
            print("... iface unpaused")
            data = bytes([5]*size)
            await asyncio.sleep(1)
            return data

    async def write(self, data):
        if not self.paused:
            await asyncio.sleep(1)
            print("wrote data")


class DataServer:
    def __init__(self, host, port, iface=None):
        self.host = host
        self.port = port


        if iface == None:
            self.iface = fake_iface()
        else:
            self.iface = iface

        loop = asyncio.get_event_loop()
        self.connect_future = loop.create_future()
        self.reader = None
        self.writer = None

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

        self.streaming = True
        self.stream_task = None
        self.patterning = True

        self.scan_mode = 0
    
    async def start(self):
        self.data_server = await asyncio.start_server(self.connect, self.host, self.port)
        await self.data_server.serve_forever()
        
    async def connect(self, reader, writer):
        self.reader = reader
        self.writer = writer
        print("data server made connection")
        addr = writer.get_extra_info('peername')
        print(f"addr: {addr!r}")
        #self.connect_future.set_result("done")
        self.stream_task = asyncio.ensure_future(self.stream_continously())
    
    async def stream_continously(self):
        while self.streaming:
            await self.exchange_packets()

    async def exchange_packets(self):
        print("reading data from iface")
        await self.read(16384)


        print("reading data from socket")
        await self.write(16384)



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
        print("pipelining reads")
        for _ in range(_xfers_per_queue):
            self._in_tasks.submit(self._in_task())
        # Give the IN tasks a chance to submit their transfers
        await asyncio.sleep(0)
        #print(f'in tasks: {vars(self._in_tasks)}')
        logger.trace("data_server: deasserting reset")

    async def _in_task(self):
        if self._read_buffer_size is not None:
            async with self._in_pushback:
                while len(self._in_buffer) > self._read_buffer_size:
                    logger.trace("data_server: read pushback")
                    await self._in_pushback.wait()

        size = self._in_packet_size * _packets_per_xfer
        data = await self.iface.read(size)
        if not data == None:
            self._in_buffer.write(data)
            self._in_tasks.submit(self._in_task())
    
    async def read(self, length=None, *, flush=True):
        print("reading")
        if flush and len(self._out_buffer) > 0:
            print("flushing")
            # Flush the buffer, so that everything written before the read reaches the device.
            await self.flush(wait=False)

        if length is None and len(self._in_buffer) > 0:
            # Just return whatever is in the buffer.
            length = len(self._in_buffer)
        elif length is None:
            # Return whatever is received in the next transfer, even if it's nothing.
            # (Gateware doesn't normally submit zero-length packets, so, unless that changes
            # or customized gateware is used, we'll always get some data here.)
            self._in_stalls += 1
            await self._in_tasks.wait_one()
            length = len(self._in_buffer)
        else:
            # Return exactly the requested length.
            self._in_stalls += 1
            while len(self._in_buffer) < length:
                print("data_server: need %d bytes", length - len(self._in_buffer))
                logger.trace("data_server: need %d bytes", length - len(self._in_buffer))
                await self._in_tasks.wait_one()
        print("in pushback?")
        async with self._in_pushback:
            result = self._in_buffer.read(length)
            print(f'read result from in buffer')
            self._in_pushback.notify_all()
        print(f'len(result): {len(result)} < length: {length}?')
        if len(result) < length:
            chunks  = [result]
            length -= len(result)
            while length > 0:
                async with self._in_pushback:
                    chunk = self._in_buffer.read(length)
                    self._in_pushback.notify_all()
                chunks.append(chunk)
                length -= len(chunk)
            # Always return a memoryview object, to avoid hard to detect edge cases downstream.
            result = memoryview(b"".join(chunks))

        print("writing to socket", result.tolist()[0:10])
        self.writer.write(result)
        await self.writer.drain()
        return result

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
            await self.iface.write(data)
        finally:
            self._out_inflight -= len(data)

        if len(self._out_buffer) >= self._out_threshold:
            self._out_tasks.submit(self._out_task(self._out_slice()))

    async def write(self, length):
        if self.scan_mode != 3:
            print("BREAK, do not write")
        else:
            if self._write_buffer_size is not None:
                # If write buffer is bounded, and we have more inflight requests than the configured
                # write buffer size, then wait until the inflight requests arrive before continuing.
                if self._out_inflight >= self._write_buffer_size:
                    self._out_stalls += 1
                while self._out_inflight >= self._write_buffer_size:
                    logger.trace("data_server: write pushback")
                    print("write pushback")
                    await self._out_tasks.wait_one()

            # Eagerly check if any of our previous queued writes errored out.
            print("polling out tasks")
            await self._out_tasks.poll()

            #self.logger.trace("data_server: write <%s>", dump_hex(data))
            out_data = await self.reader.read(16384)
            print(f'read from socket', list(out_data)[0:10])
            print("write to out buffer")
            self._out_buffer.write(out_data)

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


class CmdServer:
    def __init__(self, host, port, process_cmd = None):
        self.HOST = host
        self.PORT = port
        self.queue = TaskQueue()
        if process_cmd == None:
            self.process_cmd = self.i_process_cmd
        else:
            self.process_cmd = process_cmd

    async def start(self):
        self.server = await asyncio.start_server(self.handle_cmd, self.HOST, self.PORT)
        await self.server.serve_forever()

    async def handle_cmd(self, reader, writer):
        self.cmd_reader = reader
        self.cmd_writer = writer
        # self.cmd_reader_future.set_result(reader)
        print("cmd server made connection")
        loop = asyncio.get_running_loop()

        while self.cmd_reader.at_eof() == False:
            try:
                print("awaiting cmd read")
                #print(self.cmd_reader)
                #print(vars(self.cmd_reader._transport))
                data = await self.cmd_reader.readexactly(7)
                message = data.decode()
                print("cmd:", message)
                self.queue.submit(self.process_cmd(message))
                print("waiting queue")
                await self.queue.wait_all()
                print("waited")
            except asyncio.IncompleteReadError:
                print("err")
    
    async def i_process_cmd(self, cmd):
        await asyncio.sleep(1)
        print("run cmd:",cmd)
        c = str(cmd[0:2])
        val = int(cmd[2:])
        if c == "sc":
            self.scan_mode = val
            self.iface.scan_mode = val
        if c == "ps":
            if val == 1:
                self.iface.paused.unlock()
                self.iface.paused.notify_all()
            if val == 0:
                self.iface.paused.acquire()

        


class ScanServers:
    def __init__(self, iface=None, process_cmd=None):
        self.cmd_server = CmdServer("127.0.0.1", 1237, process_cmd)
        self.data_server = DataServer("127.0.0.1", 1238, iface)
    
    def start(self, close_future):
        self.close_future = close_future
        loop = asyncio.get_event_loop()
        loop.create_task(self.data_server.reset())
        loop.create_task(self.cmd_server.start())
        loop.create_task(self.data_server.start())


if __name__ == "__main__":
    async def main():
        loop = asyncio.get_event_loop()
        close_future = loop.create_future()
        servers = ScanServers()
        servers.start(close_future)
        try:
            await close_future
        except Exception as err:
            print(f'close err: {err}')


    asyncio.run(main())

    

