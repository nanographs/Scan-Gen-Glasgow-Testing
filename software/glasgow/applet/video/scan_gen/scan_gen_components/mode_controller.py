import amaranth
from amaranth import *
from amaranth.sim import Simulator

if "glasgow" in __name__: ## running as applet
    from ..scan_gen_components.beam_controller import BeamController
    from ..scan_gen_components.xy_scan_gen import XY_Scan_Gen
    from ..scan_gen_components.byte_packing import Box
    from ..scan_gen_components.addresses import *
else:
    from beam_controller import BeamController
    from xy_scan_gen import XY_Scan_Gen
    from byte_packing import Box
    from addresses import *

class ModeController(Elaboratable):
    '''
    Inputs:
        Mailboxes: see Box()
            - Flag_In
            - Value
        scan_mode: ScanMode.Raster or ScanMode.Vector
        dwell_mode: DwellMode.Constant or DwellMode.Variable
            - this isn't really a good distinction. It's more like,
            dwell times that are synchronized with X and Y values and only
            used once each (ie in a pattern stream) are Variable
            while dwell times that should be used continually until a different
            dwell time is recieved (ie while adjusting dwell time during
            regular imaging) are Constant
        
    Internal signals:
        Stored data:
            r_x: Raster x resolution value
            r_y: Raster y resolution value
            r_dwell_time: Raster dwell time (does this need to be its own thing?)
            r_ux: ROI upper x limit
            r_uy: ROI upper y limit
            r_lx: ROI lower x limit
            r_ly: ROI lower y limit

            v_x: Vector x position value
            v_y: Vector y position value
            v_dwell_time: Vector dwell time value

        State logic ??
            raster_next: True if raster data has been recieved
            vector_next: True if vector data has been recieved
            rastering: If true:
                xy scan gen increment = beam controller end of dwell
                beam controller next dwell <= r_dwell_time
                beam controller next x <= xy scan gen current x
                beam controller next y <= xy scan gen current y

            do_mode_switch: If true, look at raster_next and vector_next to get the next mode
                rastering <= raster_next
                vectoring <= vector next
                load_next_raster_frame_data = raster_next
                load_next_vector_values = vector_next

            load_next_raster_frame_values: If true, values are set in xy_scan_gen:
                x_resolution <= r_x
                y_resolution <= r_y
                for full frame:
                    x_upper_limit <= r_x
                    x_lower_limit <= 0
                    y_upper_limit <= r_y
                    y_lower_limit <= 0
                for ROI:
                    x_upper_limit <= r_ux
                    x_lower_limit <= r_lx
                    y_upper_limit <= r_uy
                    y_lower_limit <= r_ly
            The frame will begin next cycle

        Interpretation of mailbox.flag:
            v_x & v_y & v_dwell_time = new_vector_point_data
            r_x & r_y & r_dwell_time = new_raster_frame_data
            r_ux & r_uy & r_lx & r_ly = new_roi_data
            v_dwell_time | r_dwell_time = new_dwell_time


            
                
    '''
    def __init__(self):
        self.v_x_mailbox = Box()
        self.v_y_mailbox = Box()
        self.v_d_mailbox = Box()
        self.r_x_mailbox = Box()
        self.r_y_mailbox = Box()
        self.r_d_mailbox = Box()
        self.r_uy_mailbox =  Box()
        self.r_ux_mailbox =  Box()
        self.r_ly_mailbox =  Box()
        self.r_lx_mailbox =  Box()

        self.beam_controller = BeamController()
        self.xy_scan_gen = XY_Scan_Gen()

        self.scan_mode = Signal()
        self.dwell_mode = Signal()

        self.raster_next = Signal()
        self.vector_next = Signal()
        self.load_next_raster_frame_data = Signal()
        self.load_next_vector_values = Signal()
        
        self.v_x = Signal(14)
        self.v_y = Signal(14)
        self.v_dwell_time = Signal(16)

        self.r_x = Signal(14)
        self.r_y = Signal(14)
        self.r_ux = Signal(14)
        self.r_uy = Signal(14)
        self.r_lx = Signal(14)
        self.r_ly = Signal(14)
        self.r_dwell_time = Signal(16)

        self.rastering = Signal()
        self.vectoring = Signal()

        self.first_frame = Signal()

        self.reset = Signal()

        self.r_dwell_time_p1 = Signal(16)
        self.r_dwell_time_p2 = Signal(16)
        self.r_dwell_time_p3 = Signal(16)
        self.dwell_pipeline_level = Signal(3)
        self.dwell_pipeline_full = Signal()

        self.new_vector_point_data = Signal()
        self.new_raster_frame_data = Signal()
        self.new_roi_data = Signal()
        self.new_dwell_time = Signal()

        self.do_mode_switch = Signal()

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

        m.d.sync += self.new_vector_point_data.eq(self.v_x_mailbox.flag & 
                                                self.v_y_mailbox.flag &
                                                self.v_d_mailbox.flag)
        m.d.sync += self.new_raster_frame_data.eq(self.r_x_mailbox.flag & 
                                                self.r_y_mailbox.flag & 
                                                self.r_d_mailbox.flag)
        m.d.sync += self.new_roi_data.eq((self.r_ux_mailbox.flag) & 
                                        (self.r_uy_mailbox.flag) & 
                                        (self.r_lx_mailbox.flag) &
                                        (self.r_ly_mailbox.flag))
        m.d.sync += self.new_dwell_time.eq((self.v_d_mailbox.flag) |
                                            self.r_d_mailbox.flag)

        with m.If(self.new_vector_point_data):
            m.d.comb += self.v_x.eq(self.v_x_mailbox.value)
            m.d.comb += self.v_y.eq(self.v_y_mailbox.value)
            m.d.comb += self.v_dwell_time.eq(self.v_d_mailbox.value)
            m.d.comb += self.v_x_mailbox.flag_out.eq(1)
            m.d.comb += self.v_y_mailbox.flag_out.eq(1)
            m.d.comb += self.v_d_mailbox.flag_out.eq(1)
            m.d.sync += self.vector_next.eq(1)
            m.d.sync += self.raster_next.eq(0)
            m.d.sync += self.new_vector_point_data.eq(0)
            #m.d.sync += self.scan_mode.eq(ScanMode.Vector)

        with m.If(self.new_raster_frame_data):
            m.d.sync += self.r_x.eq(self.r_x_mailbox.value)
            m.d.sync += self.r_y.eq(self.r_y_mailbox.value)
            with m.If(self.dwell_mode == DwellMode.Constant):
                m.d.sync += self.r_dwell_time.eq(self.r_d_mailbox.value)
                m.d.comb += self.r_d_mailbox.flag_out.eq(1)
            m.d.comb += self.r_x_mailbox.flag_out.eq(1)
            m.d.comb += self.r_y_mailbox.flag_out.eq(1)
            m.d.sync += self.raster_next.eq(1)
            m.d.sync += self.vector_next.eq(0)
            m.d.sync += self.new_raster_frame_data.eq(0)

        with m.If(self.new_roi_data):
            m.d.sync += self.r_ly.eq(self.r_ly_mailbox.value)
            m.d.comb += self.r_ly_mailbox.flag_out.eq(1)
            m.d.sync += self.r_lx.eq(self.r_lx_mailbox.value)
            m.d.comb += self.r_lx_mailbox.flag_out.eq(1)
            m.d.sync += self.r_uy.eq(self.r_uy_mailbox.value)
            m.d.comb += self.r_uy_mailbox.flag_out.eq(1)
            m.d.sync += self.r_ux.eq(self.r_ux_mailbox.value)
            m.d.comb += self.r_ux_mailbox.flag_out.eq(1)
            m.d.comb += self.load_next_raster_frame_data.eq(1)
            m.d.sync += self.new_roi_data.eq(0)

        m.d.comb += self.dwell_pipeline_full.eq(self.dwell_pipeline_level == 4)
        
        with m.If((self.new_dwell_time) & (self.dwell_mode == DwellMode.Variable)
        & (self.scan_mode == ScanMode.Raster)):
        #### for raster patterning, set up a pipeline for dwell time values
            with m.If(~self.dwell_pipeline_full):
                m.d.sync += self.new_dwell_time.eq(0)
                m.d.sync += self.dwell_pipeline_level.eq(self.dwell_pipeline_level + 1)
                m.d.sync += self.r_dwell_time_p3.eq(self.r_d_mailbox.value)
                m.d.sync += self.r_dwell_time_p2.eq(self.r_dwell_time_p3)
                m.d.sync += self.r_dwell_time_p1.eq(self.r_dwell_time_p2)
                m.d.sync += self.r_dwell_time.eq(self.r_dwell_time_p1)
                m.d.comb += self.beam_controller.next_dwell.eq(self.r_dwell_time)
                m.d.comb += self.beam_controller.lock_new_point.eq(1)

        with m.If((self.new_dwell_time) & (self.dwell_mode == DwellMode.Constant)
        & (self.scan_mode == ScanMode.Raster)):
            m.d.sync += self.r_dwell_time.eq(self.r_d_mailbox.value)
            m.d.sync += self.new_dwell_time.eq(0)


        with m.If(self.do_mode_switch):
            m.d.sync += self.rastering.eq(self.raster_next)
            m.d.comb += self.load_next_raster_frame_data.eq(self.raster_next)
            m.d.sync += self.vectoring.eq(self.vector_next)
            m.d.comb += self.load_next_vector_values.eq(self.vector_next)

        with m.FSM() as fsm:
            m.d.comb += self.first_frame.eq(fsm.ongoing("Lock Data"))
            with m.State("No Dwell Started"):
                m.d.comb += self.beam_controller.lock_new_point.eq(1)
                with m.If((self.raster_next)|(self.vector_next)):
                    with m.If((self.dwell_mode == DwellMode.Variable) & (self.raster_next)):
                        with m.If(self.dwell_pipeline_full):
                            m.d.comb += self.do_mode_switch.eq(1)
                            m.d.comb += self.beam_controller.lock_new_point.eq(self.beam_controller.end_of_dwell)
                            m.d.comb += self.beam_controller.next_dwell.eq(self.r_dwell_time)
                            m.d.sync += self.dwell_pipeline_level.eq(self.dwell_pipeline_level - 1)
                            m.next = "Lock Data"
                    with m.Else():
                        m.d.comb += self.do_mode_switch.eq(1)
                        m.d.comb += self.xy_scan_gen.increment.eq(1)
                    
                        m.next = "Lock Data"
            with m.State("Lock Data"):
                m.d.comb += self.xy_scan_gen.increment.eq(1)
                m.d.comb += self.beam_controller.lock_new_point.eq(1)
                m.next = "Dwell Ongoing"
            
            with m.State("Dwell Ongoing"):
                m.d.comb += self.beam_controller.dwelling.eq(1)
                m.d.comb += self.beam_controller.lock_new_point.eq(self.beam_controller.end_of_dwell)

                with m.If((self.raster_next)|(self.vector_next)):
                    with m.If(((self.rastering) & (self.xy_scan_gen.frame_sync)) |
                        ((self.vectoring) & (self.beam_controller.end_of_dwell) & (~self.rastering)) |
                        (self.reset)):
                    
                        m.d.comb += self.do_mode_switch.eq(1)

                        m.next = "Dwell Ongoing"

        with m.If((self.rastering)):
            m.d.comb += self.xy_scan_gen.increment.eq((self.beam_controller.end_of_dwell)|(self.first_frame))
            #m.d.sync += self.beam_controller.next_x_position.eq(self.xy_scan_gen.x_scan)
            #m.d.sync += self.beam_controller.next_y_position.eq(self.xy_scan_gen.y_scan)
            ### disabled interpolation for now bc it makes it easier to see what's going on
            m.d.comb += self.beam_controller.next_x_position.eq(self.xy_scan_gen.current_x)
            m.d.comb += self.beam_controller.next_y_position.eq(self.xy_scan_gen.current_y)
            m.d.comb += self.beam_controller.next_dwell.eq(self.r_dwell_time)
        with m.If((self.load_next_raster_frame_data)):
            m.d.sync += self.xy_scan_gen.x_full_frame_resolution.eq(self.r_x)
            m.d.sync += self.xy_scan_gen.x_full_frame_resolution.eq(self.r_y)
            m.d.sync += self.xy_scan_gen.x_lower_limit.eq(self.r_lx)
            m.d.sync += self.xy_scan_gen.y_lower_limit.eq(self.r_ly)
            m.d.sync += self.xy_scan_gen.x_upper_limit.eq(self.r_ux)
            m.d.sync += self.xy_scan_gen.y_upper_limit.eq(self.r_uy)
            m.d.comb += self.beam_controller.next_dwell.eq(self.r_dwell_time)

        with m.If((self.dwell_mode == DwellMode.Variable) & (self.raster_next)
        & (self.beam_controller.end_of_dwell)):
            with m.If(self.dwell_pipeline_full):
                m.d.comb += self.beam_controller.next_dwell.eq(self.r_dwell_time)
                m.d.sync += self.dwell_pipeline_level.eq(self.dwell_pipeline_level - 1)

        with m.If((self.vector_next) & (~self.rastering)):
            m.d.comb  += self.beam_controller.next_dwell.eq(self.v_dwell_time)
            m.d.comb  += self.beam_controller.next_x_position.eq(self.v_x)
            m.d.comb += self.beam_controller.next_y_position.eq(self.v_y)

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


