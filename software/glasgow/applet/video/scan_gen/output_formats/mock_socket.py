import sys
import asyncio
sys.path.append("/Users/isabelburgos/Scan-Gen-Glasgow-Testing/software")
from glasgow.support.endpoint import *


class SG_EndpointInterface():
    def __init__(self, *args, **kwargs):
        self.scanning = False

    async def get_stream_endpoint(self):
        endpoint = await ServerEndpoint("socket", None, ("tcp","localhost","1234"), queue_size=8388608*8)
        return endpoint

    async def get_ctrl_endpoint(self):
        endpoint = await ServerEndpoint("socket", None, ("tcp","localhost","1235"), queue_size=32)
        return endpoint

    async def listen_at_endpoint(self):
        self.ctrl_endpoint = await self.get_ctrl_endpoint()
        print(self.ctrl_endpoint)
        while True:
            try:
                cmd = await self.ctrl_endpoint.recv(7)
                cmd = cmd.decode(encoding='utf-8', errors='strict')
                print("rcvd", cmd)
                await self.process_cmd(cmd)
            except:
                break

    async def stream_to_endpoint(self):
        self.stream_endpoint = await self.get_stream_endpoint()
        print(self.stream_endpoint)
        while True:
            if self.scanning:
                data = [5]*16384
                print("sending", data)
                await self.stream_endpoint.send(data)
            else:
                pass

    async def process_cmd(self, cmd):
        c = str(cmd[0:2])
        val = int(cmd[2:])
        print("cmd:", c, "val:", val)
        if c == "sc":
            self.scanning = True

async def _main():
    scan_iface = SG_EndpointInterface()
    await asyncio.gather(scan_iface.listen_at_endpoint(),
                        scan_iface.stream_to_endpoint())



def main():
    loop = asyncio.get_event_loop()
    exit(loop.run_until_complete(_main()))


if __name__ == "__main__":
    main()