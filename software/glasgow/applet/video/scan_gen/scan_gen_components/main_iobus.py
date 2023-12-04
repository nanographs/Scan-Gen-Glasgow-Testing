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
                is_simulation = True, test_mode = None):
        self.is_simulation = is_simulation
        self.test_mode = test_mode
        
        self.out_fifo = out_fifo
        self.in_fifo = in_fifo
        self.scan_mode = scan_mode
        self.x_full_resolution_b1 = x_full_resolution_b1
        self.x_full_resolution_b2 = x_full_resolution_b2
        self.y_full_resolution_b1 = y_full_resolution_b1
        self.y_full_resolution_b2 = y_full_resolution_b2

        self.mode_ctrl = ModeController()

        self.bus_multiplexer = BusMultiplexer()
        self.pins = Signal(14)

        self.x_latch = Signal()
        self.x_enable = Signal()
        self.y_latch = Signal()
        self.y_enable = Signal()
        self.a_latch = Signal()
        self.a_enable = Signal()

        self.a_clock = Signal()
        self.d_clock = Signal()

        self.io_strobe = Signal()

        self.x = Signal(16)
        self.y = Signal(16)
        self.d = Signal(16)

        #self.scan_mode = Signal(2)
        self.alt_fifo = Signal()
    def elaborate(self, platform):
        m = Module()
        m.submodules["ModeCtrl"] = self.mode_ctrl
        #m.submodules["OutBus"] = self.output_bus
        m.submodules["MuxBus"] = self.bus_multiplexer
        m.submodules["OUT_FIFO"] = self.out_fifo
        m.submodules["IN_FIFO"] = self.in_fifo

        m.d.comb += self.x_latch.eq(self.bus_multiplexer.x_dac.latch.le)
        m.d.comb += self.x_enable.eq(self.bus_multiplexer.x_dac.latch.oe)
        m.d.comb += self.y_latch.eq(self.bus_multiplexer.y_dac.latch.le)
        m.d.comb += self.y_enable.eq(self.bus_multiplexer.y_dac.latch.oe)
        m.d.comb += self.a_latch.eq(self.bus_multiplexer.a_adc.latch.le)
        m.d.comb += self.a_enable.eq(self.bus_multiplexer.a_adc.latch.oe)

        m.d.comb += self.a_clock.eq(self.bus_multiplexer.sample_clock.clock)
        m.d.comb += self.d_clock.eq(self.bus_multiplexer.sample_clock.clock)


        #m.d.comb += self.scan_mode.eq(ScanMode.Raster)
        m.d.comb += self.mode_ctrl.mode.eq(self.scan_mode)
        m.d.comb += self.mode_ctrl.ras_mode_ctrl.xy_scan_gen.x_full_frame_resolution.eq(Cat(self.x_full_resolution_b2,
                                                                                            self.x_full_resolution_b1))
        m.d.comb += self.mode_ctrl.ras_mode_ctrl.xy_scan_gen.y_full_frame_resolution.eq(Cat(self.y_full_resolution_b2,
                                                                                            self.y_full_resolution_b1))

        with m.If(self.bus_multiplexer.is_x):
            m.d.comb += self.pins.eq(self.mode_ctrl.beam_controller.x_position)
        with m.If(self.bus_multiplexer.is_y):
            m.d.comb += self.pins.eq(self.mode_ctrl.beam_controller.x_position)
        #with m.If(self.bus_multiplexer.is_a):
            #m.d.comb += self.output_bus.in_fifo.w_data.eq(self.mode_ctrl.beam_controller.dwell_time)
            # if self.is_simulation:
            #     m.d.comb += self.output_bus.video_sink.pixel_in.eq(self.input_bus.mode_controller.beam_controller.dwell_time)
            # else:
            #     m.d.comb += self.output_bus.video_sink.pixel_in.eq(self.pins)
            # Loopback

        with m.If(self.mode_ctrl.mode == ScanMode.Vector):
            m.d.comb += self.io_strobe.eq((self.in_fifo.w_rdy) & (self.out_fifo.r_rdy) & (self.mode_ctrl.internal_fifo_ready))

        with m.If(self.mode_ctrl.mode == ScanMode.Raster):
            m.d.comb += self.io_strobe.eq((self.in_fifo.w_rdy))
            
        m.d.comb += self.mode_ctrl.out_fifo_r_data.eq(self.out_fifo.r_data)
        m.d.comb += self.mode_ctrl.output_enable.eq(self.io_strobe)

        m.d.sync += self.bus_multiplexer.sampling.eq(self.mode_ctrl.beam_controller.dwelling)

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
            
            with m.If(self.io_strobe):
                # with m.If(self.mode_ctrl.ras_mode_ctrl.raster_fifo.r_rdy):
                #     m.d.comb += self.mode_ctrl.ras_mode_ctrl.raster_fifo.r_en.eq(1)
                #     m.d.comb += self.in_fifo.w_data.eq(self.mode_ctrl.ras_mode_ctrl.raster_fifo.r_data)
                #     with m.If(~(self.mode_ctrl.output_strobe_out)):
                #         m.d.comb += self.in_fifo.w_en.eq(1)
                # with m.Else():
                m.d.comb += self.in_fifo.w_data.eq(self.mode_ctrl.in_fifo_w_data)
                m.d.comb += self.out_fifo.r_en.eq(1)
                with m.If(~(self.mode_ctrl.output_strobe_out)):
                    m.d.comb += self.in_fifo.w_en.eq(1)
            # with m.If(~self.in_fifo.w_rdy):
            #     m.d.sync += self.alt_fifo.eq(1)
            # with m.If(self.in_fifo.level == 0):
            #     m.d.sync += self.alt_fifo.eq(0)
            #     m.d.comb += self.io_strobe.eq((self.mode_ctrl.ras_mode_ctrl.raster_fifo.w_rdy))
            #     m.d.comb += self.mode_ctrl.ras_mode_ctrl.raster_fifo.w_data.eq(self.mode_ctrl.in_fifo_w_data)
            #     with m.If(~(self.mode_ctrl.output_strobe_out)):
            #         m.d.comb += self.mode_ctrl.ras_mode_ctrl.raster_fifo.w_en.eq(1)


        return m

    
## see simulation.py for the full simulation