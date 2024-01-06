import asyncio

async def stream_data(reader, writer):
    data = bytes([5]*16384)
    writer.write(data)
    print("wrote data")
    await writer.drain()
    print("drained")

async def start_data_server(host, port):
    print("starting data server at", host, port)
    #self.streaming = True
    data_server = await asyncio.start_server(stream_data, host, port)
    await data_server.serve_forever()

asyncio.run(start_data_server("127.0.0.1", 1238))
