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
# if __name__ == "__main__":
else:
    from beam_controller import BeamController
    from xy_scan_gen import XY_Scan_Gen
    from addresses import *
    from mode_controller_raster import RasterModeController
    from mode_controller_vector import VectorModeController



class ModeController(Elaboratable):
    '''
    '''
    def __init__(self):
        self.beam_controller = BeamController()
        self.vec_mode_ctrl = VectorModeController()
        self.ras_mode_ctrl = RasterModeController()
        self.mode = Signal(2)
        self.in_fifo_w_data = Signal(8)
        self.out_fifo_r_data = Signal(8)
        self.output_enable = Signal()
        self.output_strobe_out = Signal()
        self.internal_fifo_ready = Signal()
        self.adc_data = Signal(16)
        self.adc_data_strobe = Signal()
    def elaborate(self, platform):
        m = Module()
        m.submodules["BeamController"] = self.beam_controller
        m.submodules["RasterModeCtrl"] = self.ras_mode_ctrl
        m.submodules["VectorModeCtrl"] = self.vec_mode_ctrl

        

        with m.If(self.mode == ScanMode.Raster):
            m.d.comb += self.beam_controller.dwelling.eq(1)
            m.d.comb += self.ras_mode_ctrl.beam_controller_end_of_dwell.eq(self.beam_controller.end_of_dwell)
            m.d.comb += self.ras_mode_ctrl.beam_controller_start_dwell.eq(self.beam_controller.start_dwell)
            #m.d.comb += self.ras_mode_ctrl.raster_point_output.eq(self.beam_controller.x_position) ## loopback
            m.d.comb += self.ras_mode_ctrl.raster_point_output.eq(self.adc_data)
            with m.If(~self.beam_controller.start_dwell):
                m.d.comb += self.ras_mode_ctrl.raster_output.strobe_in_dwell.eq(self.adc_data_strobe)
            m.d.comb += self.beam_controller.next_x_position.eq(self.ras_mode_ctrl.beam_controller_next_x_position)
            m.d.comb += self.beam_controller.next_y_position.eq(self.ras_mode_ctrl.beam_controller_next_y_position)
            m.d.comb += self.beam_controller.next_dwell.eq(self.ras_mode_ctrl.beam_controller_next_dwell)
            m.d.comb += self.in_fifo_w_data.eq(self.ras_mode_ctrl.raster_output.in_fifo_w_data)
            m.d.comb += self.ras_mode_ctrl.raster_output.enable.eq(self.output_enable)
            m.d.comb += self.output_strobe_out.eq(self.ras_mode_ctrl.raster_output.strobe_out)
            m.d.comb += self.internal_fifo_ready.eq(1) ## there is no internal fifo

        with m.If(self.mode == ScanMode.Vector):
            m.d.comb += self.beam_controller.dwelling.eq(1)
            m.d.comb += self.vec_mode_ctrl.beam_controller_end_of_dwell.eq(self.beam_controller.end_of_dwell)
            m.d.comb += self.vec_mode_ctrl.beam_controller_start_dwell.eq(self.beam_controller.start_dwell)
            #m.d.comb += self.vec_mode_ctrl.vector_point_output.eq(self.beam_controller.dwell_time) ## loopback
            
            m.d.comb += self.vec_mode_ctrl.vector_point_output.eq(self.adc_data)
            with m.If(~self.beam_controller.start_dwell):
                m.d.comb += self.vec_mode_ctrl.vector_output.strobe_in_dwell.eq(self.adc_data_strobe)

            m.d.comb += self.beam_controller.next_x_position.eq(self.vec_mode_ctrl.beam_controller_next_x_position)
            m.d.comb += self.beam_controller.next_y_position.eq(self.vec_mode_ctrl.beam_controller_next_y_position)
            m.d.comb += self.beam_controller.next_dwell.eq(self.vec_mode_ctrl.beam_controller_next_dwell)

            m.d.comb += self.in_fifo_w_data.eq(self.vec_mode_ctrl.vector_output.in_fifo_w_data)
            m.d.comb += self.vec_mode_ctrl.vector_output.enable.eq(self.output_enable)
            m.d.comb += self.vec_mode_ctrl.vector_input.enable.eq(self.output_enable)
            m.d.comb += self.output_strobe_out.eq(self.vec_mode_ctrl.vector_output.strobe_out)
            m.d.comb += self.vec_mode_ctrl.vector_input.out_fifo_r_data.eq(self.out_fifo_r_data)
            m.d.comb += self.internal_fifo_ready.eq((self.vec_mode_ctrl.vector_fifo.w_rdy))

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
