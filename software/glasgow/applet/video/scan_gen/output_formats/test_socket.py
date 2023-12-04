import socket
import asyncio


async def get_recieve_socket():
    HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
    PORT = 1234  # Port to listen on (non-privileged ports are > 1023)
    connected = False
    while connected == False:
        try:
            reader, writer = await asyncio.open_connection(HOST, PORT)
            return reader, writer
            connected = True
        except ConnectionRefusedError:
            pass

async def r_benchmark(reader,writer):
    while True:
        try:
            data = await reader.read(8388608)
            print(data)
            print("read", len(data))
        except:
            break

async def go():
    reader, writer = await asyncio.ensure_future(get_recieve_socket())
    await r_benchmark(reader,writer)

asyncio.run(go())




