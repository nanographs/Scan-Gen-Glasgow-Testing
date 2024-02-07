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


