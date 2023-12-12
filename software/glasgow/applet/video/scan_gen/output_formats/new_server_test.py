import asyncio
import functools


async def get_data():
    data = bytes([5]*16384)
    return data
    #future.set_result(data)




async def handle_echo(reader, writer):
    data = await reader.read(100)
    message = data.decode()
    addr = writer.get_extra_info('peername')

    print(f"Received {message!r} from {addr!r}")

    print(f"Send: {message!r}")
    writer.write(data)
    await writer.drain()

    print("Close the connection")
    writer.close()
    await writer.wait_closed()

class ServerHost:
    def __init__(self):
        self.servers = []
        self.streaming = None

    async def start_servers(self, client_thread, host, port):
        server = await asyncio.start_server(client_thread, host, port)
        self.servers.append(server)
        await server.serve_forever()
    
    async def start_cmd_server(self, host, port):
        print("starting cmd server")
        self.cmd_server = await asyncio.start_server(self.handle_cmd, host, port)
        await self.cmd_server.serve_forever()

    async def start_data_server(self, host, port):
        print("starting data server")
        #self.streaming = True
        self.data_server = await asyncio.start_server(self.send_data, host, port)
        await self.data_server.serve_forever()

    # def startdata(self):
    #     HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
    #     PORT = 1238  # Port to listen on (non-privileged ports are > 1023)
    #     loop = asyncio.get_event_loop()
    #     loop.create_task(self.start_data_server(HOST, PORT))
    
    async def stopdata(self):
        print("closing data writer")
        self.streaming.cancel()
        self.data_writer.close()
        await self.data_writer.wait_closed()

    async def handle_cmd(self, reader, writer):
        data = await reader.read(7)
        message = data.decode()

        print("message:", message)
        print("Close the connection")
        writer.close()
        await writer.wait_closed()

        loop = asyncio.get_event_loop()
        # loop.call_soon(
        # functools.partial(print, "Hello", flush=True))
        if message == "rx16384":
            # loop.call_soon(
            # functools.partial(self.startdata))
            self.streaming = asyncio.ensure_future(self.send_data_continously())
        elif message == "1111111":
            print(server_host.data_server)
            # loop.call_soon(
            # functools.partial(self.stopdata))
            # loop.create_task(self.stopdata())
            self.streaming.cancel()

    async def send_data(self, reader, writer):
        self.data_writer = writer
        addr = writer.get_extra_info('peername')
        print(f"addr: {addr!r}")
        

    async def send_data_continously(self):
        while True:
            await self.write_data()

    async def write_data(self):
        await asyncio.sleep(1)
        data = await get_data()
        print("sending data")
        self.data_writer.write(data)




server_host = ServerHost()


def main():
    HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
    PORT = 1237  # Port to listen on (non-privileged ports are > 1023)
    try:
        loop = asyncio.get_event_loop()
        #loop.create_task(server_host.start_servers(handle_echo, HOST, PORT))
        loop.create_task(server_host.start_cmd_server(HOST, PORT))
        loop.create_task(server_host.start_data_server(HOST, PORT+1))
        loop.run_forever()
    except Exception as e:
        print("error:", e)


main()