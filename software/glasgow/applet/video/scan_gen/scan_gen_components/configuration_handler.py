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
        self.scan_mode_locked = Signal(2)
        self.eight_bit_output = Signal()

        self.configuration_flag = Signal()

        self.in_fifo_w_data = Signal(8)
        self.config_data_valid = Signal()
        self.write_happened = Signal()

        self.writing_config = Signal()

    

    def elaborate(self, platform):
        m = Module()

        l = Signal()

        with m.FSM() as fsm:
            with m.State("Latch"):
                m.d.comb += l.eq(1)
                m.d.comb += self.writing_config.eq(0)
                m.d.comb += self.config_data_valid.eq(0)
                with m.If(self.configuration_flag):
                    m.d.comb += self.writing_config.eq(1)
                    m.d.sync += self.x_full_frame_resolution_locked.eq(Cat(self.x_full_frame_resolution_b2,
                                                                            self.x_full_frame_resolution_b1))
                    m.d.sync += self.y_full_frame_resolution_locked.eq(Cat(self.y_full_frame_resolution_b2,
                                                                            self.y_full_frame_resolution_b1))
                    m.d.comb += self.config_data_valid.eq(1)
                    m.d.comb += self.in_fifo_w_data.eq(0)
                    with m.If(self.write_happened):
                        m.next = "X1"
                    with m.Else():
                        m.next = "Insert_Start"
            with m.State("Insert_Start"):
                m.d.comb += self.writing_config.eq(1)
                m.d.comb += self.config_data_valid.eq(1)
                with m.If(self.write_happened):
                    m.d.comb += self.in_fifo_w_data.eq(0)
                    m.next = "X1"
            with m.State("X1"):
                m.d.comb += self.writing_config.eq(1)
                m.d.comb += self.config_data_valid.eq(1)
                with m.If(self.write_happened):
                    m.d.comb += self.in_fifo_w_data.eq(self.x_full_frame_resolution_b2)
                    m.next = "X2"
            with m.State("X2"):
                m.d.comb += l.eq(1)
                m.d.comb += self.writing_config.eq(1)
                m.d.comb += self.config_data_valid.eq(1)
                with m.If(self.write_happened):
                    m.d.comb += self.in_fifo_w_data.eq(self.x_full_frame_resolution_b1)
                    m.next = "Y1"
            with m.State("Y1"):
                m.d.comb += l.eq(1)
                m.d.comb += self.writing_config.eq(1)
                m.d.comb += self.config_data_valid.eq(1)
                with m.If(self.write_happened):
                    m.d.comb += self.in_fifo_w_data.eq(self.y_full_frame_resolution_b2)
                    m.next = "Y2"
            with m.State("Y2"):
                m.d.comb += self.writing_config.eq(1)
                m.d.comb += self.config_data_valid.eq(1)
                with m.If(self.write_happened):
                    m.d.comb += self.in_fifo_w_data.eq(self.y_full_frame_resolution_b1)
                    m.next = "Insert_End"
            with m.State("Insert_End"):
                m.d.comb += self.writing_config.eq(1)
                m.d.comb += self.config_data_valid.eq(1)
                with m.If(self.write_happened):
                    m.d.comb += self.in_fifo_w_data.eq(0)
                    with m.If(~self.configuration_flag):
                        m.next = "Latch"
                    with m.Else():
                        m.next = "Wait_unlatch"
            with m.State("Wait_unlatch"):
                m.d.comb += self.config_data_valid.eq(0)
                m.d.comb += self.writing_config.eq(0)
                with m.If(~self.configuration_flag):
                    m.next = "Latch"



        return m