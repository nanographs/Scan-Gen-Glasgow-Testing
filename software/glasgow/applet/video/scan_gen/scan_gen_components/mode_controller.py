import amaranth
from amaranth import *
from amaranth.sim import Simulator

from beam_controller import BeamController
from xy_scan_gen import XY_Scan_Gen

from addresses import *


class ModeController(Elaboratable):
    def __init__(self, v_x_mailbox, v_y_mailbox, v_d_mailbox,
    r_x_mailbox, r_y_mailbox, r_d_mailbox):
        self.v_x_mailbox = v_x_mailbox
        self.v_y_mailbox = v_y_mailbox
        self.v_d_mailbox = v_d_mailbox
        self.r_x_mailbox = r_x_mailbox
        self.r_y_mailbox = r_y_mailbox
        self.r_d_mailbox = r_d_mailbox

        self.scan_mode = Signal()
        self.raster_next = Signal()
        self.vector_next = Signal()
        self.raster_next_cycle = Signal()
        self.vector_next_cycle = Signal()
        self.beam_controller = BeamController()
        self.xy_scan_gen = XY_Scan_Gen()

        self.v_x = Signal(14)
        self.v_y = Signal(14)
        self.v_dwell_time = Signal(14)

        self.r_x = Signal(14)
        self.r_y= Signal(14)
        self.r_dwell_time = Signal(14)

        self.start_frame = Signal()
        self.scan_single_frame = Signal()

        self.rastering = Signal()
        self.vectoring = Signal()

        self.frame_sync = Signal()

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

        m.d.sync += self.frame_sync.eq(self.xy_scan_gen.frame_sync) ## one cycle delay

        with m.If(~(self.raster_next)):
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
                m.d.sync += self.r_dwell_time.eq(self.r_d_mailbox.value)
                m.d.sync += self.r_x_mailbox.flag.eq(0)
                m.d.sync += self.r_y_mailbox.flag.eq(0)
                m.d.sync += self.r_d_mailbox.flag.eq(0)
                m.d.sync += self.raster_next.eq(1)
                m.d.sync += self.vector_next.eq(0)

            #m.d.sync += self.scan_mode.eq(ScanMode.Raster)
            #m.d.comb += self.xy_scan_gen.increment.eq(1)
            #m.d.sync += self.start_frame.eq(1)

        with m.FSM() as fsm:
            with m.State("No Dwell Started"):
                m.d.comb += self.beam_controller.lock_new_data.eq(1)
                with m.If((self.raster_next)|(self.vector_next)):
                    m.d.sync += self.rastering.eq(self.raster_next)
                    m.d.comb += self.raster_next_cycle.eq(self.raster_next)
                    m.d.sync += self.vectoring.eq(self.vector_next)
                    m.d.comb += self.vector_next_cycle.eq(self.vector_next)
                    # m.d.sync += self.raster_next.eq(0)
                    # m.d.sync += self.vector_next.eq(0)
                    m.next = "Lock Data"
            with m.State("Lock Data"):
                m.d.comb += self.beam_controller.lock_new_data.eq(1)
                m.next = "Dwell Ongoing"
            with m.State("Dwell Ongoing"):
                m.d.sync += self.beam_controller.dwelling.eq(1)
                m.d.comb += self.beam_controller.lock_new_data.eq(self.beam_controller.end_of_dwell)

                with m.If(self.beam_controller.end_of_dwell):
                    with m.If((self.raster_next)|(self.vector_next)):
                        m.d.sync += self.rastering.eq(self.raster_next)
                        m.d.comb += self.raster_next_cycle.eq(self.raster_next)
                        m.d.sync += self.vectoring.eq(self.vector_next)
                        m.d.comb += self.vector_next_cycle.eq(self.vector_next)

                    m.next = "Dwell Ongoing"

        with m.If(self.rastering):
            m.d.comb += self.xy_scan_gen.increment.eq(self.beam_controller.end_of_dwell)
        with m.If(self.raster_next):
            m.d.sync += self.xy_scan_gen.x_lower_limit.eq(0)
            m.d.sync += self.xy_scan_gen.y_lower_limit.eq(0)
            m.d.sync += self.xy_scan_gen.x_upper_limit.eq(self.r_x)
            m.d.sync += self.xy_scan_gen.y_upper_limit.eq(self.r_y)
            m.d.sync += self.beam_controller.next_dwell.eq(self.r_dwell_time)
            m.d.sync += self.beam_controller.next_x_position.eq(self.xy_scan_gen.x_scan)
            m.d.sync += self.beam_controller.next_y_position.eq(self.xy_scan_gen.y_scan)

        with m.If((self.rastering)|(self.raster_next_cycle)|(self.raster_next)):
            with m.FSM() as fsm:
                with m.State("Start New Frame"):
                        with m.If(self.raster_next):
                            m.d.comb += self.xy_scan_gen.increment.eq(1)
                        #with m.If(self.start_frame):
                            m.next = ("Lock Data")
                with m.State("Lock Data"):  
                    with m.If(self.raster_next_cycle):       
                        m.next = "Scanning Frame"
                with m.State("Scanning Frame"):
                    m.d.comb += self.xy_scan_gen.increment.eq(self.beam_controller.end_of_dwell)
                    with m.If(self.frame_sync):
                    #     m.d.sync += self.rastering.eq(0)
                        m.d.sync += self.raster_next.eq(0)
                    #     #m.d.comb += self.xy_scan_gen.reset.eq(1)
                    m.next = "Scanning Frame"

        with m.If(self.vector_next):
            m.d.sync  += self.beam_controller.next_dwell.eq(self.v_dwell_time)
            m.d.sync  += self.beam_controller.next_x_position.eq(self.v_x)
            m.d.sync += self.beam_controller.next_y_position.eq(self.v_y)
        # with m.If(((self.vectoring)|(self.vector_next_cycle)) & (~self.raster_next_cycle)):
        #     with m.FSM() as fsm:
        #         with m.State("Start New Vector Stream"):
        #             m.next = "Lock Data"
        #         with m.State("Lock Data"):
        #             m.d.comb += self.beam_controller.lock_new_data.eq(1)
        #             m.next = "Continous Vector Patterning"
        #         with m.State("Continous Vector Patterning"):
        #             pass
        #             #m.d.comb += self.beam_controller.lock_new_data.eq(self.beam_controller.end_of_dwell)
        return m
    def ports(self):
        return [self.vector_next, self.raster_next, self.vector_next_cycle,
        self.raster_next_cycle, self.rastering, self.vectoring,
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

#test_modecontroller()

