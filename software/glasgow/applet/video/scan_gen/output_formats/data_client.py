import asyncio
import sys
sys.path.append("/Users/isabelburgos/Scan-Gen-Glasgow-Testing/software")
from glasgow.support.task_queue import TaskQueue
from glasgow.support.chunked_fifo import ChunkedFIFO

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

logging.basicConfig(filename='otherlogs.txt', filemode='w', level=logging.DEBUG)



class ConnectionClient:
    async def open_connection(self, future):
        host = self.host
        port = self.port
        print("trying to open connection at", host, port)
        while True:
            try:
                reader, writer = await asyncio.open_connection(
                    host, port)
                print("connection made")
                addr = writer.get_extra_info('peername')
                print(f"addr: {addr!r}")
                future.set_result([reader,writer])
                break
            except ConnectionError:
                #print("connection error")
                pass


_max_packets_per_ep = 1024
_packets_per_xfer = 32
_xfers_per_queue = min(16, _max_packets_per_ep // _packets_per_xfer)


class DataClient(ConnectionClient):
    def __init__(self):
        self.host = "127.0.0.1"
        self.port = 1238


        self._write_buffer_size = _max_packets_per_ep * 16384
        self._read_buffer_size  = _max_packets_per_ep * 16384
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

    async def open(self, future_con):
        print("opening data client")
        loop = asyncio.get_event_loop()
        loop.create_task(self.open_connection(future_con))
        await asyncio.sleep(0)
        reader, writer = await future_con
        self.writer = writer
        self.reader = reader
        print(reader)
        print(vars(reader))
        print(writer)
        print(vars(writer))


    async def cancel(self):
        if self._in_tasks or self._out_tasks:
            logger.trace("data_client: cancelling operations")
            await self._in_tasks .cancel()
            await self._out_tasks.cancel()

    async def reset(self):
        await self.cancel()

        logger.trace("data_client: asserting reset")
        logger.trace("data_client: synchronizing buffers")
        self._in_buffer .clear()
        self._out_buffer.clear()

        # Pipeline reads
        logger.trace("data_client: pipelining reads")
        print("pipelining reads")
        for _ in range(_xfers_per_queue):
            self._in_tasks.submit(self._in_task())
        # Give the IN tasks a chance to submit their transfers
        await asyncio.sleep(0)
        print(f'in tasks: {vars(self._in_tasks)}')
        logger.trace("data_client: deasserting reset")

    async def _in_task(self):
        if self._read_buffer_size is not None:
            async with self._in_pushback:
                while len(self._in_buffer) > self._read_buffer_size:
                    logger.trace("data_client: read pushback")
                    await self._in_pushback.wait()

        size = self._in_packet_size * _packets_per_xfer
        data = await self.reader.read(size)
        self._in_buffer.write(data)

        self._in_tasks.submit(self._in_task())

    async def read_continously(self):
        while True:
            print("reading")
            data = await self.read()
            print(f'read {len(data)}')
    
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
            print("return exactly")
            # Return exactly the requested length.
            self._in_stalls += 1
            while len(self._in_buffer) < length:
                print("data_client: need %d bytes", length - len(self._in_buffer))
                print(f'in tasks: {self._in_tasks}')
                logger.trace("data_client: need %d bytes", length - len(self._in_buffer))
                await self._in_tasks.wait_one()
        print("in pushback?")
        async with self._in_pushback:
            print(f'in pushback:{vars(self._in_pushback)}')
            result = self._in_buffer.read(length)
            print(f'result: {result}')
            self._in_pushback.notify_all()
        print(f'len(result): {len(result)} < length: {length}?')
        if len(result) < length:
            print("yes")
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

        print("returning result")
        #logger.trace("data_client: read <%s>", dump_hex(result))
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
            self.writer.write(data)
            await self.writer.drain()
        finally:
            self._out_inflight -= len(data)

        if len(self._out_buffer) >= self._out_threshold:
            self._out_tasks.submit(self._out_task(self._out_slice()))

    async def write(self, data):
        if self._write_buffer_size is not None:
            # If write buffer is bounded, and we have more inflight requests than the configured
            # write buffer size, then wait until the inflight requests arrive before continuing.
            if self._out_inflight >= self._write_buffer_size:
                self._out_stalls += 1
            while self._out_inflight >= self._write_buffer_size:
                logger.trace("data_client: write pushback")
                await self._out_tasks.wait_one()

        # Eagerly check if any of our previous queued writes errored out.
        await self._out_tasks.poll()

        self.logger.trace("data_client: write <%s>", dump_hex(data))
        self._out_buffer.write(data)

        while len(self._out_tasks) < _xfers_per_queue and \
                    len(self._out_buffer) >= self._out_threshold:
            self._out_tasks.submit(self._out_task(self._out_slice()))
    

    async def flush(self, wait=True):
        logger.trace("data_client: flush")

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
            logger.trace("data_client: wait for flush")
            if self._out_tasks:
                self._out_stalls += 1
            while self._out_tasks:
                await self._out_tasks.wait_all()



if __name__ == "__main__":
    async def main():
        data_client = DataClient("127.0.0.1",1238)
        await data_client.open()
        await data_client.reset()
        #await data_client.read(16)

    asyncio.run(main())