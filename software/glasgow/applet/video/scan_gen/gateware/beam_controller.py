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

        dwell_time:     5 5 5 5 5 5 6
        next_dwell:               6
        counter:        0 1 2 3 4 5 0
        start_of_dwell: -___________-
        end_of_dwell:   __________-__
        lock_new_point: __________-__

        
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
        
        self.true_counter = Signal(16)

        self.dwelling = Signal()
        self.end_of_dwell = Signal()
        self.at_dwell = Signal()
        
        self.lock_new_point = Signal()

        self.prev_dwelling = Signal()
        self.dwelling_changed = Signal()
        self.prev_dwelling_changed = Signal()

        self.reset = Signal()
        self.freeze = Signal()

    def elaborate(self, platform):
        m = Module()

        with m.If(self.count_enable):
            m.d.comb += self.at_dwell.eq(self.counter == self.dwell_time)

        m.d.comb += self.end_of_dwell.eq(self.at_dwell & ~self.dwelling_changed)
        m.d.sync += self.prev_dwelling.eq(self.dwelling)
        m.d.comb += self.dwelling_changed.eq(self.dwelling != self.prev_dwelling)
        m.d.sync += self.prev_dwelling_changed.eq(self.dwelling_changed)

        with m.If(self.dwelling & ~self.freeze):
            # m.d.comb += self.lock_new_point.eq(self.at_dwell)
            with m.If(self.count_enable):
                with m.If(self.at_dwell):
                    m.d.sync += self.counter.eq(0)
                with m.Else():
                    m.d.sync += self.counter.eq(self.counter + 1)
        with m.Else():
            m.d.sync += self.counter.eq(0)

        with m.If(self.reset): 
            m.d.sync += self.x_position.eq(0)  
            m.d.sync += self.y_position.eq(0)
            m.d.sync += self.dwell_time.eq(0)  
        with m.Else():
            with m.If(self.lock_new_point):
                m.d.sync += self.x_position.eq(self.next_x_position)
                m.d.sync += self.y_position.eq(self.next_y_position)
                m.d.sync += self.dwell_time.eq(self.next_dwell)    


        m.d.sync += self.true_counter.eq(self.true_counter + 1)
        with m.If(self.lock_new_point):
            m.d.sync += self.true_counter.eq(0)

        return m
    def ports(self):
        return [self.x_position, self.y_position, self.dwell_time,
        self.lock_new_point, self.dwelling]


def test_beamcontroller():
    dut = BeamController()
    def bench():
        cycles = 10
        yield dut.dwell_time.eq(cycles)
        yield dut.next_dwell.eq(6)
        yield dut.dwelling.eq(1)
        yield dut.count_enable.eq(1)
        yield
        assert(yield dut.start_dwell)
        for n in range(1,cycles):
            yield
            print("n =", n)
            assert (yield dut.counter == n)
        yield
        assert (yield dut.counter == cycles)
        assert (yield dut.end_of_dwell)
        yield
        assert( yield dut.dwell_time == 6)

        ## counter should not increment when disabled
        yield dut.count_enable.eq(0)
        yield
        yield
        assert(yield dut.counter == 1) 
    
    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("beam_controller_sim.vcd"):
        sim.run()

if __name__ == "__main__":
    test_beamcontroller()