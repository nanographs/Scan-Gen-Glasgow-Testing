import amaranth
from amaranth import *
from amaranth.sim import Simulator
from amaranth.lib import data, enum
import os, sys

if "glasgow" in __name__: ## running as applet
    from ..scan_gen_components.multi_mode_controller import ModeController
    from ..scan_gen_components.data_latch_bus import BusMultiplexer
    from ..scan_gen_components.addresses import *
else:
    from multi_mode_controller import ModeController
    from data_latch_bus import BusMultiplexer
    from addresses import *

class IOBus(Elaboratable):
    def __init__(self, in_fifo, out_fifo, scan_mode, 
                x_full_resolution_b1, x_full_resolution_b2,
                y_full_resolution_b1, y_full_resolution_b2,
                x_upper_limit_b1, x_upper_limit_b2,
                x_lower_limit_b1, x_lower_limit_b2,
                y_upper_limit_b1, y_upper_limit_b2,
                y_lower_limit_b1, y_lower_limit_b2,
                eight_bit_output, do_frame_sync, do_line_sync,
                const_dwell_time,
                is_simulation = True, test_mode = None):
        ### Build arguments
        self.is_simulation = is_simulation
        self.test_mode = test_mode
        
        ### Modules
        self.mode_ctrl = ModeController()
        self.bus_multiplexer = BusMultiplexer()
        #### FIFOs
        self.out_fifo = out_fifo
        self.in_fifo = in_fifo

        ## Top level control of fifo data flow
        self.write_strobe = Signal()
        self.read_strobe = Signal()

        #### Registers
        self.scan_mode = scan_mode
        self.eight_bit_output = eight_bit_output
        self.do_frame_sync = do_frame_sync
        self.do_line_sync = do_line_sync
        self.const_dwell_time = const_dwell_time

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

        #### =========================== CONTROL SIGNALS ====================================
        m.d.comb += self.x_latch.eq(self.bus_multiplexer.x_dac.latch.le)
        m.d.comb += self.x_enable.eq(self.bus_multiplexer.x_dac.latch.oe)
        m.d.comb += self.y_latch.eq(self.bus_multiplexer.y_dac.latch.le)
        m.d.comb += self.y_enable.eq(self.bus_multiplexer.y_dac.latch.oe)
        m.d.comb += self.a_latch.eq(self.bus_multiplexer.a_adc.latch.le)
        m.d.comb += self.a_enable.eq(self.bus_multiplexer.a_adc.latch.oe)

        m.d.comb += self.a_clock.eq(self.bus_multiplexer.sample_clock.clock)
        m.d.comb += self.d_clock.eq(~self.bus_multiplexer.sample_clock.clock)
        #### =============================================================================

        #### =========================== REGISTERS ====================================
        m.d.comb += self.mode_ctrl.const_dwell_time.eq(self.const_dwell_time)
        m.d.comb += self.mode_ctrl.mode.eq(self.scan_mode)
        m.d.comb += self.mode_ctrl.eight_bit_output.eq(self.eight_bit_output)
        m.d.comb += self.mode_ctrl.ras_mode_ctrl.do_frame_sync.eq(self.do_frame_sync)
        m.d.comb += self.mode_ctrl.ras_mode_ctrl.do_line_sync.eq(self.do_line_sync)

        m.d.comb += self.mode_ctrl.x_full_frame_resolution.eq(Cat(self.x_full_resolution_b2,
                                                                self.x_full_resolution_b1))
        m.d.comb += self.mode_ctrl.y_full_frame_resolution.eq(Cat(self.y_full_resolution_b2,
                                                                self.y_full_resolution_b1))

        m.d.comb += self.x_upper_limit.eq(Cat(self.x_upper_limit_b2,self.x_upper_limit_b1))
        m.d.comb += self.x_lower_limit.eq(Cat(self.x_lower_limit_b2,self.x_lower_limit_b1))
        m.d.comb += self.y_upper_limit.eq(Cat(self.y_upper_limit_b2,self.y_upper_limit_b1))                                                                        
        m.d.comb += self.y_lower_limit.eq(Cat(self.y_lower_limit_b2,self.y_lower_limit_b1))

        m.d.comb += self.mode_ctrl.ras_mode_ctrl.xy_scan_gen.x_upper_limit.eq(self.x_upper_limit)
        m.d.comb += self.mode_ctrl.ras_mode_ctrl.xy_scan_gen.x_lower_limit.eq(self.x_lower_limit)
        m.d.comb += self.mode_ctrl.ras_mode_ctrl.xy_scan_gen.y_upper_limit.eq(self.y_upper_limit)
        m.d.comb += self.mode_ctrl.ras_mode_ctrl.xy_scan_gen.y_lower_limit.eq(self.y_lower_limit)
        #### =============================================================================


        #### =========================="BUS STATE MACHINE"==================================
        m.d.sync += self.bus_multiplexer.sampling.eq(self.mode_ctrl.beam_controller.dwelling)

        if self.test_mode == "fast clock":
            ### min dwell time is one actual clock cycle
            m.d.comb += self.mode_ctrl.beam_controller.count_enable.eq(1)
        else:
            m.d.comb += self.mode_ctrl.beam_controller.count_enable.eq(self.bus_multiplexer.is_done)

        with m.If(self.bus_multiplexer.is_x):
            m.d.comb += self.pins_o.eq(self.mode_ctrl.beam_controller.x_position)
        with m.If(self.bus_multiplexer.is_y):
            m.d.comb += self.pins_o.eq(self.mode_ctrl.beam_controller.y_position)
        with m.If(self.bus_multiplexer.is_a):
            m.d.comb += self.mode_ctrl.adc_data_strobe.eq(self.bus_multiplexer.a_adc.released)
            if self.test_mode == "data loopback":
                with m.If(self.scan_mode == ScanMode.Raster):
                    m.d.comb += self.mode_ctrl.adc_data.eq(self.mode_ctrl.beam_controller.x_position)
                with m.If((self.scan_mode == ScanMode.Vector)|(self.scan_mode == ScanMode.RasterPattern)):
                    m.d.comb += self.mode_ctrl.adc_data.eq(self.mode_ctrl.beam_controller.dwell_time)
            else:
                m.d.comb += self.mode_ctrl.adc_data.eq(self.pins_i)
        #### =============================================================================

        #### ===========================FIFO CONTROL=================================================
        with m.If(self.mode_ctrl.mode == ScanMode.Vector):
            #m.d.comb += self.io_strobe.eq((self.in_fifo.w_rdy) & ((self.out_fifo.r_rdy) & (self.mode_ctrl.internal_fifo_ready)))
            m.d.comb += self.write_strobe.eq((self.in_fifo.w_rdy) & (~self.mode_ctrl.write_strobe))
            m.d.comb += self.read_strobe.eq(self.out_fifo.r_rdy)

        with m.If(self.mode_ctrl.mode == ScanMode.RasterPattern):
            #m.d.comb += self.io_strobe.eq((self.in_fifo.w_rdy) & ((self.out_fifo.r_rdy)))
            m.d.comb += self.write_strobe.eq((self.in_fifo.w_rdy) & (~self.mode_ctrl.write_strobe))
            m.d.comb += self.read_strobe.eq(self.out_fifo.r_rdy)

        with m.If(self.mode_ctrl.mode == ScanMode.Raster):
            #m.d.comb += self.io_strobe.eq((self.in_fifo.w_rdy))
            m.d.comb += self.write_strobe.eq((self.in_fifo.w_rdy) & (~self.mode_ctrl.write_strobe))
            m.d.comb += self.read_strobe.eq(self.out_fifo.r_rdy)
            
        m.d.comb += self.mode_ctrl.out_fifo_r_data.eq(self.out_fifo.r_data)
        m.d.comb += self.mode_ctrl.write_enable.eq(self.in_fifo.w_rdy)
        m.d.comb += self.mode_ctrl.read_enable.eq(self.out_fifo.r_rdy)

        

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
            m.d.comb += self.in_fifo.w_data.eq(self.mode_ctrl.in_fifo_w_data)
            with m.If(self.write_strobe):
                if self.test_mode == "disable output":
                    pass
                else:
                    m.d.comb += self.in_fifo.w_en.eq(1)
            with m.If(self.read_strobe):
                m.d.comb += self.out_fifo.r_en.eq(1)

        #### =============================================================================

        return m

    
## see simulation.py for the full simulation