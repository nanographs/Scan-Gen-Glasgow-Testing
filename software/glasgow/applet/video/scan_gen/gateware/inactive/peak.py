import amaranth
from amaranth import *
from amaranth.sim import Simulator
from amaranth.lib import data, enum

class PeakDetect(Elaboratable):
    def __init__(self):
        self.input = Signal(shape = signed(16))
    def elaborate(self, platform):
        m = Module()
        prev_input = Signal(shape = signed(16))
        m.d.sync += prev_input.eq(self.input)
        dx = Signal(shape = signed(16))
        m.d.sync += dx.eq(self.input-prev_input)
        prev_dx = Signal(shape = signed(16))
        m.d.sync += prev_dx.eq(dx)
        d2x = Signal(shape = signed(16))
        m.d.sync += d2x.eq(dx - prev_dx)

        peak = Signal()
        with m.If((dx == 0) & (d2x < 0)):
            m.d.comb += peak.eq(1)
        return m
        


if __name__ == "__main__":
    def peak_sim():
        dut = PeakDetect()
        def function():
            x = 0
            while True:
                y = 200 - (x-5)*(x-6)
                yield y
                x += 1

        def bench():
            f = function()
            for n in range(20):
                yield dut.input.eq(next(f))
                yield

        sim = Simulator(dut)
        sim.add_clock(2.083333e-8) # 48 MHz
        sim.add_sync_process(bench)
        with sim.write_vcd("pulse_sim.vcd"):
            sim.run()

    peak_sim()
