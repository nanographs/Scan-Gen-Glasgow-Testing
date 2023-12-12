import asyncio
import functools

async def get_data():
    data = bytes([5]*16384)
    return data
    #future.set_result(data)

def get_data_continously():
    print("getting data")
    # data = yield get_data()
    # print(data)

#get_data_continously()


async def send_data(reader, writer):
    addr = writer.get_extra_info('peername')
    print(f"addr: {addr!r}")
    data = await get_data()
    # loop = asyncio.get_event_loop()
    # future = loop.create_future()
    print("sending data")
    writer.write(data)
    writer.write_eof()
    print("sent data")
    await writer.drain()
    print("close connection")
    writer.close()
    await writer.wait_closed()
    print("connection closed")

async def handle_cmd(reader, writer):
    data = await reader.read(7)
    message = data.decode()

    print("message:", message)
    print("Close the connection")
    writer.close()
    await writer.wait_closed()

    loop = asyncio.get_event_loop()
    # loop.call_soon(
    # functools.partial(print, "Hello", flush=True))
    loop.call_soon(
    functools.partial(server_host.startdata))

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

    async def start_servers(self, client_thread, host, port):
        server = await asyncio.start_server(client_thread, host, port)
        self.servers.append(server)
        await server.serve_forever()
    
    async def start_cmd_server(self, client_thread, host, port):
        print("starting cmd server")
        self.cmd_server = await asyncio.start_server(client_thread, host, port)
        await self.cmd_server.serve_forever()

    async def start_data_server(self, client_thread, host, port):
        print("starting data server")
        self.data_server = await asyncio.start_server(client_thread, host, port)
        await self.data_server.serve_forever()

    def startdata(self):
        HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
        PORT = 1237  # Port to listen on (non-privileged ports are > 1023)
        loop = asyncio.get_event_loop()
        loop.create_task(self.start_data_server(send_data, HOST, PORT))

server_host = ServerHost()


def main():
    HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
    PORT = 1235  # Port to listen on (non-privileged ports are > 1023)
    try:
        loop = asyncio.get_event_loop()
        #loop.create_task(server_host.start_servers(handle_echo, HOST, PORT))
        loop.create_task(server_host.start_cmd_server(handle_cmd, HOST, PORT+1))
        # loop.create_task(server_host.start_data_server(send_data, HOST, PORT+2))
        loop.run_forever()
    except Exception as e:
        print("error:", e)


main()