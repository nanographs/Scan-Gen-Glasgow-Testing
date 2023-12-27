import asyncio
import numpy as np
from enum import Enum
import struct
import time


class scan_mode(Enum):
    stop = 0
    raster = 1
    raster_pattern = 2
    vector = 3

class data_format:
    frame_sync = "fs"
    line_sync = "ls" ## frame and line sync
    eight_bit = "8b"
    config = "cf"
    pause = "ps"

class frame_vars:
    x_full_frame_resolution = "rx"
    y_full_frame_resolution = "ry"
    x_lower_limit = "lx"
    x_upper_limit = "ux"
    y_lower_limit = "ly"
    y_upper_limit = "uy"
    dwell_time = "dw"

class cmd_encoder:
    def set_scan_mode(self, scan_mode):
        num = format(scan_mode.value, '05d')
        cmd = ("sc" + num)
        return cmd
    def set_frame(self, var, pixels):
        num = format(pixels, '05d')
        cmd = (var + num)
        return cmd
    def set_data_format(self, data_format, setting):
        num = format(setting, '05d')
        cmd = (data_format + num)
        return cmd

def test_cmd_encoder():
    cmd = cmd_encoder()
    assert (cmd.set_scan_mode(scan_mode.raster) == "sc00001")
    assert (cmd.set_frame(frame_vars.x_full_frame_resolution, 16384) == "rx16384")
    assert (cmd.set_data_format(data_format.eight_bit, True) == "8b00001")


class ScanCtrl:
    def __init__(self):
        self.cmd = cmd_encoder()

    def set_scan_mode(self, val):
        msg = "sc0000" + str(val)
        return msg

    def set_frame_resolution(self, x_resolution_val, y_resolution_val):
        msg1 = self.cmd.set_frame(frame_vars.x_full_frame_resolution, x_resolution_val)
        msg2 = self.cmd.set_frame(frame_vars.y_full_frame_resolution, y_resolution_val)
        return (msg1+msg2)

    def set_x_resolution(self, x_resolution_val):
        msg = self.cmd.set_frame(frame_vars.x_full_frame_resolution, x_resolution_val)
        return msg

    def set_y_resolution(self, y_resolution_val):
        msg = self.cmd.set_frame(frame_vars.y_full_frame_resolution, y_resolution_val)
        return msg

    def set_dwell_time(self, dwell_val):
        msg = self.cmd.set_frame(frame_vars.dwell_time, dwell_val)
        return msg

    def set_ROI(self, x_upper, x_lower, y_upper, y_lower):
        msg1 = self.cmd.set_frame(frame_vars.x_upper_limit, x_upper)
        msg2 = self.cmd.set_frame(frame_vars.x_lower_limit, x_lower)
        msg3 = self.cmd.set_frame(frame_vars.y_upper_limit, y_upper)
        msg4 = self.cmd.set_frame(frame_vars.y_lower_limit, y_lower)
        return (msg1+msg2+msg3+msg4)


    def raise_config_flag(self):
        msg = self.cmd.set_data_format(data_format.config, True)   
        return msg
    
    def lower_config_flag(self):
        msg = self.cmd.set_data_format(data_format.config, False)   
        return msg

    def pause(self):
        msg = self.cmd.set_data_format(data_format.pause, 0)   
        return msg
    
    def unpause(self):
        msg = self.cmd.set_data_format(data_format.pause, 1)   
        return msg

    def set_8bit_output(self):
        msg = self.cmd.set_data_format(data_format.eight_bit, True)   
        return msg
    
    def set_16bit_output(self):
        msg = self.cmd.set_data_format(data_format.eight_bit, False)   
        return msg



class ScanStream:
    _HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
    _PORT = 1234  # Port to listen on (non-privileged ports are > 1023)
    
    def __init__(self):
        self.y_height = 512
        self.x_width = 512

        self.current_x = 0
        self.current_y = 0

        self.scan_mode = 0

        self.eight_bit_output = False
        self.buffer = np.zeros(shape=(self.y_height, self.x_width),
                    dtype = np.uint8)

        self.pointbuffer = np.array([], dtype = np.uint8)
    
    def change_buffer(self, x_width, y_height):
        self.x_width = x_width
        self.y_height = y_height
        self.buffer = np.zeros(shape=(self.y_height, self.x_width),
                    dtype = np.uint8)
        print("new buffer size:", x_width, y_height)
        self.current_x = 0
        self.current_y = 0

    def clear_buffer(self):
        self.buffer = np.zeros(shape=(self.y_height, self.x_width),
                    dtype = np.uint8)
        print("cleared buffer")

    def decode_rdwell(self, n):
        a2, a1 = n
        a = int("{0:08b}".format(a1) + "{0:08b}".format(a2),2)
        return a
    
    def decode_rdwell_packet(self, raw_data):
        if isinstance(raw_data, bytes):
            data = list(raw_data)
        elif isinstance(raw_data, memoryview):
            start = time.perf_counter()
            data = raw_data.tolist()
            end = time.perf_counter()
            print("list time", end-start)
        else:
            data = raw_data
        #print("bytes:", data)
        print("first line:", data[0:12])
        start = time.perf_counter()
        if self.eight_bit_output:
            return data
        else:
            packet = []
            for n in range(0,len(data),2):
                dwell = self.decode_rdwell(data[n:n+2])
                packet.append(dwell)
            end = time.perf_counter()
            print("merge time", end-start)
            return packet

    def decode_vpoint(self, n):
        try:
            if self.eight_bit_output:
                x2, x1, y2, y1, a1 = n
            else:
                x2, x1, y2, y1, a2, a1 = n
            x = int("{0:08b}".format(x1) + "{0:08b}".format(x2),2)
            y = int("{0:08b}".format(y1) + "{0:08b}".format(y2),2)
            if self.eight_bit_output:
                a = int("{0:08b}".format(a1),2)
            else:
                a = int("{0:08b}".format(a1) + "{0:08b}".format(a2),2)
                
            return [x, y, a]
        except ValueError:
            pass ## 16384 isn't divisible by 3...
            #ignore those pesky extra values.... just for new

    def decode_vpoint_to_buffer(self, n):
        print("point:", n)
        if self.eight_bit_output:
            x2, x1, y2, y1, a1 = n
        else:
            x2, x1, y2, y1, a2, a1 = n
        x = int("{0:08b}".format(x1) + "{0:08b}".format(x2),2)
        y = int("{0:08b}".format(y1) + "{0:08b}".format(y2),2)
        if self.eight_bit_output:
            a = int("{0:08b}".format(a1),2)
        else:
            a = int("{0:08b}".format(a1) + "{0:08b}".format(a2),2)
        print("x, y, a:", x, y, a)
        self.buffer[y][x] = a
        return [x, y, a]

    def decode_vpoint_packet(self, raw_data, to_buffer = False):
        if isinstance(raw_data, bytes):
            data = list(raw_data)
        if isinstance(raw_data, memoryview):
            data = raw_data.tolist()
        else:
            data = raw_data
        packet = []
        if self.eight_bit_output:
            for n in range(0,len(data),5):
                if to_buffer:
                    self.decode_vpoint_to_buffer(data[n:n+5])
                else:
                    point = self.decode_vpoint(data[n:n+5])
                    print("point", point)
                    packet.append(point)
        else:
            for n in range(0,len(data),6):
                if to_buffer:
                    self.decode_vpoint_to_buffer(data[n:n+6])
                else:
                    point = self.decode_vpoint(data[n:n+6])
                    print("point", point)
                    packet.append(point)
        
        if not to_buffer:
            return packet

    def stream_points_to_buffer(self, data):
        print("decoding points")
        data = np.append(self.pointbuffer,data)
        print("buffered points:", self.pointbuffer)
        n_complete_points = len(data)//3
        print("n complete points:", n_complete_points)
        print("data [:",n_complete_points*3,"]")
        complete_points = np.array(data[:n_complete_points*3]).reshape((n_complete_points, 3))
        start = time.perf_counter()
        for n in complete_points:
            x, y, a = n
            self.buffer[y][x] = a
        end = time.perf_counter()
        print("total time:", end - start)
        if n_complete_points > 0:
            print("time per point:", (end-start)/n_complete_points)
        print("decoded all points")
        print("extra points:",data[n_complete_points*3:])
        extra_points = data[n_complete_points*3:]
        self.pointbuffer = extra_points

    def parse_config(self, config):
        # new_x = self.decode_rdwell(config[0:2])
        # new_y = self.decode_rdwell(config[2:4])
        # scan_mode = config[4]
        new_x = config[0]
        new_y = config[1]
        scan_mode = config[2]
        self.scan_mode = scan_mode
        if ((new_x != self.x_width) | (new_y != self.y_height)):
            self.current_x = 0
            self.current_y = 0
            self.x_width = new_x + 1
            self.y_height = new_y + 1
            self.buffer = np.zeros(shape=(self.y_height, self.x_width),
                        dtype = np.uint8)
            print("new buffer size:", self.x_width, self.y_height)
        
    def buffer_with_config(self, config, data):
        self.parse_config(config)
        print("scan mode:", self.scan_mode)
        self.stream_to_buffer(data)

    def stream_to_buffer(self, data):
        if self.scan_mode == 1:
            self.stream_frame_to_buffer(data)
        if self.scan_mode == 3:
            self.stream_points_to_buffer(data)

    def handle_config(self, raw_data, config_bytes = 3, print_debug = False):
        #print("handling mixed data stream")
        start = time.perf_counter()
        data = self.decode_rdwell_packet(raw_data)
        end = time.perf_counter()
        print("time to decode 16 to 8:", end-start)
        #print("data:", data)
        start = time.perf_counter()
        d = np.array(data)
        if print_debug:
            print("data first line:", d[0:13])
        #zero_indices = np.nonzero(d < 1)[0] ## To look for zeros
        startb = time.perf_counter()
        zero_indices = np.nonzero(d == 65535)[0]
        endb = time.perf_counter()
        print("time to check for config", endb-startb)
        if print_debug:
            print("zero indices:", zero_indices)
        if len(zero_indices) == 0:
            start_a = time.perf_counter()
            self.stream_to_buffer(data)
            end_a = time.perf_counter()
            print("time to stuff", end_a-start_a)
        else:
            start_flag = int(zero_indices[0])
            stop_flag = start_flag + config_bytes + 1
            data_start = stop_flag
            config = d[start_flag+1:stop_flag]
            if print_debug:
                print("config:", config, "start", start_flag, "stop", stop_flag)
            stop_index = np.where(zero_indices == stop_flag)[0][0]
            print("stop index", stop_index)
            zero_indices = zero_indices[stop_index+1:]
            n = 0
            while len(zero_indices) > 0:
                n += 1
                #if print_debug:
                    #print("zero indices", zero_indices)
                start_flag = int(zero_indices[0])
                data_with_config = d[stop_flag+1:start_flag]
                if print_debug:
                    print("data", data_with_config, "start", stop_flag+1, "stop", start_flag)
                end = time.perf_counter()
                print("time to parse config #",n,  end-start)
                start = time.perf_counter()
                self.buffer_with_config(config, data_with_config)
                end = time.perf_counter()
                print("time to stuff data", end - start)
                stop_flag = start_flag + config_bytes + 1
                config = d[start_flag+1:stop_flag]
                if print_debug:
                    print("start", start_flag, "stop", stop_flag)
                    print("config:", config)
                stop_index = np.where(zero_indices == stop_flag)[0][0]
                zero_indices = zero_indices[stop_index+1:]
            data_with_config = d[stop_flag+1:]
            if print_debug:
                print("data", data_with_config)
            self.buffer_with_config(config, data_with_config)
            
    def stream_frame_to_buffer(self, data, print_debug = False):
        #data = self.decode_rdwell_packet(raw_data)
        #data = raw_data
        if print_debug:
            print("data length:", len(data))
            print("frame size (x, y):", self.x_width, self.y_height)
            print("current x, current y:", self.current_x, self.current_y)
        
        if self.current_x > 0:
            
            partial_start_points = self.x_width - self.current_x
            if print_debug:
                print("partial start points:", partial_start_points)
            full_lines = ((len(data) - partial_start_points)//self.x_width)
            
            if partial_start_points > len(data): ## the current line will not be completed
                self.buffer[self.current_y][self.current_x:(self.current_x + len(data))] = data[0:]
                partial_end_points = 0
            else:
                self.buffer[self.current_y][self.current_x:self.x_width] = data[0:partial_start_points]
                partial_end_points = ((len(data) - partial_start_points)%self.x_width)
            if print_debug:
                print("top rollover index", 0, ":", partial_start_points)
                # print("rollover data", data[0:partial_start_points])
                # print("top row", self.buffer[self.current_y])
                #print(self.buffer[self.current_y][self.current_x:self.x_width] )
            if self.current_y >= self.y_height - 1:
                self.current_y = 0
                #print("cy 0")
            else:
                self.current_y += 1
                #print("cy+1")
        else:
            if print_debug:
                print("no top rollover")
            partial_start_points = 0
            partial_end_points = ((len(data))%self.x_width)
            full_lines = ((len(data))//self.x_width)

        ## TODO: rewrite without a for loop   
        for i in range(0,full_lines):
            if print_debug:
                print("current y", self.current_y)
                print("mid index", partial_start_points + i*self.x_width, ":",partial_start_points + (i+1)*self.x_width)
            self.buffer[self.current_y] = data[partial_start_points + i*self.x_width:partial_start_points + (i+1)*self.x_width]
            #print("midline", data[partial_start_points + i*self.x_width:partial_start_points + (i+1)*self.x_width])
            if self.current_y >= self.y_height - 1:
                self.current_y = 0
                #print("cy 0")
            else:
                self.current_y += 1
                #print("cy+1")
        
        if print_debug:
            print("partial end points", partial_end_points)
        self.buffer[self.current_y][0:partial_end_points] = data[self.x_width*full_lines + partial_start_points:self.x_width*full_lines + partial_start_points + partial_end_points]
        
            #print("rollover index", self.x_width*full_lines + partial_start_points,":",self.x_width*full_lines + partial_start_points + partial_end_points)
            #print(self.buffer[self.current_y][0:partial_end_points])
            #print("last row")
            #print(self.buffer[self.current_y])
        
        self.current_x = partial_end_points
        #assert (self.buffer[self.current_y][0] == 0)

        #print(self.buffer)
        #print("=====")


if __name__ == "__main__":
    scanctrl = ScanCtrl()
    scanstream = ScanStream()
    def test_raster_parsing():
        data = [250, 251, 252, 253, 254, 255, 0, 0, 2, 0, 2, 0, 1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 0, 0, 2, 0, 2, 0, 1, 1, 2, 3, 4, 5]
        data2 = [255]*16384
        scanstream.handle_config(data, print_debug=True)
        scanstream.handle_config(data2, print_debug=True)
    def test_vector_parsing():
        # data = [100, 0, 200, 0, 255, 150, 0, 250, 0, 200, 0,0,0,0]
        # data2 = [255] + [100, 0, 200, 0, 255, 150, 0, 250, 0, 200, 0,0,0,0,255]*512
        # scanstream.change_buffer(255,255)
        data = [255, 255, 255, 1, 255, 1, 3, 0, 255, 255, 255, 0, 255, 0, 1, 0]
        scanstream.handle_config(data)
        # scanstream.stream_points_to_buffer(data2)
        #scanstream.decode_vpoint_packet(data)
        #print(scanstream.buffer)

    test_vector_parsing()
