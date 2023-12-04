import sys
import asyncio
import logging
import time

logger = logging.getLogger(__name__)

from test_socket import get_recieve_socket, r_benchmark

sys.path.append("/Users/isabelburgos/Scan-Gen-Glasgow-Testing/software")
from glasgow.support.endpoint import *

data = "FFFF"*4096
bytes_data = data.encode("UTF-8")

async def get_endpoint():
    endpoint = await ServerEndpoint("socket", logger, args.endpoint, queue_size=16384*8)
    return endpoint

async def s_benchmark(endpoint):
    for n in range(256):
        start_time = time.perf_counter()
        await endpoint.send(bytes_data)
        end_time = time.perf_counter()
        print(end_time-start_time)


async def run():
    endpoint = await get_endpoint()
    reader, writer = await get_recieve_socket()
    await asyncio.gather(
        s_benchmark(endpoint),
        r_benchmark(reader, writer)
    )


asyncio.run(run())
