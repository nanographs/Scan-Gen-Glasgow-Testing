import asyncio

class ConnectionClient:
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


class DataClient(ConnectionClient):
    def __init__(self, host, port):
        self.host = host
        self.port = port
    async def open(self):
        print("opening data client")
        loop = asyncio.get_event_loop()
        future_con = loop.create_future()
        loop.create_task(self.open_connection(self.host, self.port, future_con))
        await asyncio.sleep(0)
        reader, writer = await future_con
        self.writer = writer
        self.reader = reader
        await self.start_reading()
    async def start_reading(self):
        data = await self.reader.read(16384)
        print(data)


if __name__ == "__main__":
    async def main():
        data_client = DataClient("127.0.0.1",1238)
        await data_client.open()

    asyncio.run(main())