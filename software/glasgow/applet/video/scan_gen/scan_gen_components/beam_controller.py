import amaranth
from amaranth import *
from amaranth.sim import Simulator

class BeamController(Elaboratable):
    '''
    
    Attributes:
        x_position, y_position: Signal, 14
        dwell_time : Signal, 16

        next_x_position, next_y_position, next_dwell
            Values to be assigned to x_position, y_position, and dwell_time when lock_new_data is true
        
        counter: Signal, 16, out
            Value that is incremented each cycle and compared to dwell time
        count_enable: Signal, 1,in
            The counter is only incremented if this signal is high. This signal is strobed at
            the end of every min dwell clock cycle

        dwelling: Signal, 1, out
            True when counter will be incremented next cycle
        end_of_dwell: Signal, 1, out
            True when the value of counter is equal to the value of dwell_time.
        start_dwell: Signal, 1, out
            True when the value of counter equals zero

        lock_new_point: Signal, 1, internal
            This signal is driven by end_of_dwell. If this signal is high, the values of
            x_position, y_position, and dwell_time will be set to next_x_position, next_y_position,
            and next_dwell.

        
        prev_dwelling: Signal, 1, internal
            Assigned the value of dwelling from one cycle previously
        dwelling_changed: Signal, 1, internal
            True if dwelling and prev_dwelling are different
        prev_dwelling_changed: Signal, 1, out
            Assigned the value of prev_dwelling from one cycle previously

        dwelling:              __---
        prev_dwelling:         ___--
        dwelling_changed:      ___-_
        prev_dwelling_changed: ____-


    '''
    def __init__(self):

        self.x_position = Signal(14)
        self.y_position = Signal(14)
        self.dwell_time = Signal(14)

        self.next_x_position = Signal(14)
        self.next_y_position = Signal(14)
        self.next_dwell = Signal(16)

        self.counter = Signal(16)
        self.count_enable = Signal()

        self.dwelling = Signal()
        self.end_of_dwell = Signal()
        self.start_dwell = Signal()
        
        self.lock_new_point = Signal()

        self.prev_dwelling = Signal()
        self.dwelling_changed = Signal()
        self.prev_dwelling_changed = Signal()

    def elaborate(self, platform):
        m = Module()
        with m.If(self.count_enable):
            m.d.comb += self.end_of_dwell.eq(self.counter == self.dwell_time)
            m.d.comb += self.start_dwell.eq(self.counter == 0)

        m.d.sync += self.prev_dwelling.eq(self.dwelling)
        m.d.comb += self.dwelling_changed.eq(self.dwelling != self.prev_dwelling)
        m.d.sync += self.prev_dwelling_changed.eq(self.dwelling_changed)

        with m.If(self.dwelling):
            m.d.comb += self.lock_new_point.eq(self.end_of_dwell)
            with m.If(self.count_enable):
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