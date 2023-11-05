import asyncio
import numpy as np

class ScanController:
    _msg_scan = ("scan").encode("UTF-8")
    _msg_stop = ("stop").encode("UTF-8") 
    _msg_reset = ("eeee").encode("UTF-8") 

    _HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
    _PORT = 1234  # Port to listen on (non-privileged ports are > 1023)
    
    def __init__(self):
        dimension = 512
        self.recalculate_buffer(dimension)

    def recalculate_buffer(self, dimension):
        self.dimension = dimension
        self.buf = np.ones((self.dimension, self.dimension))
        self.cur_line = 0
        self.packet_lines = int(16384/self.dimension)

    async def connect(self):
        try:
            self.reader, self.writer = await asyncio.open_connection(self._HOST, self._PORT)
            print(self.writer.transport)
            print(self.writer.can_write_eof())
            return "Connected"
        except Exception as exc:
            print(exc)
            return ("Error: {}".format(exc))
    
    async def close(self):
        if self.writer is not None:
            self.writer.close()
            await self.writer.wait_closed()

    async def start_scan(self):
        self.writer.write(self._msg_scan)
        loop = asyncio.get_event_loop()
        print("API", loop)
        print("sent", self._msg_scan)
        await self.writer.drain()

    async def stop_scan(self):
        self.writer.write(self._msg_stop)
        await self.writer.drain()

    async def reset_scan(self):
        self.writer.write(self._msg_reset)
        await self.writer.drain()
    
    async def set_mode(self):
        _msg = ("mmmm").encode("UTF-8") 
        self.writer.write(_msg)
        await self.writer.drain()
    
    async def set_loopback(self):
        _msg = ("llll").encode("UTF-8") 
        self.writer.write(_msg)
        await self.writer.drain()
    
    async def set_image_parameters(self, resolution_bits, dwell_time):
        assert (9 <= resolution_bits <= 14)
        msg_res = ("re" + format(resolution_bits, '02d')).encode("UTF-8") ## ex: res09, res10
        self.writer.write(msg_res)
        await self.writer.drain()
        msg_dwell = ("d" + format(dwell_time, '03d')).encode("UTF-8") ## ex: d255, d001
        self.writer.write(msg_dwell)
        await self.writer.drain()
    
    async def set_resolution(self, resolution_bits):
        assert (9 <= resolution_bits <= 14)
        dimension = pow(2,resolution_bits)
        self.recalculate_buffer(dimension)
        msg_res = ("re" + format(resolution_bits, '02d')).encode("UTF-8") ## ex: res09, res10
        self.writer.write(msg_res)
        await self.writer.drain()

    async def set_dwell_time(self, dwell_time):
        assert (1 <= dwell_time <= 255)
        msg_dwell = ("d" + format(dwell_time, '03d')).encode("UTF-8") ## ex: res09, res10
        self.writer.write(msg_dwell)
        await self.writer.drain()


    async def start_scan_stream(self):
        await self.start_scan()
        self.scanning = asyncio.ensure_future(self.stream_continously())

    async def start_scan_pattern_stream(self, pattern_stream):
        pattern = self.pattern_loop(512, pattern_stream)
        await self.start_scan()
        self.scanning = asyncio.ensure_future(self.stream_continously_pattern(pattern))

    def pattern_loop(self, dimension, pattern_stream):
        while 1:
            for n in range(int(dimension*dimension/16384)): #packets per frame
                print(n)
                yield pattern_stream[n*16384:(n+1)*16384]
            print("pattern complete")
        
    async def send_single_packet(self, pattern_slice):
            print("writing")
            self.writer.write(pattern_slice)
            print("write", pattern_slice[0], ":", pattern_slice[-1], "-", len(pattern_slice))
            await self.writer.drain()

    async def stream_continously(self):
        while True:
            try:
                await self.get_single_packet()
            except RuntimeError:
                print("eof:", self.reader.at_eof())
                break

    async def get_single_packet(self):
        print("reading")
        data = await self.reader.read(16384)
        print("read done")
        if data is not None:
            print("recvd", (list(data))[0], ":", (list(data))[-1], "-", len(list(data)))
            #return data
            await self.stream_to_buffer(data)

    async def stream_to_buffer(self,raw_data):
        data = list(raw_data)
        if len(data) != 16384:
            print(data)
        else:
            d = np.array(data)
            d.shape = (self.packet_lines,self.dimension)
            self.buf[self.cur_line:self.cur_line+self.packet_lines] = d
            self.cur_line += self.packet_lines
            if self.cur_line == self.dimension:
                self.cur_line = 0 ## new frame, back to the top



    async def acquire_image(self, dimension:int):
        await self.start_scan()
        self.dimension= dimension
        print("dimension:", dimension)
        valid_dimensions = [512, 1024, 2048, 8096, 16384]
        if dimension in valid_dimensions:
            print("dimension is a power of 2")
        buf = np.ones(shape=(dimension,dimension))
        packets_per_frame = int(dimension*dimension/16384)
        lines_per_packet = int(16384/dimension)
        print(packets_per_frame, "packets per frame, ", lines_per_packet, "lines each")
        for n in range(0,packets_per_frame):
            raw_data = await self.reader.read(16384)
            data = list(raw_data)
            print(n,"/", packets_per_frame, " - recvd", (list(data))[0], ":", (list(data))[-1], "-", len(list(data)))
            d = np.array(data)
            d.shape = (lines_per_packet,dimension)
            buf[n*lines_per_packet:(n+1)*lines_per_packet] = d
        await self.stop_scan()
        return buf



async def _main():
    scan_controller = ScanController()
    await scan_controller.connect()
    await scan_controller.set_image_parameters(resolution_bits = 9, dwell_time = 5)
    image = await scan_controller.acquire_image(2048)
    print(image)

def main():
    loop = asyncio.get_event_loop()
    exit(loop.run_until_complete(_main()))


if __name__ == "__main__":
    main()