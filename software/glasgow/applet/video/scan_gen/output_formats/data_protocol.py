import asyncio
import sys
# sys.path.append("/Users/isabelburgos/Scan-Gen-Glasgow-Testing/software")
# from glasgow.support.aobject import aobject

class DataClient(asyncio.Protocol):
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

    def data_received(self, data):
        print("received", len(data))
        print(data)


if __name__ == "__main__":
    async def main():
        
        loop = asyncio.get_event_loop()
        on_con_lost = loop.create_future()
        transport, protocol = await loop.create_connection(
            lambda: DataClient(on_con_lost), 
            "127.0.0.1",1238)
        
        try:
            await on_con_lost
        finally:
            transport.close()
    
    asyncio.run(main())