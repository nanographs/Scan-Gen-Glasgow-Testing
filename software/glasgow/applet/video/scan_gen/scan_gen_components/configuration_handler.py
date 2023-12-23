from amaranth import *
from amaranth.sim import Simulator


class ConfigHandler(Elaboratable):
    '''
    Inserts a demarcated "packet" into the outgoing data stream, 
    which contains the current operating parameters.

    configuration_flag: Signal, in, 1
        This value is set by the configuration register and can be
        externally updated. Once this value is asserted, the config
        writing state machine is initiated
    writing_config: Signal, out, 1
        This value is high while the config writing state machine is
        still ongoing.
    
        Short pulse:
            configuration_flag: __-______
            writing_config:     __-------_
        Long pulse:
            configuration_flag: __---------_
            writing_config:     __-------___

    State Machine:
            ↓--------------------------------------------------------------↑------↑
        Latch -> SB1 -> SB2 -> X1 -> X2 -> Y1 -> Y2 -> SC -> 8B -> EB1 -> EB2 -> Wait
            ↳------------↑ 


    Registers that are "locked in" by strobing configuration:
        eight_bit_output: Signal, in, 1

        x_full_frame_resolution_b1: Signal, in, 8
        x_full_frame_resolution_b2: Signal, in, 8
                            ↓
        x_full_frame_resolution_locked: Signal, out, 16

        y_full_frame_resolution_b1: Signal, in, 8
        y_full_frame_resolution_b2: Signal, in, 8
                            ↓
        y_full_frame_resolution_locked: Signal, out, 16

        ... repeat for x and y lower and upper limits

        scan_mode: Signal, in, 1
            This register is not locked in by strobing configuration, but its 
            instantaneous value is included in the configuration packet
    
    in_fifo_w_data: Signal, in, 8
        If writing_config is high, this signal combinatorially drives 
        the top level in_fifo.w_data
    config_data_valid: Signal, out, 1
        If high, the value of in_fifo_w_data should be written 
    write_happened: Signal, in, 1
        If high, in_fifo.w_en is also high

    '''               
    def __init__(self, demarcator = 255):
        self.demarcator = 255

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
        self.eight_bit_output_locked = Signal()

        self.configuration_flag = Signal()
        self.outer_configuration_flag = Signal()

        self.in_fifo_w_data = Signal(8)
        self.config_data_valid = Signal()
        self.write_happened = Signal()

        self.writing_config = Signal()


    def elaborate(self, platform):
        m = Module()

        l = Signal()

        with m.FSM() as fsm:
            with m.State("Latch"):
                m.d.comb += self.writing_config.eq(0)
                m.d.comb += self.config_data_valid.eq(0)
                with m.If(self.configuration_flag):
                    #m.d.comb += self.writing_config.eq(1)
                    m.d.sync += self.x_full_frame_resolution_locked.eq(Cat(self.x_full_frame_resolution_b2,
                                                                            self.x_full_frame_resolution_b1))
                    m.d.sync += self.y_full_frame_resolution_locked.eq(Cat(self.y_full_frame_resolution_b2,
                                                                            self.y_full_frame_resolution_b1))
                    m.d.sync += self.eight_bit_output_locked.eq(self.eight_bit_output)
                    #m.d.comb += self.config_data_valid.eq(1)
                    m.d.comb += self.in_fifo_w_data.eq(self.demarcator)
                    with m.If(self.write_happened):
                        m.next = "Insert_Start_B2"
                    with m.Else():
                        m.next = "Insert_Start"
            with m.State("Insert_Start"):
                m.d.comb += self.writing_config.eq(1)
                m.d.comb += self.config_data_valid.eq(1)
                with m.If(self.write_happened):
                    m.d.comb += self.in_fifo_w_data.eq(self.demarcator)
                    m.next = "Insert_Start_B2"
            with m.State("Insert_Start_B2"):
                m.d.comb += self.writing_config.eq(1)
                m.d.comb += self.config_data_valid.eq(1)
                with m.If(self.write_happened):
                    m.d.comb += self.in_fifo_w_data.eq(self.demarcator)
                    m.next = "X1"
            with m.State("X1"):
                m.d.comb += self.writing_config.eq(1)
                m.d.comb += self.config_data_valid.eq(1)
                with m.If(self.write_happened):
                    m.d.comb += self.in_fifo_w_data.eq(self.x_full_frame_resolution_b1)
                    m.next = "X2"
            with m.State("X2"):
                m.d.comb += self.writing_config.eq(1)
                m.d.comb += self.config_data_valid.eq(1)
                with m.If(self.write_happened):
                    m.d.comb += self.in_fifo_w_data.eq(self.x_full_frame_resolution_b2)
                    m.next = "Y1"
            with m.State("Y1"):
                m.d.comb += self.writing_config.eq(1)
                m.d.comb += self.config_data_valid.eq(1)
                with m.If(self.write_happened):
                    m.d.comb += self.in_fifo_w_data.eq(self.y_full_frame_resolution_b1)
                    m.next = "Y2"
            with m.State("Y2"):
                m.d.comb += self.writing_config.eq(1)
                m.d.comb += self.config_data_valid.eq(1)
                with m.If(self.write_happened):
                    m.d.comb += self.in_fifo_w_data.eq(self.y_full_frame_resolution_b2)
                    m.next = "SC"
            with m.State("SC"):
                m.d.comb += self.writing_config.eq(1)
                m.d.comb += self.config_data_valid.eq(1)
                with m.If(self.write_happened):
                    m.d.comb += self.in_fifo_w_data.eq(self.scan_mode)
                    m.next = "8B"
            with m.State("8B"):
                m.d.comb += self.writing_config.eq(1)
                m.d.comb += self.config_data_valid.eq(1)
                with m.If(self.write_happened):
                    m.d.comb += self.in_fifo_w_data.eq(self.eight_bit_output)
                    m.next = "Insert_End_B1"
            with m.State("Insert_End_B1"):
                m.d.comb += self.writing_config.eq(1)
                m.d.comb += self.config_data_valid.eq(1)
                with m.If(self.write_happened):
                    m.d.comb += self.in_fifo_w_data.eq(self.demarcator)
                    m.next = "Insert_End"
            with m.State("Insert_End"):
                m.d.comb += self.writing_config.eq(1)
                m.d.comb += self.config_data_valid.eq(1)
                with m.If(self.write_happened):
                    m.d.comb += self.in_fifo_w_data.eq(self.demarcator)
                    with m.If(~self.outer_configuration_flag):
                        m.next = "Latch"
                    with m.Else():
                        m.next = "Wait_unlatch"
            with m.State("Wait_unlatch"):
                m.d.comb += self.config_data_valid.eq(0)
                m.d.comb += self.writing_config.eq(0)
                m.d.comb += l.eq(1)
                with m.If(~self.outer_configuration_flag):
                    m.next = "Latch"



        return m