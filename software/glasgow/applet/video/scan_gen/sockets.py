import sys
import asyncio
sys.path.append("/Users/isabelburgos/Scan-Gen-Glasgow-Testing/software")
from glasgow.support.endpoint import *


async def main():  
    endpoint = await ServerEndpoint("socket", None, ("tcp","localhost","1234"), queue_size=32)
    while True:
        try:
            data = await endpoint.recv(4)
            print(data)
        except:
            break


asyncio.run(main())