import amaranth
from amaranth import *
from amaranth.sim import Simulator
from amaranth.lib import data, enum
import os, sys

if "glasgow" in __name__: ## running as applet
    from ..gateware.multi_mode_controller import ModeController
    from ..gateware.data_latch_bus import BusMultiplexer
    from ..gateware.structs import *
    from ..gateware.configuration_handler import ConfigHandler
    from ..gateware.board_sim import OBI_Board
else:
    from board_sim import OBI_Board
    from multi_mode_controller import ModeController
    from data_latch_bus import BusMultiplexer
    from configuration_handler import ConfigHandler
    from structs import *

class IOBus(Elaboratable):
    def __init__(self, in_fifo, out_fifo, scan_mode, 
                x_full_resolution_b1, x_full_resolution_b2,
                y_full_resolution_b1, y_full_resolution_b2,
                x_upper_limit_b1, x_upper_limit_b2,
                x_lower_limit_b1, x_lower_limit_b2,
                y_upper_limit_b1, y_upper_limit_b2,
                y_lower_limit_b1, y_lower_limit_b2,
                eight_bit_output, do_frame_sync, do_line_sync,
                const_dwell_time, configuration, unpause, step_size,
                is_simulation = True, test_mode = None):
        ### Build arguments
        self.is_simulation = is_simulation
        self.test_mode = test_mode

        if self.is_simulation:
            self.board = OBI_Board()
        
        ### Modules
        self.mode_ctrl = ModeController(self.test_mode)
        self.bus_multiplexer = BusMultiplexer()
        #### FIFOs
        self.out_fifo = out_fifo
        self.in_fifo = in_fifo

        ## Top level control of fifo data flow
        self.write_strobe = Signal(reset=0)
        self.read_strobe = Signal()

        ## signals "pulled out" of other modules
        self.beam_controller_end_of_dwell = Signal()

        #### Registers
        self.scan_mode = scan_mode
        self.eight_bit_output = eight_bit_output
        self.do_frame_sync = do_frame_sync
        self.do_line_sync = do_line_sync
        self.const_dwell_time = const_dwell_time
        self.unpause = unpause

        self.step_size = step_size
        
        self.x_full_resolution_b1 = x_full_resolution_b1
        self.x_full_resolution_b2 = x_full_resolution_b2
        self.y_full_resolution_b1 = y_full_resolution_b1
        self.y_full_resolution_b2 = y_full_resolution_b2

        self.x_upper_limit_b1 = x_upper_limit_b1
        self.x_upper_limit_b2 = x_upper_limit_b2
        self.x_lower_limit_b1 = x_lower_limit_b1
        self.x_lower_limit_b2 = x_lower_limit_b2

        self.y_upper_limit_b1 = y_upper_limit_b1
        self.y_upper_limit_b2 = y_upper_limit_b2
        self.y_lower_limit_b1 = y_lower_limit_b1
        self.y_lower_limit_b2 = y_lower_limit_b2

        self.x_upper_limit = Signal(16)
        self.x_lower_limit = Signal(16)
        self.y_upper_limit = Signal(16)
        self.y_lower_limit = Signal(16)

        self.roi_registers = Signal(reduced_area_8)


        self.config_handler = ConfigHandler()
        self.configuration_flag = configuration
        self.handling_config = Signal()
        #### =============================================================================

        #### Ports A and B signals
        self.pins_i = Signal(14) ## Driven by pad.i value
        self.pins_o = Signal(14) ## Drives pad.o value

        #### Control signals
        self.x_latch = Signal()
        self.x_enable = Signal()
        self.y_latch = Signal()
        self.y_enable = Signal()
        self.a_latch = Signal()
        self.a_enable = Signal()

        self.a_clock = Signal()
        self.d_clock = Signal()


        ## For simulation purposes only
        self.x = Signal(16)
        self.y = Signal(16)
        self.d = Signal(16)

        #self.scan_mode = Signal(2)
        #self.alt_fifo = Signal()
    def elaborate(self, platform):
        m = Module()
        m.submodules["ModeCtrl"] = self.mode_ctrl
        #m.submodules["OutBus"] = self.output_bus
        m.submodules["MuxBus"] = self.bus_multiplexer
        m.submodules["OUT_FIFO"] = self.out_fifo
        m.submodules["IN_FIFO"] = self.in_fifo
        m.submodules["ConfigHdlr"] = self.config_handler
        if self.is_simulation:
            m.submodules["OBI_Board"] = self.board

        #### =========================== CONTROL SIGNALS ====================================
        m.d.comb += self.x_latch.eq(self.bus_multiplexer.x_dac.latch.le)
        m.d.comb += self.x_enable.eq(self.bus_multiplexer.x_dac.latch.oe)
        m.d.comb += self.y_latch.eq(self.bus_multiplexer.y_dac.latch.le)
        m.d.comb += self.y_enable.eq(self.bus_multiplexer.y_dac.latch.oe)
        m.d.comb += self.a_latch.eq(self.bus_multiplexer.a_adc.latch.le)
        m.d.comb += self.a_enable.eq(self.bus_multiplexer.a_adc.latch.oe)

        m.d.comb += self.a_clock.eq(self.bus_multiplexer.sample_clock.clock)
        m.d.comb += self.d_clock.eq(~self.bus_multiplexer.sample_clock.clock)

        if self.is_simulation:
            m.d.comb += self.board.x_latch.eq(self.x_latch)
            m.d.comb += self.board.y_latch.eq(self.y_latch)
            m.d.comb += self.board.a_latch.eq(self.a_latch)
            m.d.comb += self.board.a_clock.eq(self.a_clock)
            m.d.comb += self.board.d_clock.eq(self.d_clock)

        #### =============================================================================

        #### =========================== REGISTERS ====================================
        m.d.comb += self.roi_registers.LX1.eq(self.x_lower_limit_b2)
        m.d.comb += self.roi_registers.LX2.eq(self.x_lower_limit_b1)
        m.d.comb += self.roi_registers.UX1.eq(self.x_upper_limit_b2)
        m.d.comb += self.roi_registers.UX2.eq(self.x_upper_limit_b1)
        m.d.comb += self.roi_registers.LY1.eq(self.y_lower_limit_b2)
        m.d.comb += self.roi_registers.LY2.eq(self.y_lower_limit_b1)
        m.d.comb += self.roi_registers.UY1.eq(self.y_upper_limit_b2)
        m.d.comb += self.roi_registers.UY2.eq(self.y_upper_limit_b1)



        m.d.comb += self.config_handler.roi_registers.eq(self.roi_registers)

        m.d.comb += self.mode_ctrl.eight_bit_output.eq(self.config_handler.eight_bit_output_locked)
        m.d.comb += self.config_handler.scan_mode.eq(self.scan_mode)
        m.d.comb += self.config_handler.step_size.eq(self.step_size)
        m.d.comb += self.mode_ctrl.x_interpolator.step_size.eq(self.config_handler.step_size_locked)
        m.d.comb += self.mode_ctrl.y_interpolator.step_size.eq(self.config_handler.step_size_locked)
        
        m.d.comb += self.handling_config.eq((self.config_handler.writing_config))
        m.d.comb += self.config_handler.outer_configuration_flag.eq(self.configuration_flag)


        a = Signal()
        b = Signal()
        c = Signal()
        d = Signal()
        e = Signal()

        config_flag_latched = Signal()
        #m.d.sync += config_flag_latched.eq(self.configuration_flag)
        

        with m.If(self.unpause == 0):
            m.d.comb += self.config_handler.configuration_flag.eq(self.configuration_flag)
            #pass
        with m.Else():
            with m.If(self.configuration_flag):
                m.d.sync += config_flag_latched.eq(1)
            with m.If((config_flag_latched) & (self.mode_ctrl.writer_data_complete)):
                m.d.comb += self.config_handler.configuration_flag.eq(1)
                m.d.sync += config_flag_latched.eq(0)
                


        ## Reset counters when configuration changes
        m.d.comb += self.mode_ctrl.reset.eq(self.handling_config)
        m.d.comb += self.mode_ctrl.disable_dwell.eq((~(self.unpause))|(self.handling_config))

        with m.If(self.handling_config):
            m.d.comb += self.mode_ctrl.mode.eq(0)
        with m.Else():
            m.d.comb += self.mode_ctrl.mode.eq(self.scan_mode)

        with m.If(~(self.unpause)):
            m.d.comb += self.write_strobe.eq(0)
        
        eflnp = Signal() ## pipelined intermediate to make timing easier
        asdf = Signal() ## pipelined intermediate to make timing easier
        sdfg = Signal()
        m.d.sync += eflnp.eq(self.config_handler.config_flag_released)
        m.d.sync += asdf.eq(eflnp)
        # m.d.sync += sdfg.eq(asdf)
        m.d.comb += self.mode_ctrl.external_force_load_new_point.eq(asdf)

        #m.d.comb += self.mode_ctrl.external_force_load_new_point.eq(self.config_handler.config_flag_released)

        m.d.comb += self.beam_controller_end_of_dwell.eq(self.mode_ctrl.beam_controller.end_of_dwell)
        m.d.comb += self.mode_ctrl.const_dwell_time.eq(self.const_dwell_time)

        m.d.comb += self.config_handler.eight_bit_output.eq(self.eight_bit_output)
        m.d.comb += self.mode_ctrl.eight_bit_output.eq(self.config_handler.eight_bit_output_locked)

        m.d.comb += self.config_handler.x_full_frame_resolution_b1.eq(self.x_full_resolution_b1)
        m.d.comb += self.config_handler.x_full_frame_resolution_b2.eq(self.x_full_resolution_b2)
        m.d.comb += self.config_handler.y_full_frame_resolution_b1.eq(self.y_full_resolution_b1)
        m.d.comb += self.config_handler.y_full_frame_resolution_b2.eq(self.y_full_resolution_b2)

        m.d.comb += self.config_handler.x_upper_limit_b1.eq(self.x_upper_limit_b1)
        m.d.comb += self.config_handler.x_upper_limit_b2.eq(self.x_upper_limit_b2)
        m.d.comb += self.config_handler.x_lower_limit_b1.eq(self.x_lower_limit_b1)
        m.d.comb += self.config_handler.x_lower_limit_b2.eq(self.x_lower_limit_b2)

        m.d.comb += self.config_handler.y_upper_limit_b1.eq(self.y_upper_limit_b1)
        m.d.comb += self.config_handler.y_upper_limit_b2.eq(self.y_upper_limit_b2)
        m.d.comb += self.config_handler.y_lower_limit_b1.eq(self.y_lower_limit_b1)
        m.d.comb += self.config_handler.y_lower_limit_b2.eq(self.y_lower_limit_b2)


        m.d.comb += self.mode_ctrl.x_full_frame_resolution.eq(self.config_handler.x_full_frame_resolution_locked)
        m.d.comb += self.mode_ctrl.y_full_frame_resolution.eq(self.config_handler.y_full_frame_resolution_locked)

        m.d.comb += self.mode_ctrl.xy_scan_gen.x_upper_limit.eq(self.config_handler.roi_registers_locked.UX)
        m.d.comb += self.mode_ctrl.xy_scan_gen.x_lower_limit.eq(self.config_handler.roi_registers_locked.LX)
        m.d.comb += self.mode_ctrl.xy_scan_gen.y_upper_limit.eq(self.config_handler.roi_registers_locked.UY)
        m.d.comb += self.mode_ctrl.xy_scan_gen.y_lower_limit.eq(self.config_handler.roi_registers_locked.LY) 

        #### =============================================================================


        #### =========================="BUS STATE MACHINE"==================================
        m.d.comb += self.bus_multiplexer.sampling.eq(self.mode_ctrl.beam_controller.dwelling)

        if self.test_mode == "fast clock":
            ### min dwell time is one actual clock cycle
            m.d.comb += self.mode_ctrl.beam_controller.count_enable.eq(1)
        else:
            m.d.comb += self.mode_ctrl.beam_controller.count_enable.eq(self.bus_multiplexer.is_done)

        with m.If(self.bus_multiplexer.is_x):
            m.d.comb += self.pins_o.eq(self.mode_ctrl.beam_controller.x_position)
            if self.is_simulation:
                m.d.comb += self.board.x_latch_chip.d.eq(self.pins_o)
        with m.If(self.bus_multiplexer.is_y):
            m.d.comb += self.pins_o.eq(self.mode_ctrl.beam_controller.y_position)
            if self.is_simulation:
                m.d.comb += self.board.y_latch_chip.d.eq(self.pins_o)
        with m.If(self.bus_multiplexer.is_a):
            m.d.comb += self.mode_ctrl.adc_data_strobe.eq(self.bus_multiplexer.a_adc.released)
            if self.is_simulation:
                m.d.sync += self.board.adc_input.eq(self.mode_ctrl.adc_data)
            if self.test_mode == "data loopback":
                with m.If(self.scan_mode == ScanMode.Raster):
                    m.d.comb += self.mode_ctrl.adc_data.eq(self.mode_ctrl.beam_controller.x_position)
                with m.If((self.scan_mode == ScanMode.Vector)|(self.scan_mode == ScanMode.RasterPattern)):
                    m.d.comb += self.mode_ctrl.adc_data.eq(self.mode_ctrl.beam_controller.dwell_time)
            else:
                m.d.comb += self.mode_ctrl.adc_data.eq(self.pins_i)

        if self.is_simulation:
            self.board.adc_input.eq(self.mode_ctrl.adc_data)
        #### =============================================================================

        #### ===========================FIFO CONTROL=================================================
        
        '''
        read_strobe: Signal, 1, in
            This signal is high when:
                - the out fifo is ready to be read from, AND
                - the "reader" module has NOT recieved a complete data point
        read_happened: Signal, 1, out
            This signal is driven by read_strobe
            out_fifo.r_en is also driven by read_strobe

        write_strobe: Signal, 1, in
            This signal is high when:
                - the in fifo is ready to be written to, AND
                - the "writer" module has valid data to write
        write_happened: Signal, 1, out
            This signal is driven by write_strobe
            in_fifo.w_en is also driven by write_strobe
        '''

        m.d.comb += self.read_strobe.eq((~(self.mode_ctrl.reader_data_complete))&(self.out_fifo.r_rdy))
        m.d.comb += self.mode_ctrl.out_fifo_r_data.eq(self.out_fifo.r_data)
        m.d.comb += self.mode_ctrl.read_happened.eq((self.read_strobe))

        with m.If((self.handling_config)):
            m.d.comb += self.write_strobe.eq((self.in_fifo.w_rdy) & (self.config_handler.config_data_valid))
            m.d.comb += self.config_handler.write_happened.eq((self.write_strobe) & (self.unpause))
        with m.Else():
            m.d.comb += self.write_strobe.eq((self.in_fifo.w_rdy) & (self.mode_ctrl.writer_data_valid))
            m.d.comb += self.mode_ctrl.write_happened.eq((self.write_strobe) & (self.unpause))

        
        m.d.comb += self.mode_ctrl.write_ready.eq(self.in_fifo.w_rdy)


        if self.test_mode == "loopback":
            m.d.comb += self.in_fifo.w_data.eq(self.out_fifo.r_data)
            with m.If(self.in_fifo.w_rdy & self.out_fifo.r_rdy):
                m.d.comb += self.in_fifo.w_en.eq(1)
                m.d.comb += self.out_fifo.r_en.eq(1)

        if self.test_mode == "sync loopback":
            loopback = Signal(8, reset = 3)
            m.d.sync += loopback.eq(self.out_fifo.r_data)
            m.d.sync += self.in_fifo.w_data.eq(loopback)
            with m.If(self.in_fifo.w_rdy):
                m.d.comb += self.in_fifo.w_en.eq(1)
            with m.If(self.out_fifo.r_rdy):
                m.d.comb += self.out_fifo.r_en.eq(1)
                
        else:
            with m.If(self.unpause):
                with m.If(self.handling_config):
                    m.d.comb += self.in_fifo.w_data.eq(self.config_handler.in_fifo_w_data)
                with m.Else():
                    m.d.comb += self.in_fifo.w_data.eq(self.mode_ctrl.in_fifo_w_data)

            with m.If((self.write_strobe)&(self.unpause)):
                if self.test_mode == "disable output":
                    pass
                else:
                    m.d.comb += self.in_fifo.w_en.eq(1)
            with m.If(self.read_strobe):
                m.d.comb += self.out_fifo.r_en.eq(1)

        #### =============================================================================

        return m

    
## see simulation.py for the full simulation