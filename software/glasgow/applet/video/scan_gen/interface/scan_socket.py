import asyncio

if __name__ == "interface.scan_socket":
    import sys
    import os
    path = os.path.split(sys.path[0])[0]
    sys.path.append(path)
    from interface.scan_ctrl import ScanCtrl
    from interface.scan_stream import ScanStream

else:
    from scan_ctrl import ScanCtrl
    from scan_stream import ScanStream
    from ..pattern_generators.patterngen_utils import packet_from_generator

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

logging.basicConfig(filename='otherlogs.txt', filemode='w', level=logging.DEBUG)

import time


class ConnectionManager:
    def __init__(self):
        self.scan_stream = ScanStream()
        self.scan_ctrl = ScanCtrl()

        self.data_writer = None
        self.data_reader = None

        self.stream_pattern = False

        self.scan_mode = 0

        self.pattern_loop = None
        self.pattern_done = False

        # self.text_file = open("socket_packets.txt", "w")

        self.logging = False

    async def open_connection(self, host, port, future):
        #print("trying to open connection at", host, port)
        while True:
            try:
                reader, writer = await asyncio.open_connection(
                    host, port)
                addr = writer.get_extra_info('peername')
                #print(f"addr: {addr!r}")
                future.set_result([reader,writer])
                break
            except ConnectionError:
                self.pattern_done = True
                #print("connection error")
                pass
    
    def set_patterngen(self, gen):
        print(f'gen: {gen}')
        self.pattern_loop = packet_from_generator(gen)
        print(f'pattern loop: {self.pattern_loop}')
        self.pattern_done = False


    async def write_points(self,nth, print_debug = True):
        if print_debug:
            print(f'writing points {nth}')
        try:
            points = next(self.pattern_loop)
            next_points = next(self.pattern_loop)
            next_next_points = next(self.pattern_loop)
            # while True:
            #     try:
            self.data_writer.write(points)
            self.data_writer.write(next_points)
            self.data_writer.write(next_next_points)
            await self.data_writer.drain()
            if self.logging:
                print(f'wrote points {nth}')
                self.text_file.write("=====Sent=====\n")
                self.text_file.write(str(list(points)))
            logger.info(f'wrote points {nth}')
                # except Exception as err:
                #     print(f'done writing points: {err}')
                #     break
            return "done2"
        except Exception as err: ## should be StopIteration
            print(f'Pattern complete')
            return "done"

    async def read_continously(self, print_debug = True):
        reader = self.data_reader
        writer = self.data_writer
        n = 0
        while True:
            try:
                if print_debug:
                    print("trying to read")
                if not reader.at_eof():
                    if self.stream_pattern == True:
                        if not self.pattern_done == True:
                            r = await self.write_points(n)
                            print("result", r)
                    await asyncio.sleep(0)
                    data = await reader.readexactly(16384)
                    n += 1
                    if print_debug:
                        print(f'recieved data {n}')
                    logger.info(f'recieved data {n}, length {len(data)}')
                    if self.logging:
                        self.text_file.write("=====Received=====\n")
                        self.text_file.write(str(list(data)))
                        logger.info(f'wrote data {n} to text file')
                    self.scan_stream.writeto(data)

                else:
                    print("at eof?")
                    print(reader)
                    break
            except StopIteration:
                print(f'STOPPED 2, {self.pattern_done}')
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
        self.data_reader, self.data_writer = await future_con
        await self.start_reading()

    async def open_cmd_client(self):
        host = "127.0.0.1"  # Standard loopback interface address (localhost)
        port = 1237  # Port to listen on (non-privileged ports are > 1023)
        print("opening data client")
        loop = asyncio.get_event_loop()
        future_con = loop.create_future()
        loop.create_task(self.open_connection(host, port, future_con))
        await asyncio.sleep(0)
        self.cmd_reader, self.cmd_writer = await future_con
        #await self.start_reading()

    async def cmd_client(self, message, print_debug = True):
        HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
        PORT = 1237  # Port to listen on (non-privileged ports are > 1023)
        loop = asyncio.get_event_loop()
        future_con = loop.create_future()
        loop.create_task(self.open_connection(HOST, PORT, future_con))
        await asyncio.sleep(0)
        reader, writer = await future_con
        if print_debug:
            print(f'Send: {message!r}')
        writer.write(message.encode())
        await writer.drain()
        if print_debug:
            print("sent")

    async def start_reading(self):
        print("start reading")
        self.streaming = asyncio.ensure_future(self.read_continously())


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

    async def set_dwell_time(self, dval):
        await self.cmd_client(self.scan_ctrl.set_dwell_time(dval))

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

    async def set_ROI(self, x_upper, x_lower, y_upper, y_lower):
        await self.cmd_client(self.scan_ctrl.set_ROI(x_upper, x_lower, y_upper, y_lower))




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