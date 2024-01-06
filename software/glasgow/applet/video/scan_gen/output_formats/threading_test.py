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
    def __init__(self, connect_event, disconnect_future):
        super().__init__(connect_event, disconnect_future)
        self.scan_stream = ScanStream()
    
    def data_received(self, data):
        print(f'received {len(data)}')
        print(f'current thread: {threading.current_thread()}')
        self.scan_stream.parse_config_from_data(data)
    
class ConnectionClient():
    def __init__(self, host, port, protocol_type, connect_event, disconnect_event):
        self.host = host
        self.port = port
        self.protocol_type = protocol_type
        self.connect_event = connect_event
        self.disconnect_event = disconnect_event
        self.transport = None
        self.protocol = None
        

    async def open(self):
        print(f'opening {self.host} {self.port}')
        loop = asyncio.get_event_loop()
        self.disconnect_future = loop.create_future()
        try:
            transport, protocol = await loop.create_connection(
                lambda: self.protocol_type(self.connect_event, self.disconnect_future), 
                self.host, self.port)
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

class ConnectionManager:
    def __init__(self, cmd_connect_event, data_connect_event,
                    cmd_disconnect_event, data_disconnect_event):
        self.cmd_connect_event = cmd_connect_event
        self.data_connect_event = data_connect_event
        self.cmd_disconnect_event = cmd_disconnect_event
        self.data_disconnect_event = cmd_disconnect_event

        self.cmd_client = ConnectionClient("127.0.0.1", 1237, ConnectionProtocol, self.cmd_connect_event, self.cmd_disconnect_event)
        self.data_client = ConnectionClient("127.0.0.1",1238, DataProtocol, self.data_connect_event, self.data_disconnect_event)
    async def start(self):
        await asyncio.gather(self.cmd_client.open(), self.data_client.open())



def conthread(con):
    loop = asyncio.new_event_loop()
    loop.run_until_complete(con.start())


class ConnThreadManager:
    def __init__(self):
        self.cmd_connect_event = multiprocessing.Event()
        self.data_connect_event = multiprocessing.Event()
        self.cmd_disconnect_event = multiprocessing.Event()
        self.data_disconnect_event = multiprocessing.Event()

        self.con = ConnectionManager(self.cmd_connect_event, self.data_connect_event,
            self.cmd_disconnect_event, self.data_disconnect_event)

    def start(self):
        t = multiprocessing.Process(target = conthread, args = [self.con])
        t.start()
        print("waiting for connection...")
        self.cmd_connect_event.wait()
        print("cmd connected")
        self.data_connect_event.wait()
        print("connected!!")
        self.buffer = self.con.data_client.protocol.scan_stream.buffer

    def sendcmd(self, cmd):
        print(f'sending cmd: {cmd}')
        print(f'data client: {self.con.data_client.transport}')
        s = multiprocessing.Process(target = self.con.cmd_client.protocol.write_data, args = [cmd.encode()])
        s.start()


class ScanInterface(ConnThreadManager):
    def __init__(self):
        super().__init__()
        self.scan_ctrl = ScanCtrl()
        

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
        self.con.data_client.transport.pause_reading()


    def unpause(self):
        self.sendcmd(self.scan_ctrl.unpause())
        print(f'data client: {self.con.data_client.transport}')
        self.con.data_client.transport.resume_reading()


    def set_ROI(self, x_upper, x_lower, y_upper, y_lower):
        self.sendcmd(self.scan_ctrl.set_ROI(x_upper, x_lower, y_upper, y_lower))


class UI:
    def __init__(self):
        self.con = ScanInterface()
    def connect(self):
        self.con.start()
    def raster(self):
        print("setting resolution")
        self.con.set_x_resolution(512)
        self.con.set_y_resolution(512)
        self.con.set_scan_mode(1)
        self.con.strobe_config()
        self.con.unpause()


if __name__ == "__main__":
    async def main():
        print(f'start! current thread: {threading.current_thread()}')
        ui = UI()
        ui.connect()
        ui.raster()
        await asyncio.sleep(2)
        print("WAKEUP")
        for n in range(10):
            print(f'n: {n} current thread: {threading.current_thread()}')
            print(ui.con.buffer)
            await asyncio.sleep(0)
    
    asyncio.run(main())
