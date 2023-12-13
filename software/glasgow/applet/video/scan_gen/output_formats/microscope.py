import asyncio
import numpy as np
from enum import Enum
import struct

class scan_mode(Enum):
    stop = 0
    raster = 1
    raster_pattern = 2
    vector = 3

class data_format:
    frame_sync = "fs"
    line_sync = "ls" ## frame and line sync
    eight_bit = "8b"

class frame_vars:
    x_full_frame_resolution = "rx"
    y_full_frame_resolution = "ry"
    x_lower_limit = "lx"
    x_upper_limit = "ux"
    y_lower_limit = "ly"
    y_upper_limit = "uy"

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
    async def set_frame_resolution(self, x_resolution_val, y_resolution_val):
        msg1 = self.cmd.set_frame(frame_vars.x_full_frame_resolution, x_resolution_val)
        msg2 = self.cmd.set_frame(frame_vars.y_full_frame_resolution, y_resolution_val)
        return (msg1+msg2)

    async def set_x_resolution(self, x_resolution_val):
        msg = self.cmd.set_frame(frame_vars.x_full_frame_resolution, x_resolution_val)
        return msg

    async def set_y_resolution(self, y_resolution_val):
        msg = self.cmd.set_frame(frame_vars.y_full_frame_resolution, y_resolution_val)
        return msg

    async def set_ROI(self, x_upper, x_lower, y_upper, y_lower):
        msg1 = cmd.set_frame(frame_vars.x_upper_limit, x_upper)
        msg2 = cmd.set_frame(frame_vars.x_lower_limit, x_lower)
        msg3 = cmd.set_frame(frame_vars.y_upper_limit, y_upper)
        msg4 = cmd.set_frame(frame_vars.y_lower_limit, y_lower)
        return (msg1+msg2+msg3+msg4)
        

class ScanStream:
    _HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
    _PORT = 1234  # Port to listen on (non-privileged ports are > 1023)
    
    def __init__(self):
        self.y_height = 512
        self.x_width = 512

        self.current_x = 0
        self.current_y = 0

        self.eight_bit_output = True
        self.buffer = np.zeros(shape=(self.y_height, self.x_width),
                    dtype = np.uint8)
    
    def change_buffer(self, x_width, y_height):
        self.x_width = x_width
        self.y_height = y_height
        self.buffer = np.zeros(shape=(self.y_height, self.x_width),
                    dtype = np.uint8)

    def decode_rdwell(self, n):
        a2, a1 = n
        a = int("{0:08b}".format(a1) + "{0:08b}".format(a2),2)
        return a
    
    def decode_rdwell_packet(self, raw_data):
        if isinstance(raw_data, bytes):
            data = list(raw_data)
        else:
            data = raw_data.tolist()
        if self.eight_bit_output:
            return data
        else:
            packet = []
            for n in range(0,len(data),2):
                dwell = self.decode_rdwell(data[n:n+2])
                packet.append(dwell)
            return packet

    def stream_to_buffer(self, raw_data):
        data = self.decode_rdwell_packet(raw_data)
        #print("cur x,y", self.current_x, self.current_y)
        
        if self.current_x > 0:
            
            partial_start_points = self.x_width - self.current_x
            #print("psp", partial_start_points)
            full_lines = ((len(data) - partial_start_points)//self.x_width)
            partial_end_points = ((len(data) - partial_start_points)%self.x_width)

            self.buffer[self.current_y][self.current_x:self.x_width] = data[0:partial_start_points]
            # print("rollover index", 0, ":", partial_start_points)
            # print("rollover data", data[0:partial_start_points])
            # print("top rollover")
            # print("top row", self.buffer[self.current_y])
            #print(self.buffer[self.current_y][self.current_x:self.x_width] )
            if self.current_y >= self.y_height - 1:
                self.current_y = 0
                #print("cy 0")
            else:
                self.current_y += 1
                #print("cy+1")
        else:
            #print("no top rollover")
            partial_start_points = 0
            partial_end_points = ((len(data))%self.x_width)
            full_lines = ((len(data))//self.x_width)
            
        for i in range(0,full_lines):
            
            #print("cy", self.current_y)
            #print("mid index", partial_start_points + i*self.x_width, ":",partial_start_points + (i+1)*self.x_width)
            self.buffer[self.current_y] = data[partial_start_points + i*self.x_width:partial_start_points + (i+1)*self.x_width]
            #print("midline", data[partial_start_points + i*self.x_width:partial_start_points + (i+1)*self.x_width])
            if self.current_y >= self.y_height - 1:
                self.current_y = 0
                #print("cy 0")
            else:
                self.current_y += 1
                #print("cy+1")
        
        self.buffer[self.current_y][0:partial_end_points] = data[self.x_width*full_lines + partial_start_points:self.x_width*full_lines + partial_start_points + partial_end_points]
        #print("bottom rollover", partial_end_points)
        #print("rollover index", self.x_width*full_lines + partial_start_points,":",self.x_width*full_lines + partial_start_points + partial_end_points)
        #print(self.buffer[self.current_y][0:partial_end_points])
        #print("last row")
        #print(self.buffer[self.current_y])
        
        self.current_x = partial_end_points
        assert (self.buffer[self.current_y][0] == 0)

        print(self.buffer)
        #print("=====")
