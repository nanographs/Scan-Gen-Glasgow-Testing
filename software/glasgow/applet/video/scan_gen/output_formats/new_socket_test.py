import asyncio

async def recieve_data_client():
    HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
    PORT = 1237  # Port to listen on (non-privileged ports are > 1023)
    print("opening connection")
    while True:
        await asyncio.sleep(0)
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
        try:
            if not reader.at_eof():
                await asyncio.sleep(0)
                data = await reader.read(16384)
                print("recieved data")
                print(f'Received: {data.decode()!r}')
            else:
                print("at eof?")
                print(reader)
                break
        except Exception as e:
            print("error:", e)
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


async def wait():
    await asyncio.sleep(10)
    await tcp_msg_client('1111111')


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(tcp_msg_client('rx16384'))
    loop.create_task(recieve_data_client())
    loop.create_task(wait())
    loop.run_forever()

main()