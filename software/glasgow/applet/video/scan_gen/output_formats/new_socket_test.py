import asyncio

async def recieve_data_client():
    HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
    PORT = 1237  # Port to listen on (non-privileged ports are > 1023)
    print("opening connection")
    while True:
        try:
            reader, writer = await asyncio.open_connection(
                HOST, PORT)
            print("connection made")
            addr = writer.get_extra_info('peername')
            print(f"addr: {addr!r}")
            break
        except:
            pass
    while True:
        if not reader.at_eof():
            data = await reader.read(16384)
            print("recieved data")
            print(f'Received: {data.decode()!r}')
        else:
            break
    print('Close the connection')
    writer.close()
    await writer.wait_closed()

async def tcp_echo_client(message):
    HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
    PORT = 1235  # Port to listen on (non-privileged ports are > 1023)
    reader, writer = await asyncio.open_connection(
        HOST, PORT)

    print(f'Send: {message!r}')
    writer.write(message.encode())
    await writer.drain()

    data = await reader.read(100)
    print(f'Received: {data.decode()!r}')

    print('Close the connection')
    writer.close()
    await writer.wait_closed()



async def tcp_msg_client(message):
    HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
    PORT = 1236  # Port to listen on (non-privileged ports are > 1023)
    reader, writer = await asyncio.open_connection(
        HOST, PORT)

    print(f'Send: {message!r}')
    writer.write(message.encode())
    await writer.drain()

    print('Close the connection')
    writer.close()
    await writer.wait_closed()

asyncio.run(tcp_msg_client('rx16384'))
asyncio.run(recieve_data_client())
