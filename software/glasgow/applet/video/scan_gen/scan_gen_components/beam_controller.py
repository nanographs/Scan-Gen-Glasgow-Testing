import amaranth
from amaranth import *
from amaranth.sim import Simulator

class BeamController(Elaboratable):
    '''
    
    Attributes:
        X position, y position: 14-bit values
        Dwell time : 14 bit value
        Dwelling - True when counter will be incremented next cycle
        Counter - Value that is incremented each cycle and compared to dwell time

    '''
    def __init__(self):

        self.x_position = Signal(14)
        self.y_position = Signal(14)
        self.dwell_time = Signal(14)

        self.next_x_position = Signal(14)
        self.next_y_position = Signal(14)
        self.next_dwell = Signal(14)
        self.dwelling = Signal()
        self.end_of_dwell = Signal()
        self.start_dwell = Signal()

        self.counter = Signal(14)

        self.lock_new_point = Signal()
        self.reset_dwell_ctr = Signal()



        self.fresh_data = Signal()
        self.stale_data = Signal()

    def elaborate(self, platform):
        m = Module()
        m.d.comb += self.end_of_dwell.eq(self.counter == self.dwell_time)
        m.d.comb += self.start_dwell.eq(self.counter == 0)

        with m.If(self.dwelling):
            m.d.comb += self.lock_new_point.eq(self.end_of_dwell)
            with m.If(self.end_of_dwell):
                m.d.sync += self.counter.eq(0)
            with m.Else():
                m.d.sync += self.counter.eq(self.counter + 1)
        with m.Else():
            m.d.sync += self.counter.eq(0)
                
        with m.If(self.lock_new_point):
            m.d.sync += self.x_position.eq(self.next_x_position)
            m.d.sync += self.y_position.eq(self.next_y_position)
            m.d.sync += self.dwell_time.eq(self.next_dwell)     
        return m
    def ports(self):
        return [self.x_position, self.y_position, self.dwell_time,
        self.lock_new_point, self.dwelling]


def test_beamcontroller():
    dut = BeamController()
    def bench():
        cycles = 24
        yield dut.dwell_time.eq(cycles)
        yield dut.dwelling.eq(1)
        yield
        for n in range(cycles):
            assert (yield dut.counter == n)
            yield
            
    
    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    sim.run()