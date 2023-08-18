import amaranth
from amaranth import *
from amaranth.sim import Simulator
import unittest

## dealing with relative imports

if "glasgow" in __name__: ## running as applet
    from ..scan_gen_components.ramps import RampGenerator
    from ..scan_gen_components.dwell_ctr import DwellCtr
    from ..scan_gen_components.min_dwell_ctr import MinDwellCtr
    from ..scan_gen_components.xy_ramp_gen import ScanGenerator
else: ## running as script (simulation)
    from dwell_ctr import DwellCtr
    from min_dwell_ctr import MinDwellCtr
    from xy_ramp_gen import ScanGenerator
    from ramps import RampGenerator

BUS_WRITE_X = 0x01
BUS_WRITE_Y = 0x02
BUS_READ = 0x03
BUS_FIFO_1 = 0x04
BUS_FIFO_2 = 0x05
FIFO_WAIT = 0x06
A_RELEASE = 0x07
OUT_FIFO = 0x08



class ScanIOBus(Elaboratable):
    def __init__(self, resolution_bits, dwell_time_user, mode):
        self.resolution_bits = resolution_bits
        self.dwell_time_user = dwell_time_user
        self.mode = mode #image or pattern

        self.dwell_time = Signal(8)
        self.out_fifo = Signal(8)

        self.bus_state = Signal(8)
        self.x_data = Signal(14)
        self.y_data = Signal(14)



        self.x_latch = Signal()
        self.x_enable = Signal()
        self.y_latch = Signal()
        self.y_enable = Signal()
        self.a_latch = Signal()
        self.a_enable = Signal()
        self.a_clock = Signal()
        self.d_clock = Signal()

        self.line_sync = Signal() 
        self.frame_sync = Signal()

        self.in_fifo_ready = Signal()
        self.out_fifo_ready = Signal()

        self.count_one = Signal()
        self.count_six = Signal()

        self.dwell_ctr_ovf = Signal()

        self.dwell_ctr_limit = Signal(8)

    def elaborate(self, platform):
        m = Module()

        m.submodules.min_dwell_ctr = min_dwell_ctr = MinDwellCtr()
        m.submodules.dwell_ctr = dwell_ctr = DwellCtr()

        

        m.submodules.scan_gen = scan_gen = ScanGenerator(self.resolution_bits) 

    
        m.d.comb += [
            self.x_data.eq(scan_gen.x_data),
            self.y_data.eq(scan_gen.y_data),
            self.line_sync.eq(scan_gen.line_sync),
            self.frame_sync.eq(scan_gen.frame_sync),
            self.x_enable.eq(0), ## default state for X enable
            self.y_enable.eq(0),
            self.a_enable.eq(1)
        ]

        m.d.sync += [
            self.count_one.eq(min_dwell_ctr.count == 1),
            self.count_six.eq(min_dwell_ctr.count > 5),
            
        ]

        with m.If(self.count_six):
            m.d.sync += [
                self.a_clock.eq(0),
                self.d_clock.eq(1)
            ]
        with m.Else():
            m.d.sync += [
                self.a_clock.eq(1),
                self.d_clock.eq(0)
            ]


        m.d.comb += self.dwell_ctr_ovf.eq(0)
        with m.If(dwell_ctr.count >= self.out_fifo):
        #with m.If(dwell_ctr.count >= 1):
            m.d.comb += self.dwell_ctr_ovf.eq(1)
        


        # m.d.comb += [scan_gen.rst.eq(0),
        #     scan_gen.x_rst.eq(0)]

        # with m.If(self.out_fifo == 0): ## frame sync
        #     m.d.comb += [scan_gen.rst.eq(1)]

        # with m.If(self.out_fifo == 1): ## line sync
        #     m.d.comb += [scan_gen.x_rst.eq(1)]

        

        with m.FSM() as fsm:
            if self.mode == "pattern" or self.mode == "pattern_out":
                with m.State("Wait_For_First_USB_Data"):
                    with m.If(self.out_fifo_ready):
                        m.d.comb += [self.bus_state.eq(OUT_FIFO)]
                        m.next = "WAIT"

            with m.State("WAIT"):
                with m.If(self.count_one):
                    with m.If(self.dwell_ctr_ovf):
                        m.d.comb += [
                            dwell_ctr.rst.eq(1),
                            scan_gen.en.eq(1)
                        ]
                        if self.mode == "pattern" or self.mode == "pattern_out":
                            m.d.comb += self.bus_state.eq(OUT_FIFO)


                    with m.Else():
                        m.d.comb += dwell_ctr.en.eq(1)
                    m.next = "X WRITE"
                with m.Else():
                    m.next = "WAIT"


            with m.State("X WRITE"):
                m.d.comb += self.bus_state.eq(BUS_WRITE_X)
                m.d.comb += self.x_latch.eq(0)
                m.next = "X LATCH"

            with m.State("X LATCH"):
                m.d.comb += self.bus_state.eq(BUS_WRITE_X)
                m.d.comb += self.x_latch.eq(1)
                m.next = "X RELEASE"
            
            with m.State("X RELEASE"):
                m.d.comb += self.bus_state.eq(BUS_WRITE_X)
                m.d.comb += self.x_latch.eq(0)
                m.next = "Y WRITE"

            with m.State("Y WRITE"):
                m.d.comb += self.bus_state.eq(BUS_WRITE_Y)
                m.d.comb += self.y_latch.eq(0)
                m.next = "Y LATCH"

            with m.State("Y LATCH"):
                m.d.comb += self.bus_state.eq(BUS_WRITE_Y)
                m.d.comb += self.y_latch.eq(1)
                m.next = "Y RELEASE"

            with m.State("Y RELEASE"):
                m.d.comb += self.bus_state.eq(BUS_WRITE_Y)
                m.d.comb += self.y_latch.eq(0)
                # if self.mode == "pattern_out":
                #     with m.If(self.out_fifo_ready):
                #         m.next = "WAIT"
                #         #m.next = "Wait_For_First_USB_Data"
                # else: 
                m.next = "A LATCH & ENABLE"

            with m.State("A LATCH & ENABLE"):
                m.d.comb += [                  
                    self.a_latch.eq(1),
                    self.a_enable.eq(0)
                ]
                m.next = "A READ"

            with m.State("A READ"):
                m.d.comb += self.a_enable.eq(0)
                m.d.comb += self.bus_state.eq(BUS_READ)
                m.next = "A RELEASE"

            with m.State("A RELEASE"):
                m.d.comb += self.a_enable.eq(0)
                m.d.comb += self.bus_state.eq(A_RELEASE)
                if self.mode == "image":
                    with m.If(self.in_fifo_ready):
                        m.next = "FIFO_1"
                if self.mode == "pattern":
                    with m.If(self.in_fifo_ready & self.out_fifo_ready):
                        m.next = "FIFO_1"
                if self.mode == "pattern_out":
                    m.next = "FIFO_1"

                        
            with m.State("FIFO_1"):
                if self.mode == "pattern" or self.mode == "pattern_out":
                    with m.If(self.out_fifo >= 2):
                        m.d.comb += self.bus_state.eq(BUS_FIFO_1)
                else:
                    m.d.comb += self.bus_state.eq(BUS_FIFO_1)
                if self.mode == "image":
                    with m.If(self.in_fifo_ready):
                        m.next = "FIFO_2"
                if self.mode == "pattern":
                    with m.If(self.in_fifo_ready):
                        m.next = "FIFO_2"
                if self.mode == "pattern_out":
                    m.next = "FIFO_2"

                    
            with m.State("FIFO_2"):
                m.d.comb += self.bus_state.eq(BUS_FIFO_2)
                m.next = "WAIT"

        return m
    def ports(self):
        return [self.x_data, self.y_data, self.x_latch, self.x_enable,
        self.y_latch, self.y_enable, self.a_latch, self.a_enable, self.bus_state]


# --- TEST ---

def run_sim():
    dut = ScanIOBus(4,8,mode="image") # 16 x 16
    def bench():
        yield dut.in_fifo_ready.eq(1)
        yield dut.out_fifo_ready.eq(1)
        yield dut.out_fifo.eq(3)
        for _ in range(4096):
            yield
        yield


    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("scan_sim_bus.vcd"):
        sim.run()

def test_case():
    dut = ScanIOBus(4) # 16 x 16
    def bench():
        yield dut.in_fifo_ready.eq(1)
        


    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    sim.run()


if __name__ == "__main__":
    run_sim()