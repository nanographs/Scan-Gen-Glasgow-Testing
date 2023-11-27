import amaranth
from amaranth import *
from amaranth.sim import Simulator

if "glasgow" in __name__: ## running as applet
    from ..scan_gen_components.beam_controller import BeamController
    from ..scan_gen_components.xy_scan_gen import XY_Scan_Gen
    from ..scan_gen_components.addresses import *
else:
    from beam_controller import BeamController
    from xy_scan_gen import XY_Scan_Gen

    from addresses import *

class ModeController(Elaboratable):
    def __init__(self, v_x_mailbox, v_y_mailbox, v_d_mailbox,
    r_x_mailbox, r_y_mailbox, r_d_mailbox, 
    r_uy_mailbox, r_ux_mailbox, r_ly_mailbox, r_lx_mailbox):
        self.v_x_mailbox = v_x_mailbox
        self.v_y_mailbox = v_y_mailbox
        self.v_d_mailbox = v_d_mailbox
        self.r_x_mailbox = r_x_mailbox
        self.r_y_mailbox = r_y_mailbox
        self.r_d_mailbox = r_d_mailbox
        self.r_uy_mailbox = r_uy_mailbox
        self.r_ux_mailbox = r_ux_mailbox
        self.r_ly_mailbox = r_ly_mailbox
        self.r_lx_mailbox = r_lx_mailbox

        self.scan_mode = Signal()
        self.dwell_mode = Signal()

        self.raster_next = Signal()
        self.vector_next = Signal()
        self.load_next_raster_frame_data = Signal()
        self.load_next_vector_values = Signal()
        self.beam_controller = BeamController()
        self.xy_scan_gen = XY_Scan_Gen()

        self.v_x = Signal(14)
        self.v_y = Signal(14)
        self.v_dwell_time = Signal(16)

        self.r_x = Signal(14)
        self.r_y= Signal(14)
        self.r_ux = Signal(14)
        self.r_uy= Signal(14)
        self.r_lx = Signal(14)
        self.r_ly= Signal(14)
        self.r_dwell_time = Signal(16)

        self.start_frame = Signal()
        self.scan_single_frame = Signal()

        self.rastering = Signal()
        self.vectoring = Signal()

        self.frame_sync = Signal()

        self.reset = Signal()

        self.first_frame = Signal()

        self.r_dwell_time_p1 = Signal(16)
        self.r_dwell_time_p2 = Signal(16)
        self.r_dwell_time_p3 = Signal(16)
        self.dwell_pipeline_level = Signal(3)
        self.dwell_pipeline_full = Signal()


    def elaborate(self, platform):
        m = Module()
        m.submodules["XYScanGen"] = self.xy_scan_gen
        m.submodules["BeamController"] = self.beam_controller

        m.submodules["vx"] = self.v_x_mailbox
        m.submodules["vy"] = self.v_y_mailbox
        m.submodules["vd"] = self.v_d_mailbox
        m.submodules["rx"] = self.r_x_mailbox
        m.submodules["ry"] = self.r_y_mailbox
        m.submodules["rd"] = self.r_d_mailbox
        m.submodules["rux"] = self.r_ux_mailbox
        m.submodules["ruy"] = self.r_uy_mailbox
        m.submodules["rlx"] = self.r_lx_mailbox
        m.submodules["rly"] = self.r_ly_mailbox

        m.d.sync += self.frame_sync.eq(self.xy_scan_gen.frame_sync) ## one cycle delay

        with m.If(self.v_x_mailbox.flag & self.v_y_mailbox.flag & self.v_d_mailbox.flag):
            m.d.sync += self.v_x.eq(self.v_x_mailbox.value)
            m.d.sync += self.v_y.eq(self.v_y_mailbox.value)
            m.d.sync += self.v_dwell_time.eq(self.v_d_mailbox.value)
            m.d.sync += self.v_x_mailbox.flag.eq(0)
            m.d.sync += self.v_y_mailbox.flag.eq(0)
            m.d.sync += self.v_d_mailbox.flag.eq(0)
            m.d.sync += self.vector_next.eq(1)
            m.d.sync += self.raster_next.eq(0)
            #m.d.sync += self.scan_mode.eq(ScanMode.Vector)

        with m.If(self.r_x_mailbox.flag & self.r_y_mailbox.flag & self.r_d_mailbox.flag):
            m.d.sync += self.r_x.eq(self.r_x_mailbox.value)
            m.d.sync += self.r_y.eq(self.r_y_mailbox.value)
            with m.If(self.dwell_mode == DwellMode.Constant):
                m.d.sync += self.r_dwell_time.eq(self.r_d_mailbox.value)
                m.d.sync += self.r_d_mailbox.flag.eq(0)
            m.d.sync += self.r_x_mailbox.flag.eq(0)
            m.d.sync += self.r_y_mailbox.flag.eq(0)
            m.d.sync += self.raster_next.eq(1)
            m.d.sync += self.vector_next.eq(0)

        with m.If(self.r_ly_mailbox.flag):
            m.d.sync += self.r_ly.eq(self.r_ly_mailbox.value)
            m.d.sync += self.r_ly_mailbox.flag.eq(0)
            m.d.comb += self.load_next_raster_frame_data.eq(1)

        with m.If(self.r_lx_mailbox.flag):
            m.d.sync += self.r_lx.eq(self.r_lx_mailbox.value)
            m.d.sync += self.r_lx_mailbox.flag.eq(0)
            m.d.comb += self.load_next_raster_frame_data.eq(1)

        with m.If(self.r_uy_mailbox.flag):
            m.d.sync += self.r_uy.eq(self.r_uy_mailbox.value)
            m.d.sync += self.r_uy_mailbox.flag.eq(0)
            m.d.comb += self.load_next_raster_frame_data.eq(1)

        with m.If(self.r_ux_mailbox.flag):
            m.d.sync += self.r_ux.eq(self.r_ux_mailbox.value)
            m.d.sync += self.r_ux_mailbox.flag.eq(0)
            m.d.comb += self.load_next_raster_frame_data.eq(1)

        m.d.comb += self.dwell_pipeline_full.eq(self.dwell_pipeline_level == 4)
        
        with m.If((self.r_d_mailbox.flag) & (self.dwell_mode == DwellMode.Variable)):
            with m.If(~self.dwell_pipeline_full):
                # m.d.comb += self.dwell_mem.writing.eq(1)
                # m.d.comb += self.dwell_mem.pixel_in.eq(self.r_d_mailbox.value)
                m.d.sync += self.r_d_mailbox.flag.eq(0)
                m.d.sync += self.dwell_pipeline_level.eq(self.dwell_pipeline_level + 1)
                m.d.sync += self.r_dwell_time_p3.eq(self.r_d_mailbox.value)
                m.d.sync += self.r_dwell_time_p2.eq(self.r_dwell_time_p3)
                m.d.sync += self.r_dwell_time_p1.eq(self.r_dwell_time_p2)
                m.d.sync += self.r_dwell_time.eq(self.r_dwell_time_p1)
                m.d.sync += self.beam_controller.next_dwell.eq(self.r_dwell_time)
                m.d.comb += self.beam_controller.lock_new_point.eq(1)

        with m.If((self.r_d_mailbox.flag) & (self.dwell_mode == DwellMode.Constant)
        & (self.scan_mode == ScanMode.Raster)):
            m.d.sync += self.r_dwell_time.eq(self.r_d_mailbox.value)
            m.d.sync += self.r_d_mailbox.flag.eq(0)

        with m.FSM() as fsm:
            m.d.comb += self.first_frame.eq(fsm.ongoing("Lock Data"))
            with m.State("No Dwell Started"):
                m.d.comb += self.beam_controller.lock_new_point.eq(1)
                with m.If((self.raster_next)|(self.vector_next)):
                    with m.If((self.dwell_mode == DwellMode.Variable) & (self.raster_next)):
                        with m.If(self.dwell_pipeline_full):
                            m.d.sync += self.rastering.eq((self.raster_next))
                            m.d.comb += self.load_next_raster_frame_data.eq(self.raster_next)
                            m.d.comb += self.beam_controller.lock_new_point.eq(self.beam_controller.end_of_dwell)
                            m.d.sync += self.beam_controller.next_dwell.eq(self.r_dwell_time)
                            m.d.sync += self.dwell_pipeline_level.eq(self.dwell_pipeline_level - 1)
                            m.next = "Lock Data"
                    with m.Else():
                        m.d.sync += self.rastering.eq(self.raster_next)
                        m.d.comb += self.load_next_raster_frame_data.eq(self.raster_next)
                        m.d.sync += self.vectoring.eq(self.vector_next)
                        m.d.comb += self.load_next_vector_values.eq(self.vector_next)
                        m.d.comb += self.xy_scan_gen.increment.eq(1)
                    # m.d.sync += self.raster_next.eq(0)
                    # m.d.sync += self.vector_next.eq(0)
                    
                        m.next = "Lock Data"
            with m.State("Lock Data"):
                m.d.comb += self.xy_scan_gen.increment.eq(1)
                m.d.comb += self.beam_controller.lock_new_point.eq(1)
                m.next = "Dwell Ongoing"
            
            # with m.State("Lock Data2"):
            #     m.next = "Dwell Ongoing"

            with m.State("Dwell Ongoing"):
                m.d.sync += self.beam_controller.dwelling.eq(1)
                m.d.comb += self.beam_controller.lock_new_point.eq(self.beam_controller.end_of_dwell)

                with m.If((self.raster_next)|(self.vector_next)):
                    with m.If(((self.rastering) & (self.xy_scan_gen.frame_sync)) |
                        ((self.vectoring) & (self.beam_controller.end_of_dwell) & (~self.rastering)) |
                        (self.reset)):
                    
                        m.d.sync += self.rastering.eq(self.raster_next)
                        m.d.comb += self.load_next_raster_frame_data.eq(self.raster_next)
                        m.d.sync += self.vectoring.eq(self.vector_next)
                        m.d.comb += self.load_next_vector_values.eq(self.vector_next)

                        m.next = "Dwell Ongoing"

        with m.If((self.rastering)):
            m.d.comb += self.xy_scan_gen.increment.eq((self.beam_controller.end_of_dwell)|(self.first_frame))
            #m.d.sync += self.beam_controller.next_x_position.eq(self.xy_scan_gen.x_scan)
            #m.d.sync += self.beam_controller.next_y_position.eq(self.xy_scan_gen.y_scan)
            m.d.sync += self.beam_controller.next_x_position.eq(self.xy_scan_gen.current_x)
            m.d.sync += self.beam_controller.next_y_position.eq(self.xy_scan_gen.current_y)
            m.d.sync += self.beam_controller.next_dwell.eq(self.r_dwell_time)
        with m.If((self.load_next_raster_frame_data)):
            m.d.sync += self.xy_scan_gen.x_full_frame_resolution.eq(self.r_x)
            m.d.sync += self.xy_scan_gen.x_full_frame_resolution.eq(self.r_y)
            m.d.sync += self.xy_scan_gen.x_lower_limit.eq(self.r_lx)
            m.d.sync += self.xy_scan_gen.y_lower_limit.eq(self.r_ly)
            m.d.sync += self.xy_scan_gen.x_upper_limit.eq(self.r_ux)
            m.d.sync += self.xy_scan_gen.y_upper_limit.eq(self.r_uy)
            m.d.sync += self.beam_controller.next_dwell.eq(self.r_dwell_time)

        with m.If((self.dwell_mode == DwellMode.Variable) & (self.raster_next)
        & (self.beam_controller.end_of_dwell)):
            with m.If(self.dwell_pipeline_full):
                m.d.sync += self.beam_controller.next_dwell.eq(self.r_dwell_time)
                m.d.sync += self.dwell_pipeline_level.eq(self.dwell_pipeline_level - 1)

        with m.If((self.vector_next) & (~self.rastering)):
            m.d.sync  += self.beam_controller.next_dwell.eq(self.v_dwell_time)
            m.d.sync  += self.beam_controller.next_x_position.eq(self.v_x)
            m.d.sync += self.beam_controller.next_y_position.eq(self.v_y)

        return m
    def ports(self):
        return [self.vector_next, self.raster_next, self.load_next_vector_values,
        self.load_next_raster_frame_data, self.rastering, self.vectoring,
        self.r_x, self.r_y, self.r_dwell_time,
        self.v_x, self.v_y, self.v_dwell_time]


def test_modecontroller():
    dut = ModeController()
    def bench():
        yield dut.start_frame.eq(1)
        yield dut.xy_scan_gen.full_frame_size.eq(4)
        yield dut.scan_mode.eq(ScanMode.Raster)
        yield dut.r_x.eq(4)
        yield dut.r_y.eq(4)
        yield dut.r_dwell_time.eq(2)
        yield dut.v_x.eq(5)
        yield dut.v_y.eq(10)
        yield dut.v_dwell_time.eq(3)
        for n in range(4*4*2):
            yield
        yield dut.scan_mode.eq(ScanMode.Vector)
        for n in range(4):
            yield
        yield dut.v_x.eq(6)
        yield dut.v_y.eq(4)
        yield dut.v_dwell_time.eq(4)
        for n in range(4):
            yield

    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("multimode_sim.vcd"):
        sim.run()



# def export_modecontroller():
#     top = ModeController()
#     with open("mode_controller.v", "w") as f:
#         f.write(verilog.convert(top, ports=[self.ports()]))


#test_modecontroller()
#export_modecontroller()


