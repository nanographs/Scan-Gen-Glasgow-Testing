from amaranth import *
from amaranth.sim import Simulator


class ConfigHandler(Elaboratable):
    def __init__(self):
        self.x_full_frame_resolution_b1 = Signal(8)
        self.x_full_frame_resolution_b2 = Signal(8)
        self.y_full_frame_resolution_b1 = Signal(8)
        self.y_full_frame_resolution_b2 = Signal(8)

        self.x_full_frame_resolution_locked = Signal(16)
        self.y_full_frame_resolution_locked = Signal(16)

        self.x_lower_limit_b1 = Signal(8)
        self.x_lower_limit_b2 = Signal(8)
        self.x_upper_limit_b1 = Signal(8)
        self.x_upper_limit_b2 = Signal(8)

        self.x_lower_limit_locked = Signal(16)
        self.x_upper_limit_locked = Signal(16)

        self.y_lower_limit_b1 = Signal(8)
        self.y_lower_limit_b2 = Signal(8)
        self.y_upper_limit_b1 = Signal(8)
        self.y_upper_limit_b2 = Signal(8)

        self.y_lower_limit_locked = Signal(16)
        self.y_upper_limit_locked = Signal(16)
        
        self.scan_mode = Signal(2)
        self.eight_bit_output = Signal()

        self.configuration_flag = Signal()

    def elaborate(self):
        m = Module()


        return m