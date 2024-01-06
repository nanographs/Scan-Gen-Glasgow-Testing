import threading
from time import sleep, perf_counter
import asyncio

class ConnectionProtocol(asyncio.Protocol):
    def __init__(self, connect_event, disconnect_future):
        self.connect_event = connect_event
        self.disconnect_future  = disconnect_future 

        self.transport = None
    
    def connection_made(self, transport):
        self.transport = transport
        self.connect_event.set()
        print("connected")
    
    def connection_lost(self, exc):
        self.disconnect_future.set_result("done")
        print("connection lost")

    def data_recieved(self, data):
        print(f'recieved {len(data)}')
    
    def write_data(self, data):
        self.transport.write(data)
    
class ConnectionClient():
    def __init__(self, host, port, connect_event, disconnect_event):
        self.host = host
        self.port = port
        self.connect_event = connect_event
        self.disconnect_event = disconnect_event
        self.transport = None

    async def open(self):
        loop = asyncio.get_event_loop()
        self.disconnect_future = loop.create_future()
        try:
            transport, protocol = await loop.create_connection(
                lambda: ConnectionProtocol(self.connect_event, self.disconnect_future), 
                self.host, self.port)
            self.transport = transport
            print("got transport")
            await self.disconnect_future
        except ConnectionRefusedError:
            print("Could not make connection")
        finally:
            if not self.transport == None:
                self.transport.close()
            self.disconnect_event.set()

class ConnectionManager:
    def __init__(self, connect_event, disconnect_event):
        self.connect_event = connect_event
        self.disconnect_event = disconnect_event

        loop = asyncio.new_event_loop()
        self.data_con_lost = loop.create_future()
        self.cmd_con_lost = loop.create_future()

        self.cmd_client = ConnectionClient("127.0.0.1", 1237, connect_event, disconnect_event)
        self.data_client = ConnectionClient("127.0.0.1",1238, connect_event, disconnect_event)
    async def start(self):
        await self.cmd_client.open()
        await self.data_client.open()



def conthread(connect_event, disconnect_event):
    con = ConnectionManager(connect_event, disconnect_event)
    asyncio.run(con.start())

class UI:
    def __init__(self):
        self.connect_event = threading.Event()
        self.disconnect_event = threading.Event()

    def start(self):
        t = threading.Thread(target = conthread, args = [self.connect_event, self.disconnect_event])
        t.start()
        print("waiting for connection...")
        self.connect_event.wait()
        print("connected!!")
        t.join()
        print("thread done")


ui = UI()
ui.start()
