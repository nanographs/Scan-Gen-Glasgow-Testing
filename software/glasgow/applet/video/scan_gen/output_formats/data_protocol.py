import asyncio
import sys
# sys.path.append("/Users/isabelburgos/Scan-Gen-Glasgow-Testing/software")
# from glasgow.support.aobject import aobject


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

    def data_received(self, data):
        print("received", len(data))
        print(list(data)[0:10])
        self.write_pattern()

    def write_pattern(self):
        data = bytes([6]*16384)
        self._transport.write(data)
        print("wrote data")

class ScanCmdClient(ScanClient):
    def __init__(self, on_con_lost):
        super().__init__(on_con_lost)

    def write_cmd(self, cmd):
        self._transport.write(cmd.encode())


class ConnectionClient:
    def __init__(self, close_future):
        self.close_future = close_future
        loop = asyncio.get_event_loop()
        self.data_con_lost = loop.create_future()
        self.cmd_con_lost = loop.create_future()
    
    async def start(self):
        loop = asyncio.get_event_loop()
        loop.create_task(self.open_cmd_client())
        loop.create_task(self.open_data_client())


    async def open_data_client(self):
        loop = asyncio.get_event_loop()
        transport, protocol = await loop.create_connection(
            lambda: ScanDataClient(self.data_con_lost), 
            "127.0.0.1",1238)
        try:
            await self.data_con_lost
        except ConnectionRefusedError:
            print("Could not make connection")
        finally:
            transport.close()
    
    async def open_cmd_client(self):
        loop = asyncio.get_event_loop()
        transport, protocol = await loop.create_connection(
            lambda: ScanDataClient(self.cmd_con_lost), 
            "127.0.0.1",1237)
        try:
            await self.cmd_con_lost
        except ConnectionRefusedError:
            print("Could not make connection")
        finally:
            transport.close()
    
    

if __name__ == "__main__":
    async def main():
        loop = asyncio.get_event_loop()
        close_future = loop.create_future()
        con = ConnectionClient(close_future)
        await con.start()
        await close_future
        
        
    asyncio.run(main())