import asyncio

from microscope import ScanCtrl
from encoding_test import ScanStream

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

logging.basicConfig(filename='otherlogs.txt', filemode='w', level=logging.DEBUG)

from hilbert_test import hilbert
import time


def get_two_bytes(n: int):
    bits = "{0:016b}".format(n)
    b1 = int(bits[0:8], 2)
    b2 = int(bits[8:16], 2)
    return b1, b2


class ConnectionManager:
    def __init__(self):
        self.scan_stream = ScanStream()
        self.scan_ctrl = ScanCtrl()

        self.data_writer = None
        self.data_reader = None

        self.stream_pattern = False

        self.scan_mode = 0

        #self.pattern_loop = self.loop_pattern()
        self.pattern_loop = hilbert()

        self.text_file = open("socket_packets.txt", "w")

        self.logging = False

    def looppattern(self):
        L = [255, 255, 10, 100, 100, 10, 250, 100, 10, 200, 200, 10, 150, 150, 10, 100, 150, 10,
            230, 220, 10, 50, 10, 10]
        def gentr_fn(alist):
            while 1:
                for j in alist:
                    yield j

        a = gentr_fn(L)
        return a

    async def open_connection(self, host, port, future):
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

    async def write_2bytes(self, val):
        writer = self.data_writer
        b1, b2 = get_two_bytes(val)
        writer.write(b2.to_bytes())
        await writer.drain()
        writer.write(b1.to_bytes())
        await writer.drain()

    async def write_points(self):
        writer = self.data_writer
        print("writing points")
        n = 0
        while n <= 16384:
            n += 1
            point = next(self.pattern_loop)
            await self.write_2bytes(point)
        print("wrote", n)

    async def read_continously(self):
        reader = self.data_reader
        writer = self.data_writer
        n = 0
        while True:
            try:
                print("trying to read")
                if not reader.at_eof():
                    if self.stream_pattern == True:
                        await self.write_points()
                    await asyncio.sleep(0)
                    data = await reader.read(16384)
                    n += 1
                    print(f'recieved data {n}')
                    logger.info(f'recieved data {n}, length {len(data)}')
                    if self.logging:
                        self.text_file.write(str(list(data)))
                        logger.info(f'wrote data {n} to text file')
                    self.scan_stream.parse_config_from_data(data)

                    

                else:
                    print("at eof?")
                    print(reader)
                    break
            except Exception as e:
                print("error:", e, type(e), vars(e))
                print(reader)
                if self.logging:
                    logging.debug("continous read error" + repr(reader))
                break

    async def open_data_client(self):
        host = "127.0.0.1"  # Standard loopback interface address (localhost)
        port = 1238  # Port to listen on (non-privileged ports are > 1023)
        print("opening data client")
        loop = asyncio.get_event_loop()
        future_con = loop.create_future()
        loop.create_task(self.open_connection(host, port, future_con))
        await asyncio.sleep(0)
        reader, writer = await future_con
        self.data_writer = writer
        self.data_reader = reader
        await self.start_reading()

    async def cmd_client(self, message):
        HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
        PORT = 1237  # Port to listen on (non-privileged ports are > 1023)
        print("opening cmd client")
        loop = asyncio.get_event_loop()
        future_con = loop.create_future()
        loop.create_task(self.open_connection(HOST, PORT, future_con))
        await asyncio.sleep(0)
        reader, writer = await future_con
        print(f'Send: {message!r}')
        writer.write(message.encode())
        await writer.drain()
        print("sent")

        # print('Close tcp_msg_client')
        # writer.close()
        # await writer.wait_closed()

    async def wait_stop(self):
        await asyncio.sleep(10)
        await self.stop_reading()
        await asyncio.sleep(1)
        await self.start_reading()
        await asyncio.sleep(10)
        await self.stop_reading()

    async def start_reading(self):
        print("start reading")
        self.streaming = asyncio.ensure_future(self.read_continously())
    
    async def close_data_stream(self):
        print('Close data stream')
        self.data_writer.close()
        await self.data_writer.wait_closed()


class ScanInterface(ConnectionManager):
    def __init__(self):
        super().__init__()

    async def strobe_config(self):
        await self.cmd_client(self.scan_ctrl.raise_config_flag())
        await self.cmd_client(self.scan_ctrl.lower_config_flag())

    async def set_x_resolution(self, xval):
        await self.cmd_client(self.scan_ctrl.set_x_resolution(xval))

    async def set_y_resolution(self, yval):
        await self.cmd_client(self.scan_ctrl.set_y_resolution(yval))

    async def set_scan_mode(self, mode):
        self.scan_mode = mode
        await self.cmd_client(self.scan_ctrl.set_scan_mode(mode))

    async def set_8bit_output(self):
        await self.cmd_client(self.scan_ctrl.set_8bit_output())
    
    async def set_16bit_output(self):
        await self.cmd_client(self.scan_ctrl.set_16bit_output())
    
    async def pause(self):
        await self.cmd_client(self.scan_ctrl.pause())

    async def unpause(self):
        await self.cmd_client(self.scan_ctrl.unpause())




async def main():
    con = ScanInterface()
    con.logging = True

    async def raster_test():
        await con.set_x_resolution(400)
        await con.set_y_resolution(400)
        await con.set_scan_mode(1)
        await con.strobe_config()
        await con.open_data_client()
        await con.unpause()

    async def vector_test():
        await con.set_x_resolution(1024)
        await con.set_y_resolution(1024)
        await con.set_scan_mode(3)
        await con.strobe_config()
        con.stream_pattern = True
        await con.open_data_client()
        await con.unpause()
        
        #await con.write_points()

    await vector_test()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    loop.run_forever()