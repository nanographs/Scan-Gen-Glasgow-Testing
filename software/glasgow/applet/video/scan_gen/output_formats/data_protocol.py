import asyncio
import sys
# sys.path.append("/Users/isabelburgos/Scan-Gen-Glasgow-Testing/software")
# from glasgow.support.aobject import aobject

from microscope import ScanCtrl
from tests import generate_vector_packet


class ScanClient(asyncio.Protocol):
    def __init__(self, on_con_lost):
        self._transport = None
        self._new_transport = None
        self.on_con_lost = on_con_lost

    def connection_made(self, transport):
        peername = transport.get_extra_info("peername")
        if peername:
            print("new connection from:", *peername[0:2])
        else:
            print("new connection")

        if self._transport is None:
            self._transport = transport
        else:
            print("closing old connection")
            self._transport.close()
            self._new_transport = transport

    def connection_lost(self, exc):
        print("server closed connection")
        self.on_con_lost.set_result(True)


class ScanDataClient(ScanClient):
    def __init__(self, on_con_lost):
        super().__init__(on_con_lost)
        self.streaming = True
        self.patterning = True
        self.scan_mode = 0
        self.patterngen = generate_vector_packet()

    def data_received(self, data):
        print("received", len(data))
        print(list(data)[0:10])
        if self.scan_mode == 3:
            self.write_pattern()

    def write_pattern(self):
        #data = bytes([6]*16384)
        data = bytes(next(self.patterngen))
        self._transport.write(data)
        print("wrote data")

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
        print(f'transport: {transport}')
        print(f'protocol: {protocol}')
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
        con.set_x_resolution(400)
        con.set_y_resolution(400)
        con.set_scan_mode(1)
        con.strobe_config()
        con.unpause()
        await asyncio.sleep(5)
        con.pause()
        con.set_x_resolution(1024)
        con.set_y_resolution(1024)
        con.set_scan_mode(3)
        con.strobe_config()
        con.unpause()
        # await asyncio.sleep(10)
        # con.pause()
        await close_future
        
        
    asyncio.run(main())