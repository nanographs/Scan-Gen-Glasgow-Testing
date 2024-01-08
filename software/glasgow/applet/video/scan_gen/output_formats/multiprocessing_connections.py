import multiprocessing
import asyncio

class ThreadConnectionProtocol(asyncio.Protocol):
    def __init__(self, pipe=None):
        self.transport = None
        self.pipe = pipe
    
    def connection_made(self, transport):
        self.transport = transport
        #self.connect_event.set()
        print("connected")
    
    def connection_lost(self, exc):
        self.disconnect_future.set_result("done")
        print("connection lost")

    def data_received(self,data):
        print(f'received {len(data)}')
        self.pipe.send(data)

    def write_data(self, data):
        self.transport.write(data)


async def open_connection_multi(pipe_conn=None):
    loop = asyncio.get_event_loop()
    close_future = loop.create_future()
    transport, protocol = await loop.create_connection(
        lambda: ThreadConnectionProtocol(pipe_conn), 
        "127.0.0.1", 1238)
    await close_future
    

def run(pipe_conn=None):
    asyncio.run(open_connection_multi(pipe_conn))

def receiver(connection):
    while True:
        data = connection.recv()
        print(f'other side received {len(data)}')

if __name__ == "__main__":
    conn1, conn2 = multiprocessing.Pipe(duplex=True)
    p = multiprocessing.Process(target=run, args = [conn1])
    p2 = multiprocessing.Process(target=receiver, args = [conn2])
    print("start process")
    p.start()
    p2.start()
    p.join()
    p2.join()

