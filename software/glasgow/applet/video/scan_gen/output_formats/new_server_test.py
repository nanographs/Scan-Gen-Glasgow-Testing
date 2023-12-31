import asyncio
import functools
import sys


class fake_iface:
    def __init__(self):
        self.paused = False
        self.scan_mode = 0
    async def read(self):
        if not self.paused:
            data = bytes([5]*16384)
            await asyncio.sleep(1)
            return data
    async def write(self, data):
        if not self.paused:
            await asyncio.sleep(1)
            print("wrote data")

iface = fake_iface()      


class ServerHost:
    def __init__(self, queue, process_cmd=None):
        self.streaming = None
        self.HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
        self.PORT = 1237  # Port to listen on (non-privileged ports are > 1023)
        self.queue = queue
        if process_cmd == None:
            self.process_cmd = self.i_process_cmd
        else:
            self.process_cmd = process_cmd
        self.scan_mode = 0


    def start_start_servers(self, close_future):
        self.close_future = close_future
        loop = asyncio.get_event_loop()
        self.data_server_future = loop.create_future()
        self.start_servers(self.data_server_future)
        self.streaming = asyncio.ensure_future(self.stream_data())


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

    async def stopdata(self):
        print("closing data writer")
        self.streaming.cancel()
        self.data_writer.close()
        await self.data_writer.wait_closed()

    async def handle_cmd(self, reader, writer):
        self.cmd_reader = reader
        self.cmd_writer = writer
        # self.cmd_reader_future.set_result(reader)
        print("cmd server made connection")
        loop = asyncio.get_running_loop()
        try:
            print("awaiting cmd read")
            data = await self.cmd_reader.readexactly(7)
            message = data.decode()
            print("cmd:", message)
            self.queue.submit(self.process_cmd(message))
            await self.queue.poll()
        except asyncio.IncompleteReadError:
            print("err")


    async def handle_data(self, reader, writer):
        self.data_reader = reader
        self.data_writer = writer
        print("data server made connection")
        addr = writer.get_extra_info('peername')
        print(f"addr: {addr!r}")
        self.data_server_future.set_result("done")
        

    async def send_data_continously(self):
        while True:
            await self.write_data()

    async def write_data(self):
        await asyncio.sleep(1)
        data = await get_data()
        print("sending data")
        self.data_writer.write(data)

    async def recv_packet(self):
        print("standing by to recieve packet...")
        await self.data_server_future
        print("reading from server")
        try:
            data = await self.data_reader.readexactly(16384)
            print(type(data))
            print("recieved points!", len(data))
            await iface.write(data)
        except Exception as err:
            print(f'error: {err}')


    async def stream_data(self):
        n = 0
        while True:
            n += 1
            if self.scan_mode == 3:
                await self.recv_packet()
            data = await iface.read(data)
            self.data_writer.write(data)
            await self.data_writer.drain()

    async def i_process_cmd(self, cmd):
        print("run cmd:",cmd)
        c = str(cmd[0:2])
        val = int(cmd[2:])
        if c == "sc":
            self.scan_mode = val
            iface.scan_mode = val
        if c == "ps":
            if val == 1:
                iface.paused = False
            if val == 0:
                iface.paused = True





# server_host = ServerHost()


def main():
    sys.path.append("/Users/isabelburgos/Scan-Gen-Glasgow-Testing/software")
    from glasgow.support.task_queue import TaskQueue
    queue = TaskQueue()
    loop = asyncio.get_event_loop()
    close_future = loop.create_future()
    server_host = ServerHost(queue)
    server_host.start_start_servers(close_future)
    loop.run_forever()

if __name__ == "__main__":
    main()