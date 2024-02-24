import amaranth
from amaranth import *
from amaranth.sim import Simulator

class MinDwellCtr(Elaboratable):
    def __init__(self,half_freq): # half_period
        self.half_freq = half_freq
        self.clock = Signal()
    def elaborate(self, platform):
        m = Module()
        timer = Signal(range(self.half_freq))
        with m.If(timer == self.half_freq - 1):
            m.d.sync += [
                timer.eq(0),
                self.clock.eq(~self.clock)
            ]
        with m.Else():
            m.d.sync += timer.eq(timer + 1)
        return m


## latch states
TRANSPARENT = b'01'
LATCHED = b'00'
HIGH_IMPEDANCE = b'10'

class DataLatch(Elaboratable):
    def __init__(self):
        self.le = Signal()
        self.oe = Signal()
        # self.state = Signal(2)
    def elaborate(self, platform):
        m = Module()

        # m.d.comb += [
        #     Cat(self.oe, self.le).eq(self.state)
        # ]
        return m

# from amaranth.lib import wiring
# from amaranth.lib.wiring import In, Out
# DATA_LATCH = wiring.Signature({
#     "le": Out(1),
#     "oe": Out(1),
# })
# x = DATA_LATCH.create(); x.le # (sig 1)

class DACSample(Elaboratable):
    '''
    oe:        -----
    le:        __-__
    sampling:  _---_
    released:  ___-_
    '''
    def __init__(self):
        self.latch = DataLatch()
        self.sampling = Signal()
        self.released = Signal()
    def elaborate(self, platform):
        m = Module()
        m.submodules.latch = latch = self.latch
        m.d.comb += [
            latch.oe.eq(0),
            latch.le.eq(0)
        ]

        with m.If(self.sampling):
            with m.FSM() as fsm:
                m.d.comb += self.released.eq(fsm.ongoing("Release"))
                with m.State("Write"):
                    m.next = "Latch"
                with m.State("Latch"):
                    m.d.comb += latch.le.eq(1)
                    m.next = "Release"
                with m.State("Release"):
                    m.next = "Write"
        return m

def test_DACSample():
    dut = DACSample()
    def bench():
        yield dut.sampling.eq(1)
        assert (yield dut.latch.oe.eq(1))
        assert (yield dut.latch.le.eq(0))
        yield
        assert (yield dut.latch.oe.eq(1))
        assert (yield dut.latch.le.eq(1))
        yield
        assert (yield dut.latch.oe.eq(1))
        assert (yield dut.latch.le.eq(0))
    
    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    sim.run()


class ADCSample(Elaboratable):
    '''
    oe:        --_--
    le:        __-__
    sampling:  _---_
    released:  ___-_
    '''
    def __init__(self):
        self.latch = DataLatch()
        self.sampling = Signal()
        self.released = Signal()

    def elaborate(self, platform):
        m = Module()
        m.submodules.latch = latch = self.latch
        m.d.comb += [
            latch.oe.eq(1),
            latch.le.eq(0)
        ]

        with m.If(self.sampling):
            with m.FSM() as fsm:
                m.d.comb += self.released.eq(fsm.ongoing("Release"))
                with m.State("Latch & Enable"):
                    m.d.comb += [ 
                        latch.oe.eq(0),                 
                        latch.le.eq(1)
                    ]
                    m.next = "Read"

                with m.State("Read"):
                    m.next = "Release"

                with m.State("Release"):
                    m.next = "Latch & Enable"
        return m


class BusMultiplexer(Elaboratable):
    '''
    X -> Y -> A -> X...
    '''
    def __init__(self):
        self.x_dac = DACSample()
        self.y_dac = DACSample()
        self.a_adc = ADCSample()
        self.sample_clock = MinDwellCtr(12)
        self.sampling = Signal()

        self.is_x = Signal()
        self.is_y = Signal()
        self.is_a = Signal()
        self.is_done = Signal()

        self.a_clock = Signal()
        self.d_clock = Signal()

    def elaborate(self, platform):
        m = Module()

        m.submodules.x_dac = x_dac = self.x_dac
        m.submodules.y_dac = y_dac = self.y_dac
        m.submodules.a_adc = a_adc = self.a_adc

        m.submodules.sample_clock = sample_clock = self.sample_clock

        m.d.comb += self.a_clock.eq(~self.sample_clock.clock)
        m.d.comb += self.d_clock.eq(self.sample_clock.clock)

        
        with m.If(self.sampling):
            with m.FSM() as fsm:
                m.d.comb += self.is_x.eq(fsm.ongoing("X"))
                m.d.comb += self.is_y.eq(fsm.ongoing("Y"))
                m.d.comb += self.is_a.eq(fsm.ongoing("A"))
                m.d.comb += self.is_done.eq(fsm.ongoing("Start"))

                with m.State("Start"):
                        m.next = "X"
                with m.State("X"):
                    m.d.comb += x_dac.sampling.eq(1)
                    with m.If(x_dac.released):
                        m.next = "Y"
                with m.State("Y"):
                    m.d.comb += y_dac.sampling.eq(1)
                    with m.If(y_dac.released):
                        m.next = "Wait for A"
                with m.State("Wait for A"):
                    with m.If(self.d_clock):
                        m.next = "A"
                with m.State("A"):
                    m.d.comb += a_adc.sampling.eq(1)
                    with m.If(a_adc.released):
                        m.next = "Wait"
                with m.State("Wait"):
                    with m.If(self.a_clock):
                        m.next = "Start"

        return m


if __name__ == "__main__":
    dut = BusMultiplexer()
    def bench():
        for n in range(24):
            yield dut.sampling.eq(1)
            yield
    
    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("new_bus_sim.vcd"):
        sim.run()

