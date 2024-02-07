import amaranth
from amaranth import *
from amaranth.sim import Simulator
from amaranth.lib.fifo import SyncFIFO, SyncFIFOBuffered
from amaranth.lib import data, enum

if "glasgow" in __name__: ## running as applet
    from ..gateware.beam_controller import BeamController
    from ..gateware.mode_controller_raster import RasterModeController
    from ..gateware.mode_controller_vector import VectorModeController
    from ..gateware.structs import *
    from ..gateware.pixel_ratio_interpolator import PixelRatioInterpolator
    from ..gateware.dwell_averager import DwellTimeAverager
    from ..gateware.byte_replacer import ByteReplacer
# if __name__ == "__main__":
else:
    from beam_controller import BeamController
    from structs import *
    from mode_controller_raster import RasterModeController
    from mode_controller_vector import VectorModeController
    from pixel_ratio_interpolator import PixelRatioInterpolator
    from dwell_averager import DwellTimeAverager
    from byte_replacer import ByteReplacer



class ModeController(Elaboratable):
    '''
    beam_controller: see beam_controller.py
    vec_mode_ctrl: see mode_controller_vector.py
    ras_mode_ctrl: see mode_controller_raster.py

    x_interpolator:
    y_interpolator:

    x_full_frame_resolution: Signal, in, 16
        Number of discrete steps to cover DAC full range
    y_full_frame_resolution: Signal, in, 16
        Number of discrete steps to cover DAC full range 
        The actual full frame size is the maximum of either
        x_full_frame_resolution or y_full_frame_resolution 

    mode: Signal, in, 2
        ScanMode.Raster = 1
        ScanMode.Vector = 3

    in_fifo_w_data: Signal, out, 8
        Combinatorially drives the top level in_fifo.w_data
    out_fifo_r_data: Signal, in, 8
        Combinatorially driven by the top level out_fifo.r_data

    output_enable: Signal, in, 1
        Asserted when fifos can be read to and written from
        Driven by top level io_strobe
    writer_data_valid: Signal, out, 1
        Asserted when in_fifo_w_data is valid
        Driven by either vec_mode_ctrl.vector_output.data_valid
        or  ras_mode_ctrl.raster_output.data_valid
    internal_fifo_ready: Signal, out, 1
        Vector mode: Asserted when vector_fifo.w_rdy is true
        Raster mode: Always true
    
    adc_data: Signal, in, 16:
        Data to be recorded as the brightness value for this point
    adc_data_strobe: Signal, in, 1
        Asserted when adc_data is valid
    '''
    def __init__(self, test_mode):
        self.test_mode = test_mode

        self.beam_controller = BeamController()
        self.vec_mode_ctrl = VectorModeController()
        self.ras_mode_ctrl = RasterModeController()

        self.x_interpolator = PixelRatioInterpolator()
        self.y_interpolator = PixelRatioInterpolator()

        self.byte_replacer = ByteReplacer(self.test_mode)

        self.dwell_avgr = DwellTimeAverager()

        self.x_full_frame_resolution = Signal(16)
        self.y_full_frame_resolution = Signal(16)

        self.x_lower_limit = Signal(16)
        self.x_upper_limit = Signal(16)
        self.y_lower_limit = Signal(16)
        self.y_upper_limit = Signal(16)

        self.mode = Signal(2)

        self.in_fifo_w_data = Signal(8)
        self.out_fifo_r_data = Signal(8)

        #self.read_enable = Signal()
        #self.write_enable = Signal()
        #self.write_strobe = Signal()
        self.write_ready = Signal()
        #self.read_strobe = Signal()
        self.reader_data_complete = Signal()
        self.read_happened = Signal()

        self.write_happened = Signal()
        self.writer_data_valid = Signal()

        self.writer_data_complete = Signal()

        self.internal_fifo_ready = Signal()
        self.adc_data = Signal(16)
        self.adc_data_strobe = Signal()

        self.eight_bit_output = Signal()
        self.const_dwell_time = Signal(8)

        self.replace_FF_to_FE = Signal()

        self.reset = Signal()
        self.disable_dwell = Signal()
        self.complete_one_point = Signal()

        self.strobe_new_point = Signal()

        self.xy_scan_gen_increment = Signal()

        self.load_next_point = Signal()
        self.write_this_point = Signal()
        self.reader_data_fresh = Signal()

        self.beam_controller_freeze = Signal()
        self.beam_controller_end_of_dwell = Signal()

        self.force_load_new_point = Signal()
        self.external_force_load_new_point = Signal()
        
    def elaborate(self, platform):
        m = Module()
        m.submodules["BeamController"] = self.beam_controller
        m.submodules["RasterModeCtrl"] = self.ras_mode_ctrl
        m.submodules["VectorModeCtrl"] = self.vec_mode_ctrl

        m.submodules["XInt"] = self.x_interpolator
        m.submodules["YInt"] = self.y_interpolator

        m.submodules["DwellAvgr"] = self.dwell_avgr
        m.submodules["ByteReplace"] = self.byte_replacer

        #m.d.comb += self.beam_controller.freeze.eq(self.beam_controller_freeze)
        #m.d.comb += self.beam_controller_end_of_dwell.eq(self.beam_controller.end_of_dwell)
        m.d.comb += self.x_interpolator.frame_size.eq(self.x_full_frame_resolution)
        m.d.comb += self.y_interpolator.frame_size.eq(self.y_full_frame_resolution)

        m.d.comb += self.dwell_avgr.pixel_in.eq(self.adc_data)
        m.d.comb += self.dwell_avgr.strobe.eq(self.adc_data_strobe)

        m.d.comb += self.byte_replacer.point_data.eq(self.dwell_avgr.running_average)
        m.d.comb += self.byte_replacer.replace_FF_to_FE.eq(self.replace_FF_to_FE)


        m.d.comb += self.beam_controller.next_x_position.eq(self.x_interpolator.output)
        m.d.comb += self.beam_controller.next_y_position.eq(self.y_interpolator.output)

        m.d.comb += self.ras_mode_ctrl.xy_scan_gen.reset.eq(self.reset)
        m.d.comb += self.ras_mode_ctrl.xy_scan_gen_increment.eq(self.xy_scan_gen_increment)
        m.d.comb += self.ras_mode_ctrl.eight_bit_output.eq(self.eight_bit_output)
        m.d.comb += self.beam_controller.reset.eq(self.reset)
        m.d.comb += self.beam_controller.lock_new_point.eq(self.load_next_point)

        m.d.comb += self.internal_fifo_ready.eq(1)

        

        with m.If((self.force_load_new_point)|(self.external_force_load_new_point)):
            m.d.comb += self.load_next_point.eq(1)
            m.d.comb += self.beam_controller.lock_new_point.eq(1)
            m.d.comb += self.dwell_avgr.start_new_average.eq(1)
            
        data_stale = Signal()

        with m.If((self.mode == ScanMode.Vector)|(self.mode == ScanMode.RasterPattern)):
            #with m.If(self.reader_data_fresh):
                #m.d.sync += data_stale.eq(0)
            with m.If((self.beam_controller.end_of_dwell) & (~(self.reader_data_fresh))):
                #m.d.sync += self.beam_controller.freeze.eq(1)
                m.d.sync += data_stale.eq(1)
                with m.If((~(data_stale))):
                    m.d.comb += self.write_this_point.eq(1)
            with m.If((self.beam_controller.end_of_dwell) & (self.reader_data_fresh)):
                m.d.sync += data_stale.eq(0)
                m.d.comb += self.load_next_point.eq(1)
                with m.If((~(data_stale))):
                    m.d.comb += self.write_this_point.eq(1)
                m.d.comb += self.dwell_avgr.start_new_average.eq(self.beam_controller.at_dwell)
                
            # with m.If((self.beam_controller.freeze) & (self.adc_data_strobe) & (self.reader_data_fresh)):
            #     m.d.sync += self.beam_controller_freeze.eq(0)
            #     m.d.comb += self.force_load_new_point.eq(1)

            


            with m.FSM() as fsm:
                with m.State("Wait for first USB"):
                    with m.If(self.reader_data_complete):
                        m.d.comb += self.beam_controller.dwelling.eq((self.write_ready) & (~(self.disable_dwell))) 
                        m.d.comb += self.load_next_point.eq(1)
                        m.d.comb += self.dwell_avgr.start_new_average.eq(1)
                        m.next = "Patterning"
                with m.State("Patterning"):
                    m.d.comb += self.beam_controller.dwelling.eq((self.write_ready) & (~(self.disable_dwell))) 

        with m.If((self.mode == ScanMode.Raster)|(self.mode == ScanMode.RasterPattern)):
            #### Interpolation 
            m.d.comb += self.ras_mode_ctrl.xy_scan_gen.x_full_frame_resolution.eq(self.x_full_frame_resolution)
            m.d.comb += self.ras_mode_ctrl.xy_scan_gen.y_full_frame_resolution.eq(self.y_full_frame_resolution)
            m.d.comb += self.x_interpolator.input.eq(self.ras_mode_ctrl.beam_controller_next.X)
            m.d.comb += self.y_interpolator.input.eq(self.ras_mode_ctrl.beam_controller_next.Y)

            m.d.comb += self.ras_mode_ctrl.beam_controller_end_of_dwell.eq(self.beam_controller.end_of_dwell)
            m.d.comb += self.ras_mode_ctrl.adc_data_avgd.eq(self.byte_replacer.processed_point_data)

            with m.If(self.eight_bit_output):
                m.d.comb += self.in_fifo_w_data.eq(self.ras_mode_ctrl.onebyte_writer.in_fifo_w_data)
                m.d.comb += self.ras_mode_ctrl.onebyte_writer.write_happened.eq(self.write_happened)
                m.d.comb += self.writer_data_valid.eq(self.ras_mode_ctrl.onebyte_writer.data_valid)
                m.d.comb += self.writer_data_complete.eq(self.ras_mode_ctrl.onebyte_writer.data_complete)
            with m.Else():
                m.d.comb += self.in_fifo_w_data.eq(self.ras_mode_ctrl.writer.in_fifo_w_data)
                m.d.comb += self.ras_mode_ctrl.writer.write_happened.eq(self.write_happened)
                m.d.comb += self.writer_data_valid.eq(self.ras_mode_ctrl.writer.data_valid)
                m.d.comb += self.writer_data_complete.eq(self.ras_mode_ctrl.writer.data_complete)

            m.d.comb += self.ras_mode_ctrl.load_next_point.eq(self.load_next_point)
            m.d.comb += self.ras_mode_ctrl.write_this_point.eq(self.write_this_point)

            with m.If(self.external_force_load_new_point):
                m.d.comb += self.ras_mode_ctrl.xy_scan_gen_increment.eq(1)

        with m.If(self.mode == ScanMode.Raster):
            m.d.comb += self.dwell_avgr.start_new_average.eq(self.beam_controller.at_dwell)
            m.d.comb += self.beam_controller.dwelling.eq((self.write_ready) & (~(self.disable_dwell))) 
            m.d.comb += self.load_next_point.eq(self.beam_controller.end_of_dwell)
            m.d.comb += self.write_this_point.eq(self.beam_controller.end_of_dwell)
            m.d.comb += self.beam_controller.next_dwell.eq(self.const_dwell_time)

        with m.If(self.mode == ScanMode.RasterPattern):
            m.d.comb += self.reader_data_complete.eq(self.ras_mode_ctrl.reader.data_complete);
            m.d.comb += self.reader_data_fresh.eq(self.ras_mode_ctrl.reader.data_fresh)

            m.d.comb += self.ras_mode_ctrl.reader.out_fifo_r_data.eq(self.out_fifo_r_data)
            m.d.comb += self.ras_mode_ctrl.reader.read_happened.eq(self.read_happened)
            m.d.comb += self.beam_controller.next_dwell.eq(self.ras_mode_ctrl.beam_controller_next.D)

            
        with m.If(self.mode == ScanMode.Vector):
            m.d.comb += self.writer_data_complete.eq(self.vec_mode_ctrl.writer.data_complete)
            m.d.comb += self.reader_data_complete.eq(self.vec_mode_ctrl.reader.data_complete)
            m.d.comb += self.vec_mode_ctrl.reader.read_happened.eq(self.read_happened)
            m.d.comb += self.vec_mode_ctrl.load_next_point.eq(self.load_next_point)
            m.d.comb += self.vec_mode_ctrl.write_this_point.eq(self.write_this_point)
            m.d.comb += self.reader_data_fresh.eq(self.vec_mode_ctrl.reader.data_fresh)
            
            m.d.comb += self.vec_mode_ctrl.beam_controller_end_of_dwell.eq(self.beam_controller.end_of_dwell)

            m.d.comb += self.vec_mode_ctrl.adc_data_avgd.eq(self.byte_replacer.processed_point_data)


            m.d.comb += self.x_interpolator.input.eq(self.vec_mode_ctrl.beam_controller_next.X)
            m.d.comb += self.y_interpolator.input.eq(self.vec_mode_ctrl.beam_controller_next.Y)
            m.d.comb += self.beam_controller.next_dwell.eq(self.vec_mode_ctrl.beam_controller_next.D)

            m.d.comb += self.in_fifo_w_data.eq(self.vec_mode_ctrl.writer.in_fifo_w_data)
            m.d.comb += self.vec_mode_ctrl.writer.write_happened.eq(self.write_happened)
            m.d.comb += self.vec_mode_ctrl.reader.read_happened.eq(self.read_happened)
            m.d.comb += self.writer_data_valid.eq(self.vec_mode_ctrl.writer.data_valid)
            m.d.comb += self.vec_mode_ctrl.reader.out_fifo_r_data.eq(self.out_fifo_r_data)
            


        return m

def test_multimodecontroller():

    dut = ModeController()

    def bench():
        yield dut.mode.eq(1)
        yield dut.beam_controller.count_enable.eq(1)
        yield dut.ras_mode_ctrl.xy_scan_gen.x_full_frame_resolution.eq(8)
        yield dut.ras_mode_ctrl.xy_scan_gen.y_full_frame_resolution.eq(8)
        yield
        for n in range(64):
            yield

    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("multimode_sim.vcd"):
        sim.run()


if __name__ == "__main__":
    test_multimodecontroller()
