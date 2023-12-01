import amaranth
from amaranth import *
from amaranth.sim import Simulator
from amaranth.lib import data, enum
import os, sys

if "glasgow" in __name__: ## running as applet
    #from ..scan_gen_components.output_bus import OutputBus
    #from ..scan_gen_components.multimode_input import InputBus
    from ..scan_gen_components.multi_mode_controller import ModeController
    from ..scan_gen_components.data_latch_bus import BusMultiplexer
    from ..scan_gen_components.addresses import *
else:
    #from multimode_input import InputBus
    from multi_mode_controller import ModeController
    #from output_bus import OutputBus
    from data_latch_bus import BusMultiplexer
    from addresses import *
    sys.path.append("/Users/isabelburgos/Scan-Gen-Glasgow-Testing/software")
    from glasgow import *
    from glasgow.access.simulation import SimulationMultiplexerInterface, SimulationDemultiplexerInterface


# sim_iface = SimulationMultiplexerInterface()

class IOBus(Elaboratable):
    def __init__(self, in_fifo, out_fifo, is_simulation, test_mode = None, mode = "Raster"):
        self.is_simulation = is_simulation
        self.test_mode = test_mode
        self.mode = mode
        
        self.out_fifo = out_fifo
        self.in_fifo = in_fifo
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

        if self.mode == "Vector":
            m.d.comb += self.mode_ctrl.vector_input.out_fifo_r_data.eq(self.out_fifo.r_data)
            m.d.comb += self.mode_ctrl.vector_input.out_fifo_r_en.eq(self.out_fifo.r_en)

            m.d.comb += self.io_strobe.eq((self.in_fifo.w_rdy) & (self.out_fifo.r_rdy) & (self.mode_ctrl.vector_fifo.w_rdy))
            m.d.comb += self.mode_ctrl.vector_input.enable.eq(self.io_strobe)
            m.d.comb += self.mode_ctrl.vector_output.enable.eq(self.io_strobe)

            ### x, y, d top level signals for simulation viewing purposes lol
            m.d.comb += self.x.eq(Cat(self.mode_ctrl.vector_input.vector_point_data_c.X1, self.mode_ctrl.vector_input.vector_point_data_c.X2))
            m.d.comb += self.y.eq(Cat(self.mode_ctrl.vector_input.vector_point_data_c.Y1, self.mode_ctrl.vector_input.vector_point_data_c.Y2))
            m.d.comb += self.d.eq(Cat(self.mode_ctrl.vector_input.vector_point_data_c.D1, self.mode_ctrl.vector_input.vector_point_data_c.D2))
        else: 
            m.d.comb += self.io_strobe.eq((self.in_fifo.w_rdy))
            #m.d.comb += self.mode_ctrl.vector_output.enable.eq(self.io_strobe)
            m.d.comb += self.mode_ctrl.output_enable.eq(self.io_strobe)

        m.d.sync += self.bus_multiplexer.sampling.eq(self.mode_ctrl.beam_controller.dwelling)
        #m.d.sync += self.bus_multiplexer.sampling.eq(0)
        with m.If(self.bus_multiplexer.is_x):
            #m.d.comb += self.pins.eq(self.input_bus.mode_controller.beam_controller.x_position)
            m.d.comb += self.pins.eq(self.mode_ctrl.beam_controller.x_position)
        with m.If(self.bus_multiplexer.is_y):
            #m.d.comb += self.pins.eq(self.input_bus.mode_controller.beam_controller.y_position)
            m.d.comb += self.pins.eq(self.mode_ctrl.beam_controller.x_position)
        #with m.If(self.bus_multiplexer.is_a):
            #m.d.comb += self.output_bus.in_fifo.w_data.eq(self.mode_ctrl.beam_controller.dwell_time)
            # if self.is_simulation:
            #     m.d.comb += self.output_bus.video_sink.pixel_in.eq(self.input_bus.mode_controller.beam_controller.dwell_time)
            # else:
            #     m.d.comb += self.output_bus.video_sink.pixel_in.eq(self.pins)
            # Loopback
        #m.d.comb += self.output_bus.in_fifo.w_data.eq(self.mode_ctrl.beam_controller.dwell_time)
        #m.d.comb += self.output_bus.video_sink.dwelling.eq(self.mode_ctrl.beam_controller.dwelling)
        #m.d.comb += self.output_bus.video_sink.dwell_time_averager.start_new_average.eq(self.mode_ctrl.beam_controller.end_of_dwell)
        #m.d.comb += self.output_bus.strobe.eq(self.bus_multiplexer.a_adc.released)
        #m.d.comb += self.output_bus.strobe.eq(self.mode_ctrl.beam_controller.end_of_dwell)
        #m.d.comb += self.output_bus.strobe.eq(1)


        if self.test_mode == "loopback":
            m.d.comb += self.in_fifo.w_data.eq(self.out_fifo.r_data)
            with m.If(self.in_fifo.w_rdy & self.out_fifo.r_rdy):
                m.d.comb += self.in_fifo.w_en.eq(1)
                m.d.comb += self.out_fifo.r_en.eq(1)

        else:
            if self.mode == "Vector":
                m.d.comb += self.in_fifo.w_data.eq(self.mode_ctrl.vector_output.in_fifo_w_data)
                with m.If(self.io_strobe):
                    m.d.comb += self.out_fifo.r_en.eq(1)
                    with m.If(~(self.mode_ctrl.vector_output.strobe_out)):
                        m.d.comb += self.in_fifo.w_en.eq(1)

            else:
                # m.d.comb += self.in_fifo.w_data.eq(self.mode_ctrl.vector_output.in_fifo_w_data)
                # with m.If(self.io_strobe):
                #     with m.If(~(self.mode_ctrl.vector_output.strobe_out)):
                #         m.d.comb += self.in_fifo.w_en.eq(1)
                m.d.comb += self.in_fifo.w_data.eq(self.mode_ctrl.in_fifo_w_data)
                with m.If(self.io_strobe):
                    with m.If(~(self.mode_ctrl.output_strobe_out)):
                        m.d.comb += self.in_fifo.w_en.eq(1)
                

        return m

    
## see simulation.py for the full simulation