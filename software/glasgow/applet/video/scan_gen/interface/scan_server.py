import asyncio
import functools
import sys


async def get_data():
    data = bytes([5]*16384)
    return data
    #future.set_result(data)

class ServerHost:
    def __init__(self, process_cmd, queue):
        self.streaming = None
        self.HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
        self.PORT = 1237  # Port to listen on (non-privileged ports are > 1023)
        self.queue = queue
        self.process_cmd = process_cmd


    def start_servers(self, data_server_future):
        self.data_server_future = data_server_future
        try:
            # self.cmd_reader_future = future
            loop = asyncio.get_event_loop()
            loop.create_task(self.start_cmd_server(self.HOST, self.PORT))
            loop.create_task(self.start_data_server(self.HOST, self.PORT+1))
        except Exception as e:
            print("error:", e)
    
    async def start_cmd_server(self, host, port):
        print("starting cmd server at", host, port)
        self.cmd_server = await asyncio.start_server(self.handle_cmd, host, port)
        await self.cmd_server.serve_forever()

    async def start_data_server(self, host, port):
        print("starting data server at", host, port)
        #self.streaming = True
        self.data_server = await asyncio.start_server(self.handle_data, host, port)
        await self.data_server.serve_forever()

    # async def stopdata(self):
    #     print("closing data writer")
    #     self.streaming.cancel()
    #     self.data_writer.close()
    #     await self.data_writer.wait_closed()

    async def handle_cmd(self, reader, writer):
        self.cmd_reader = reader
        self.cmd_writer = writer
        #loop = asyncio.get_running_loop()
        #self.cmd_server_closed_future = loop.create_future()
        #loop.create_task(self.read_cmds())
        

    
    #async def read_cmds(self):
        async def read_cmd():
            print("awaiting cmd read")
            data = await self.cmd_reader.readexactly(7)
            message = data.decode()
            print("cmd:", message)
            self.queue.submit(self.process_cmd(message))
            await self.queue.poll()
            #await self.process_cmd(message)

        #while True:
        try:
            await read_cmd()
            while len(self.cmd_reader._buffer) >= 7:
                print("reading additional cmds")
                await read_cmd()
        except asyncio.IncompleteReadError:
            print("unable to read 7 bytes from cmd stream")


    async def handle_data(self, reader, writer):
        self.data_reader = reader
        self.data_writer = writer
        print("data server made connection")
        addr = writer.get_extra_info('peername')
        print(f"addr: {addr!r}")
        self.data_server_future.set_result("done")
        

    # async def send_data_continously(self):
    #     while True:
    #         await self.write_data()

    # async def write_data(self):
    #     await asyncio.sleep(1)
    #     data = await get_data()
    #     print("sending data")
    #     self.data_writer.write(data)




# server_host = ServerHost()


def main():
    sys.path.append("/Users/isabelburgos/Scan-Gen-Glasgow-Testing/software")
    from glasgow.support.task_queue import TaskQueue
    queue = TaskQueue()
    loop = asyncio.get_event_loop()
    data_server_future = loop.create_future()
    def process_cmd(cmd):
        print("cmd:", cmd)
    server_host = ServerHost(queue, process_cmd)
    server_host.start_servers(data_server_future)
    loop.run_forever()

if __name__ == "__main__":
    main()