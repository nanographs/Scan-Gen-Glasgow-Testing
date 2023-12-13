import asyncio


async def tcp_echo_client(message):
    HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
    PORT = 1237  # Port to listen on (non-privileged ports are > 1023)
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



class ConnectionManager:
    def __init__(self):
        pass
    async def open_connection(self, host, port, future):
        print("trying to open connection at", host, port)
        while True:
            try:
                reader, writer = await asyncio.open_connection(
                    host, port)
                print("connection made")
                addr = writer.get_extra_info('peername')
                print(f"addr: {addr!r}")
                future.set_result([reader,writer])
                break
            except ConnectionError:
                #print("connection error")
                pass

    async def read_continously(self, reader):
        while True:
            try:
                if not reader.at_eof():
                    await asyncio.sleep(0)
                    data = await reader.read(16384)
                    print("recieved data")
                    print(data)
                    #print(f'Received: {data.decode()!r}')
                else:
                    print("at eof?")
                    print(reader)
                    break
            except Exception as e:
                print("error:", e)
                break


    async def recieve_data_client(self):
        host = "127.0.0.1"  # Standard loopback interface address (localhost)
        port = 1238  # Port to listen on (non-privileged ports are > 1023)
        print("opening data client")
        loop = asyncio.get_event_loop()
        future_con = loop.create_future()
        loop.create_task(self.open_connection(host, port, future_con))
        await asyncio.sleep(0)
        reader, writer = await future_con
        self.data_writer = writer
        self.data_reader = reader

    async def tcp_msg_client(self, message):
        HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
        PORT = 1237  # Port to listen on (non-privileged ports are > 1023)
        print("opening cmd client")
        loop = asyncio.get_event_loop()
        future_con = loop.create_future()
        loop.create_task(self.open_connection(HOST, PORT, future_con))
        await asyncio.sleep(0)
        reader, writer = await future_con
        # reader, writer = await asyncio.open_connection(
        #     HOST, PORT)

        print(f'Send: {message!r}')
        writer.write(message.encode())
        await writer.drain()

        print('Close tcp_msg_client')
        writer.close()
        await writer.wait_closed()


    async def wait_stop(self):
        await asyncio.sleep(10)
        await self.stop_reading()
        
    async def start_reading(self):
        asyncio.ensure_future(self.tcp_msg_client('sc00001'))
        self.streaming = asyncio.ensure_future(self.read_continously(self.data_reader))

    async def stop_reading(self):
        await self.tcp_msg_client('1111111')
        self.streaming.cancel()
    
    async def close_data_stream(self):
        print('Close data stream')
        self.data_writer.close()
        await self.data_writer.wait_closed()


def main():
    con = ConnectionManager()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(con.recieve_data_client())
    loop.run_until_complete(con.tcp_msg_client("rx16384"))
    loop.run_until_complete(con.tcp_msg_client("ry16384"))
    loop.create_task(con.start_reading())
    loop.create_task(con.wait_stop())
    loop.run_forever()
    #loop.run_until_complete(con.tcp_msg_client("sc00001"))
    # # con = ConnectionManager()
    
    # loop.run_until_complete(con.start_reading())
    # loop.run_until_complete(con.wait_stop())
    # loop.run_until_complete(con.start_reading())
    # loop.run_until_complete(con.wait_stop())
    # loop.run_until_complete(con.close_data_stream())
    # loop.run_forever()

main()