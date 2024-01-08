import threading
from time import sleep, perf_counter
import asyncio
from microscope import ScanCtrl
from encoding_test import ScanStream
import multiprocessing

class ConnectionProtocol(asyncio.Protocol):
    def __init__(self, connect_event, disconnect_future):
        self.connect_event = connect_event
        self.disconnect_future  = disconnect_future 

        self.transport = None
    
    def connection_made(self, transport):
        self.transport = transport
        #self.connect_event.set()
        print("connected")
    
    def connection_lost(self, exc):
        self.disconnect_future.set_result("done")
        print("connection lost")

    
    def write_data(self, data):
        self.transport.write(data)


class DataProtocol(ConnectionProtocol):
    def __init__(self, connect_event, disconnect_future, buf):
        super().__init__(connect_event, disconnect_future)
        #self.scan_stream = ScanStream()
        self.buf = buf
        
    
    def data_received(self, data):
        print(f'received {len(data)}')
        self.buf.extend(data)
        #self.transport.pause_reading()
        #self.pipe_end.send(data)
        #print(f'current thread: {threading.current_thread()}')
        #self.scan_stream.parse_config_from_data(data)

    
class ConnectionClient():
    def __init__(self, host, port, connect_event, disconnect_event):
        self.host = host
        self.port = port
        self.connect_event = connect_event
        self.disconnect_event = disconnect_event
        self.transport = None
        self.protocol = None
        

    async def open(self):
        print(f'opening {self.host} {self.port}')
        self.loop = asyncio.get_event_loop()
        self.disconnect_future = self.loop.create_future()
        try:
            transport, protocol = await self.create_connection(self.loop)
            self.transport = transport
            self.protocol = protocol
            print(f'got transport, {self.host}, {self.port}')
            self.transport.pause_reading()
            self.connect_event.set()
            await self.disconnect_future
        except ConnectionRefusedError:
            print("Could not make connection")
        finally:
            if not self.transport == None:
                self.transport.close()
            self.disconnect_event.set()

    async def create_connection(self, loop):
        transport, protocol = await self.loop.create_connection(
                lambda: ConnectionProtocol(self.connect_event, self.disconnect_future), 
                self.host, self.port)
        return transport, protocol


class DataConnectionClient(ConnectionClient):
    def __init__(self, host, port, connect_event, disconnect_event, pipe_end):
        super().__init__(host, port, connect_event, disconnect_event)
        self.pipe_end = pipe_end
        self.scan_stream = ScanStream()
    
    async def open(self):
        print(f'opening {self.host} {self.port}')
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
        print(f'got reader/writer {self.host} {self.port}')
        self.connect_event.set()
        print("data connect")
    
    # async def read(self, read_event):
    #     self.reader._transport.resume_reading()
    #     print("trying to read from data reader...")
    #     print(f'{self.reader}')
    #     data = await self.reader.read(16384)
    #     self.reader._transport.pause_reading()
    #     print(f'data received {len(data)}')
    #     self.scan_stream.parse_config_from_data(data)
    #     read_event.set()

    async def read_continously(self):
        while True:
            try:
                if not self.reader.at_eof():
                    await asyncio.sleep(0)
                    data = await self.reader.read(16384)
                    self.scan_stream.parse_config_from_data(data)
                else:
                    print("at eof")
                    break
            except Exception as err:
                print(f'error: {err}')
                break

    
    # async def create_connection(self, loop):
    #     print(f'trying to connect {self.host} {self.port}')
    #     transport, protocol = await loop.create_connection(
    #             lambda: DataProtocol(self.connect_event, self.disconnect_future, self.pipe_end), 
    #             self.host, self.port)
    #     return transport, protocol

class ConnectionManager:
    def __init__(self, cmd_connect_event, data_connect_event,
                    cmd_disconnect_event, data_disconnect_event, pipe_end):
        self.cmd_connect_event = cmd_connect_event
        self.data_connect_event = data_connect_event
        self.cmd_disconnect_event = cmd_disconnect_event
        self.data_disconnect_event = cmd_disconnect_event

        self.cmd_client = ConnectionClient("127.0.0.1", 1237, self.cmd_connect_event, self.cmd_disconnect_event)
        self.data_client = DataConnectionClient("127.0.0.1",1238, self.data_connect_event, self.data_disconnect_event, pipe_end)
    async def start(self):
        await asyncio.gather(self.cmd_client.open(), self.data_client.open())




# def open_data_client(connect_event, disconnect_event, other_pipe_end):
#     data_client = DataConnectionClient("127.0.0.1",1238, connect_event, disconnect_event, other_pipe_end)
#     loop = asyncio.get_event_loop()
#     loop.run_until_complete(data_client.open())



class ConnThreadManager:
    def __init__(self):
        self.buf = bytearray(16384)

        self.cmd_connect_event = threading.Event()
        self.data_connect_event = threading.Event()
        self.cmd_disconnect_event = threading.Event()
        self.data_disconnect_event = threading.Event()

        # self.con = ConnectionManager(self.cmd_connect_event, self.data_connect_event,
        #     self.cmd_disconnect_event, self.data_disconnect_event, other_pipe_end)

        self.cmd_client = ConnectionClient("127.0.0.1", 1237, self.cmd_connect_event, self.cmd_disconnect_event)
        self.data_client = DataConnectionClient("127.0.0.1",1238, self.data_connect_event, self.data_disconnect_event, self.buf)

    async def open_clients(self):
        #loop = asyncio.new_event_loop()
        await asyncio.gather(self.cmd_client.open(),
            self.data_client.open())
    
    def open(self):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self.open_clients(loop))

    async def start(self):
        print("waiting for connection...")

        #t = threading.Thread(target = self.open)
        #t.start()
        await self.open_clients()
        # loop = asyncio.get_event_loop()
        # loop.create_task(self.cmd_client.open())
        # loop.create_task(self.data_client.open())
        print("thread started")
        self.cmd_connect_event.wait()
        print("cmd connected")
        self.data_connect_event.wait()
        print("connected!!")
        self.data_client.loop.create_task(self.data_client.read_continously())

    def sendcmd(self, cmd):
        print(f'sending cmd: {cmd}')
        #s = threading.Thread(target = self.cmd_client.protocol.write_data, args = [cmd.encode()])
        #s.start()
        self.cmd_client.protocol.write_data(cmd.encode())


class ScanInterface(ConnThreadManager):
    def __init__(self):
        super().__init__()
        self.scan_ctrl = ScanCtrl()
        self.scan_stream = ScanStream()
        self.buffer = self.data_client.scan_stream.buffer

        
    def strobe_config(self):
        self.sendcmd(self.scan_ctrl.raise_config_flag())
        self.sendcmd(self.scan_ctrl.lower_config_flag())

    def set_x_resolution(self, xval):
        self.sendcmd(self.scan_ctrl.set_x_resolution(xval))

    def set_y_resolution(self, yval):
        self.sendcmd(self.scan_ctrl.set_y_resolution(yval))

    def set_dwell_time(self, dval):
        self.sendcmd(self.scan_ctrl.set_dwell_time(dval))

    def set_scan_mode(self, mode):
        self.sendcmd(self.scan_ctrl.set_scan_mode(mode))
        # self.data_client.scan_mode = mode
        # if mode == 3:
        #     self.data_client.write_pattern()

    def set_8bit_output(self):
        self.sendcmd(self.scan_ctrl.set_8bit_output())
    
    def set_16bit_output(self):
        self.sendcmd(self.scan_ctrl.set_16bit_output())
    
    def pause(self):
        self.sendcmd(self.scan_ctrl.pause())
        #self.con.data_client.transport.pause_reading()


    def unpause(self):
        self.sendcmd(self.scan_ctrl.unpause())
        #self.data_client.transport.resume_reading()


    def set_ROI(self, x_upper, x_lower, y_upper, y_lower):
        self.sendcmd(self.scan_ctrl.set_ROI(x_upper, x_lower, y_upper, y_lower))


    def read(self, read_event):
        #print("creating task")
        #print(f'{self.data_client.reader}')
        asyncio.ensure_future(self.data_client.read_continously)

        
        
        
        
    

class UI:
    def __init__(self):
        self.con = ScanInterface()
        
    # def connect(self):
    #     self.con.start()
    def raster(self):
        print("setting resolution")
        self.con.set_x_resolution(512)
        self.con.set_y_resolution(512)
        self.con.set_scan_mode(1)
        self.con.strobe_config()
        self.con.unpause()
    async def showdata(self):
        while True:
            print("SHOWING DATA")
            await asyncio.sleep(0)
            print(self.con.buffer)






if __name__ == "__main__":
    async def main():
        print(f'start! current thread: {threading.current_thread()}')
        ui = UI()
        await ui.con.start()
        ui.raster()
        print("SHOW DATA")
        # ui.con.read()
        #ui.showdata()

        asyncio.ensure_future(ui.showdata())
        await asyncio.sleep(5)
        ui.con.pause()
            
            
    asyncio.run(main())
