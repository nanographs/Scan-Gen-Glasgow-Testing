import amaranth
from amaranth import *
from amaranth.sim import Simulator
from amaranth.lib import data, enum
import os, sys

if "glasgow" in __name__: ## running as applet
    from ..gateware.data_latch_bus import BusMultiplexer
    from ..gateware.structs import *
    from ..gateware.configuration_handler import ConfigHandler
    from ..gateware.board_sim import OBI_Board
    from ..gateware.beam_controller import BeamController
    from ..gateware.pixel_ratio_interpolator import PixelRatioInterpolator
    from ..gateware.dwell_averager import DwellTimeAverager
    from ..gateware.stream_reader import StreamReader
    from ..gateware.stream_writer import StreamWriter
    from ..gateware.xy_scan_gen import XY_Scan_Gen
    from ..gateware.byte_swapper import ByteSwapper
else:
    from board_sim import OBI_Board
    from data_latch_bus import BusMultiplexer
    from configuration_handler import ConfigHandler
    from structs import *
    from beam_controller import BeamController
    from pixel_ratio_interpolator import PixelRatioInterpolator
    from dwell_averager import DwellTimeAverager
    from stream_reader import StreamReader
    from stream_writer import StreamWriter
    from xy_scan_gen import XY_Scan_Gen
    from byte_swapper import ByteSwapper

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
        self.bus_multiplexer = BusMultiplexer()

        self.writer = StreamWriter(scan_dwell_8)
        self.onebyte_writer = StreamWriter(scan_dwell_8_onebyte)
        self.raster_reader = StreamReader(scan_dwell_8)
        self.vector_reader = StreamReader(scan_point_8)
        
        self.xy_scan_gen = XY_Scan_Gen()
        self.beam_controller = BeamController()
        self.x_interpolator = PixelRatioInterpolator()
        self.y_interpolator = PixelRatioInterpolator()
        self.byte_replacer = ByteSwapper(test_mode=self.test_mode)
        self.dwell_avgr = DwellTimeAverager()
        #### FIFOs
        self.out_fifo = out_fifo
        self.in_fifo = in_fifo

        ## Top level control of fifo data flow
        self.write_strobe = Signal(reset=0)
        self.read_strobe = Signal()

        self.write_this_point = Signal()
        self.load_next_point = Signal()
        self.reader_data_fresh = Signal()

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
        #m.submodules["ModeCtrl"] = self.mode_ctrl
        m.submodules["MuxBus"] = self.bus_multiplexer
        m.submodules["OUT_FIFO"] = self.out_fifo
        m.submodules["IN_FIFO"] = self.in_fifo
        m.submodules["ConfigHdlr"] = self.config_handler

        m.submodules["BeamController"] = self.beam_controller
        m.submodules["1byteWriter"] = self.onebyte_writer
        m.submodules["Writer"] = self.writer
        m.submodules["RasterReader"] = self.raster_reader   
        m.submodules["VectorReader"] = self.vector_reader         
        m.submodules["XYScanGen"] = self.xy_scan_gen
        m.submodules["XInt"] = self.x_interpolator
        m.submodules["YInt"] = self.y_interpolator

        m.submodules["DwellAvgr"] = self.dwell_avgr
        m.submodules["ByteReplace"] = self.byte_replacer
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
        #### =========================="BUS STATE MACHINE"==================================
        m.d.comb += self.bus_multiplexer.sampling.eq(self.beam_controller.dwelling)

        if self.test_mode == "fast clock":
            ### min dwell time is one actual clock cycle
            m.d.comb += self.beam_controller.count_enable.eq(1)
        else:
            m.d.comb += self.beam_controller.count_enable.eq(self.bus_multiplexer.is_done)

        with m.If(self.bus_multiplexer.is_x):
            m.d.comb += self.pins_o.eq(self.beam_controller.x_position)
            if self.is_simulation:
                m.d.comb += self.board.x_latch_chip.d.eq(self.pins_o)
        with m.If(self.bus_multiplexer.is_y):
            m.d.comb += self.pins_o.eq(self.beam_controller.y_position)
            if self.is_simulation:
                m.d.comb += self.board.y_latch_chip.d.eq(self.pins_o)
        with m.If(self.bus_multiplexer.is_a):
            m.d.comb += self.dwell_avgr.strobe.eq(self.bus_multiplexer.a_adc.released)
            if self.is_simulation:
                m.d.sync += self.board.adc_input.eq(self.dwell_avgr.pixel_in)
            if self.test_mode == "data loopback":
                with m.If(self.scan_mode == ScanMode.Raster):
                    m.d.comb += self.dwell_avgr.pixel_in.eq(self.beam_controller.x_position)
                with m.If((self.scan_mode == ScanMode.Vector)|(self.scan_mode == ScanMode.RasterPattern)):
                    m.d.comb += self.dwell_avgr.pixel_in.eq(self.beam_controller.dwell_time*64)
            else:
                m.d.comb += self.dwell_avgr.pixel_in.eq(self.pins_i)

        #### =============================================================================



        #### =========================== REGISTERS ====================================
        m.d.comb += self.roi_registers.LX1.eq(self.x_lower_limit_b1)
        m.d.comb += self.roi_registers.LX2.eq(self.x_lower_limit_b2)
        m.d.comb += self.roi_registers.UX1.eq(self.x_upper_limit_b1)
        m.d.comb += self.roi_registers.UX2.eq(self.x_upper_limit_b2)
        m.d.comb += self.roi_registers.LY1.eq(self.y_lower_limit_b1)
        m.d.comb += self.roi_registers.LY2.eq(self.y_lower_limit_b2)
        m.d.comb += self.roi_registers.UY1.eq(self.y_upper_limit_b1)
        m.d.comb += self.roi_registers.UY2.eq(self.y_upper_limit_b2)



        m.d.comb += self.config_handler.roi_registers.eq(self.roi_registers)

        #m.d.comb += self.mode_ctrl.eight_bit_output.eq(self.config_handler.eight_bit_output_locked)
        m.d.comb += self.config_handler.scan_mode.eq(self.scan_mode)
        m.d.comb += self.config_handler.step_size.eq(self.step_size)
        m.d.comb += self.x_interpolator.step_size.eq(self.config_handler.step_size_locked)
        m.d.comb += self.y_interpolator.step_size.eq(self.config_handler.step_size_locked)
        
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
            with m.If(self.config_handler.eight_bit_output_locked):
                with m.If((config_flag_latched) & (self.onebyte_writer.data_complete)):
                    m.d.comb += self.config_handler.configuration_flag.eq(1)
                    m.d.sync += config_flag_latched.eq(0)
            with m.If(~(self.config_handler.eight_bit_output_locked)):
                with m.If((config_flag_latched) & (self.writer.data_complete)):
                    m.d.comb += self.config_handler.configuration_flag.eq(1)
                    m.d.sync += config_flag_latched.eq(0)


        with m.If(~(self.unpause)):
            m.d.comb += self.write_strobe.eq(0)
        
        eflnp = Signal() ## pipelined intermediate to make timing easier
        asdf = Signal() ## pipelined intermediate to make timing easier
        sdfg = Signal()
        m.d.sync += eflnp.eq(self.config_handler.config_flag_released)
        m.d.sync += asdf.eq(eflnp)
        # m.d.sync += sdfg.eq(asdf)

        with m.If(asdf):
            m.d.comb += self.load_next_point.eq(1)
            m.d.comb += self.beam_controller.lock_new_point.eq(1)
            m.d.comb += self.dwell_avgr.start_new_average.eq(1)
        
        with m.If(asdf):
            m.d.comb += self.xy_scan_gen.increment.eq(1)

        m.d.comb += self.xy_scan_gen.reset.eq(self.handling_config)
        m.d.comb += self.beam_controller.reset.eq(self.handling_config)

        #m.d.comb += self.beam_controller_end_of_dwell.eq(self.mode_ctrl.beam_controller.end_of_dwell)
        #m.d.comb += self.mode_ctrl.const_dwell_time.eq(self.const_dwell_time)

        m.d.comb += self.config_handler.eight_bit_output.eq(self.eight_bit_output)
        #m.d.comb += self.mode_ctrl.eight_bit_output.eq(self.config_handler.eight_bit_output_locked)

        m.d.comb += self.config_handler.x_full_frame_resolution_b1.eq(self.x_full_resolution_b1)
        m.d.comb += self.config_handler.x_full_frame_resolution_b2.eq(self.x_full_resolution_b2)
        m.d.comb += self.config_handler.y_full_frame_resolution_b1.eq(self.y_full_resolution_b1)
        m.d.comb += self.config_handler.y_full_frame_resolution_b2.eq(self.y_full_resolution_b2)


        m.d.comb += self.xy_scan_gen.x_full_frame_resolution.eq(self.config_handler.x_full_frame_resolution_locked)
        m.d.comb += self.xy_scan_gen.y_full_frame_resolution.eq(self.config_handler.y_full_frame_resolution_locked)

        m.d.comb += self.xy_scan_gen.x_counter.upper_limit.eq(self.config_handler.roi_registers_locked.UX)
        m.d.comb += self.xy_scan_gen.x_counter.lower_limit.eq(self.config_handler.roi_registers_locked.LX)
        m.d.comb += self.xy_scan_gen.y_counter.upper_limit.eq(self.config_handler.roi_registers_locked.UY)
        m.d.comb += self.xy_scan_gen.y_counter.lower_limit.eq(self.config_handler.roi_registers_locked.LY) 

        #not used because we can't do division
        #m.d.comb += self.x_interpolator.frame_size.eq(self.config_handler.x_full_frame_resolution_locked)
        #m.d.comb += self.y_interpolator.frame_size.eq(self.config_handler.x_full_frame_resolution_locked)

        #### =============================================================================



        #### ===========================MODE CONTROL=================================================

        m.d.comb += self.byte_replacer.point_data.eq(self.dwell_avgr.running_average)
        m.d.comb += self.byte_replacer.eight_bit_output.eq(self.config_handler.eight_bit_output_locked)

        m.d.comb += self.beam_controller.next_x_position.eq(self.x_interpolator.output)
        m.d.comb += self.beam_controller.next_y_position.eq(self.y_interpolator.output)

        m.d.comb += self.beam_controller.lock_new_point.eq(self.load_next_point)

        with m.If(self.config_handler.eight_bit_output_locked):
            m.d.comb += self.onebyte_writer.data_c.eq(self.byte_replacer.processed_point_data)
            m.d.comb += self.in_fifo.w_data.eq(self.onebyte_writer.in_fifo_w_data)
            m.d.comb += self.onebyte_writer.write_happened.eq((self.write_strobe)&(self.unpause))
            m.d.comb += self.onebyte_writer.strobe_in.eq(self.write_this_point)
        with m.Else():
            m.d.comb += self.writer.data_c.eq(self.byte_replacer.processed_point_data.D1)
            m.d.comb += self.in_fifo.w_data.eq(self.writer.in_fifo_w_data)
            m.d.comb += self.writer.write_happened.eq((self.write_strobe)&(self.unpause))
            m.d.comb += self.writer.strobe_in.eq(self.write_this_point)

        data_stale = Signal()

        with m.If((self.scan_mode == ScanMode.Vector)|(self.scan_mode == ScanMode.RasterPattern)):
            with m.If((self.beam_controller.end_of_dwell) & (~(self.reader_data_fresh))):
                m.d.sync += data_stale.eq(1)
                with m.If((~(data_stale))):
                    m.d.comb += self.write_this_point.eq(1)
            with m.If((self.beam_controller.end_of_dwell) & (self.reader_data_fresh)):
                m.d.sync += data_stale.eq(0)
                m.d.comb += self.load_next_point.eq(1)
                with m.If((~(data_stale))):
                    m.d.comb += self.write_this_point.eq(1)
                m.d.comb += self.dwell_avgr.start_new_average.eq(1)
                


            with m.FSM() as fsm:
                with m.State("Wait for first USB"):
                    with m.If(self.scan_mode == ScanMode.RasterPattern):
                        with m.If(self.raster_reader.data_complete):
                            m.d.comb += self.beam_controller.dwelling.eq((self.in_fifo.w_rdy) & (self.unpause) & (~(self.handling_config)))
                            m.d.comb += self.load_next_point.eq(1)
                            m.d.comb += self.dwell_avgr.start_new_average.eq(1)
                            m.next = "Patterning"
                    with m.If(self.scan_mode == ScanMode.Vector):
                        with m.If(self.vector_reader.data_complete):
                            m.d.comb += self.beam_controller.dwelling.eq((self.in_fifo.w_rdy) & (self.unpause) & (~(self.handling_config)))
                            m.d.comb += self.load_next_point.eq(1)
                            m.d.comb += self.dwell_avgr.start_new_average.eq(1)
                            m.next = "Patterning"
                with m.State("Patterning"):
                    m.d.comb += self.beam_controller.dwelling.eq((self.in_fifo.w_rdy) & (self.unpause) & (~(self.handling_config)))

        with m.If((self.scan_mode == ScanMode.Raster)|(self.scan_mode == ScanMode.RasterPattern)):
            #### Interpolation 
            m.d.comb += self.xy_scan_gen.x_full_frame_resolution.eq(self.config_handler.x_full_frame_resolution_locked)
            m.d.comb += self.xy_scan_gen.y_full_frame_resolution.eq(self.config_handler.y_full_frame_resolution_locked)

            with m.If(self.load_next_point):
                m.d.comb += self.xy_scan_gen.increment.eq(1)
                m.d.comb += self.x_interpolator.input.eq(self.xy_scan_gen.current_x)
                m.d.comb += self.y_interpolator.input.eq(self.xy_scan_gen.current_y)
                m.d.comb += self.raster_reader.data_used.eq(1)
                m.d.comb += self.beam_controller.next_dwell.eq(self.raster_reader.data_c.as_value())


            

        with m.If(self.scan_mode == ScanMode.Raster):
            m.d.comb += self.dwell_avgr.start_new_average.eq(self.beam_controller.at_dwell)
            m.d.comb += self.beam_controller.dwelling.eq((self.in_fifo.w_rdy) & (self.unpause) & ((~self.handling_config))) 
            m.d.comb += self.load_next_point.eq(self.beam_controller.end_of_dwell)
            m.d.comb += self.write_this_point.eq(self.beam_controller.end_of_dwell)
            m.d.comb += self.beam_controller.next_dwell.eq(self.const_dwell_time)

        with m.If(self.scan_mode == ScanMode.RasterPattern):
            m.d.comb += self.reader_data_fresh.eq(self.raster_reader.data_fresh)
            m.d.comb += self.raster_reader.out_fifo_r_data.eq(self.out_fifo.r_data)
            m.d.comb += self.raster_reader.read_happened.eq(self.read_strobe)
            m.d.comb += self.beam_controller.next_dwell.eq(Cat(self.raster_reader.data.D1, self.raster_reader.data.D2))

            
        with m.If(self.scan_mode == ScanMode.Vector):
            m.d.comb += self.reader_data_fresh.eq(self.vector_reader.data_fresh)

            m.d.comb += self.vector_reader.read_happened.eq(self.read_strobe)
            m.d.comb += self.vector_reader.out_fifo_r_data.eq(self.out_fifo.r_data)

            m.d.comb += self.x_interpolator.input.eq(Cat(self.vector_reader.data.X1, self.vector_reader.data.X2))
            m.d.comb += self.y_interpolator.input.eq(Cat(self.vector_reader.data.Y1, self.vector_reader.data.Y2))
            m.d.comb += self.beam_controller.next_dwell.eq(Cat(self.vector_reader.data.D1, self.vector_reader.data.D2))

            with m.If(self.load_next_point):
                m.d.comb += self.vector_reader.data_used.eq(1)

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

        with m.If(self.scan_mode == ScanMode.RasterPattern):
            m.d.comb += self.read_strobe.eq((~(self.raster_reader.data_complete))&(self.out_fifo.r_rdy))
        with m.Elif(self.scan_mode == ScanMode.Vector): 
            m.d.comb += self.read_strobe.eq((~(self.vector_reader.data_complete))&(self.out_fifo.r_rdy))
        with m.Else():
            m.d.comb += self.read_strobe.eq(self.out_fifo.r_rdy)

        with m.If((self.handling_config)):
            m.d.comb += self.write_strobe.eq((self.in_fifo.w_rdy) & (self.config_handler.config_data_valid))
            m.d.comb += self.config_handler.write_happened.eq((self.write_strobe) & (self.unpause))
        with m.Else():
            with m.If(self.config_handler.eight_bit_output_locked):
                m.d.comb += self.write_strobe.eq((self.in_fifo.w_rdy) & (self.onebyte_writer.data_valid))
                m.d.comb += self.onebyte_writer.write_happened.eq((self.write_strobe) & (self.unpause))
            with m.Else():
                m.d.comb += self.write_strobe.eq((self.in_fifo.w_rdy) & (self.writer.data_valid))
                m.d.comb += self.writer.write_happened.eq((self.write_strobe) & (self.unpause))

        

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
                    with m.If(self.config_handler.eight_bit_output_locked):
                        m.d.comb += self.in_fifo.w_data.eq(self.onebyte_writer.in_fifo_w_data)
                    with m.Else():
                        m.d.comb += self.in_fifo.w_data.eq(self.writer.in_fifo_w_data)

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