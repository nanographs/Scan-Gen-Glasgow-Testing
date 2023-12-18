import amaranth
from amaranth import *
from amaranth.sim import Simulator
from amaranth.lib.fifo import SyncFIFO, SyncFIFOBuffered
from amaranth.lib import data, enum

if "glasgow" in __name__: ## running as applet
    from ..scan_gen_components.beam_controller import BeamController
    from ..scan_gen_components.xy_scan_gen import XY_Scan_Gen
    from ..scan_gen_components.mode_controller_raster import RasterModeController
    from ..scan_gen_components.mode_controller_vector import VectorModeController
    from ..scan_gen_components.addresses import *
    from ..scan_gen_components.pixel_ratio_interpolator import PixelRatioInterpolator
    from ..scan_gen_components.output_handling import DwellTimeAverager
# if __name__ == "__main__":
else:
    from beam_controller import BeamController
    from xy_scan_gen import XY_Scan_Gen
    from addresses import *
    from mode_controller_raster import RasterModeController
    from mode_controller_vector import VectorModeController
    from pixel_ratio_interpolator import PixelRatioInterpolator
    from output_handling import DwellTimeAverager



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
    def __init__(self):
        self.beam_controller = BeamController()
        self.vec_mode_ctrl = VectorModeController()
        self.ras_mode_ctrl = RasterModeController()

        self.x_interpolator = PixelRatioInterpolator()
        self.y_interpolator = PixelRatioInterpolator()

        self.dwell_avgr = DwellTimeAverager()

        self.x_full_frame_resolution = Signal(16)
        self.y_full_frame_resolution = Signal(16)

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

        self.internal_fifo_ready = Signal()
        self.adc_data = Signal(16)
        self.adc_data_strobe = Signal()

        self.eight_bit_output = Signal()
        self.const_dwell_time = Signal(8)
        
    def elaborate(self, platform):
        m = Module()
        m.submodules["BeamController"] = self.beam_controller
        m.submodules["RasterModeCtrl"] = self.ras_mode_ctrl
        m.submodules["VectorModeCtrl"] = self.vec_mode_ctrl

        m.submodules["XInt"] = self.x_interpolator
        m.submodules["YInt"] = self.y_interpolator

        m.submodules["DwellAvgr"] = self.dwell_avgr

        m.d.comb += self.x_interpolator.frame_size.eq(self.x_full_frame_resolution)
        m.d.comb += self.y_interpolator.frame_size.eq(self.y_full_frame_resolution)

        m.d.comb += self.dwell_avgr.pixel_in.eq(self.adc_data)
        m.d.comb += self.dwell_avgr.strobe.eq(self.adc_data_strobe)
        m.d.comb += self.dwell_avgr.start_new_average.eq(self.beam_controller.end_of_dwell)

        # with m.If(self.mode == 0): ### when in DO NOTHING mode, do nothing.
        #     m.d.comb += self.write_happened.eq(0)
        #     m.d.comb += self.beam_controller.dwelling.eq(0)

        with m.If((self.mode == ScanMode.Raster)|(self.mode == ScanMode.RasterPattern)):
            #### Interpolation 
            m.d.comb += self.ras_mode_ctrl.xy_scan_gen.x_full_frame_resolution.eq(self.x_full_frame_resolution)
            m.d.comb += self.ras_mode_ctrl.xy_scan_gen.y_full_frame_resolution.eq(self.y_full_frame_resolution)
            # m.d.comb += self.beam_controller.next_x_position.eq(self.ras_mode_ctrl.beam_controller_next_x_position)
            # m.d.comb += self.beam_controller.next_y_position.eq(self.ras_mode_ctrl.beam_controller_next_y_position)
            m.d.comb += self.x_interpolator.input.eq(self.ras_mode_ctrl.beam_controller_next_x_position)
            m.d.comb += self.y_interpolator.input.eq(self.ras_mode_ctrl.beam_controller_next_y_position)
            m.d.comb += self.beam_controller.next_x_position.eq(self.x_interpolator.output)
            m.d.comb += self.beam_controller.next_y_position.eq(self.y_interpolator.output)

            
            m.d.comb += self.ras_mode_ctrl.beam_controller_end_of_dwell.eq(self.beam_controller.end_of_dwell)
            m.d.comb += self.ras_mode_ctrl.beam_controller_start_dwell.eq(self.beam_controller.start_dwell)
            #m.d.comb += self.ras_mode_ctrl.raster_point_output.eq(self.beam_controller.x_position) ## loopback
            m.d.comb += self.ras_mode_ctrl.raster_point_output.eq(self.dwell_avgr.running_average)
            with m.If(~self.beam_controller.prev_dwelling_changed):
                m.d.comb += self.ras_mode_ctrl.raster_writer.strobe_in_dwell.eq(self.beam_controller.end_of_dwell)

            
            m.d.comb += self.in_fifo_w_data.eq(self.ras_mode_ctrl.raster_writer.in_fifo_w_data)
            m.d.comb += self.ras_mode_ctrl.raster_writer.write_happened.eq(self.write_happened)
            m.d.comb += self.writer_data_valid.eq(self.ras_mode_ctrl.raster_writer.data_valid)
            
            m.d.comb += self.ras_mode_ctrl.raster_writer.eight_bit_output.eq(self.eight_bit_output)
            m.d.comb += self.ras_mode_ctrl.eight_bit_output.eq(self.eight_bit_output)

            
            with m.If(self.mode == ScanMode.Raster):
                m.d.comb += self.beam_controller.dwelling.eq(self.write_ready)
                m.d.comb += self.beam_controller.next_dwell.eq(self.const_dwell_time)
                m.d.comb += self.internal_fifo_ready.eq(1) ## there is no internal 
                

            with m.If(self.mode == ScanMode.RasterPattern):
                ## pattern pixels must be in sync with frame pixels, or else pattern gets garbled
                with m.FSM() as fsm:
                    with m.State("Wait for first USB"):
                        with m.If(self.ras_mode_ctrl.raster_fifo.r_rdy):
                            m.d.comb += self.beam_controller.dwelling.eq(self.write_ready) 
                            m.next = "Patterning"
                    with m.State("Patterning"):
                        m.d.comb += self.beam_controller.dwelling.eq(self.write_ready) 
                m.d.comb += self.ras_mode_ctrl.raster_reader.out_fifo_r_data.eq(self.out_fifo_r_data)
                m.d.comb += self.ras_mode_ctrl.raster_reader.read_happened.eq(self.read_happened)
                m.d.comb += self.internal_fifo_ready.eq(self.ras_mode_ctrl.raster_fifo.w_rdy)
                m.d.comb += self.beam_controller.next_dwell.eq(self.ras_mode_ctrl.beam_controller_next_dwell)

            
        with m.If(self.mode == ScanMode.Vector):
            m.d.comb += self.reader_data_complete.eq((self.vec_mode_ctrl.vector_reader.data_complete))
            m.d.comb += self.vec_mode_ctrl.vector_reader.read_happened.eq(self.read_happened)
            with m.FSM() as fsm:
                    with m.State("Wait for first USB"):
                        #with m.If(self.vec_mode_ctrl.vector_fifo.r_rdy):
                        with m.If(self.vec_mode_ctrl.vector_reader.data_complete):
                            m.d.comb += self.beam_controller.dwelling.eq(self.write_ready)
                            m.next = "Patterning"
                    with m.State("Patterning"):
                        m.d.comb += self.beam_controller.dwelling.eq(self.write_ready) 
                        m.d.comb += self.vec_mode_ctrl.vector_writer.strobe_in_xy.eq((self.beam_controller.end_of_dwell))
                        m.d.comb += self.vec_mode_ctrl.vector_reader.data_point_used.eq(self.beam_controller.end_of_dwell)
                        m.d.comb += self.vec_mode_ctrl.vector_writer.strobe_in_dwell.eq((self.beam_controller.end_of_dwell))

                    # 
            # with m.If((~self.beam_controller.dwelling_changed) & (self.reader_data_complete)):
            #     
            # with m.If((~self.beam_controller.dwelling_changed)):
            #     




            m.d.comb += self.vec_mode_ctrl.beam_controller_end_of_dwell.eq(self.beam_controller.end_of_dwell)
            m.d.comb += self.vec_mode_ctrl.beam_controller_start_dwell.eq(self.beam_controller.start_dwell)

            m.d.comb += self.vec_mode_ctrl.vector_point_output.eq(self.dwell_avgr.running_average)

            #with m.If(~self.beam_controller.dwelling_changed & (self.reader_data_complete)):

            m.d.comb += self.vec_mode_ctrl.beam_controller_dwelling_changed.eq(self.beam_controller.dwelling_changed)

            m.d.comb += self.beam_controller.next_x_position.eq(self.vec_mode_ctrl.beam_controller_next_x_position)
            m.d.comb += self.beam_controller.next_y_position.eq(self.vec_mode_ctrl.beam_controller_next_y_position)
            m.d.comb += self.beam_controller.next_dwell.eq(self.vec_mode_ctrl.beam_controller_next_dwell)

            m.d.comb += self.in_fifo_w_data.eq(self.vec_mode_ctrl.vector_writer.in_fifo_w_data)
            m.d.comb += self.vec_mode_ctrl.vector_writer.write_happened.eq(self.write_happened)
            m.d.comb += self.vec_mode_ctrl.vector_reader.read_happened.eq(self.read_happened)
            m.d.comb += self.writer_data_valid.eq(self.vec_mode_ctrl.vector_writer.data_valid)
            m.d.comb += self.vec_mode_ctrl.vector_reader.out_fifo_r_data.eq(self.out_fifo_r_data)
            m.d.comb += self.internal_fifo_ready.eq((self.vec_mode_ctrl.vector_fifo.w_rdy))

            m.d.comb += self.vec_mode_ctrl.vector_writer.eight_bit_output.eq(self.eight_bit_output)

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
