import amaranth
from amaranth import *
from amaranth.sim import Simulator


class SN74ALVCH16373(Elaboratable):
    def __init__(self):
        self.le = Signal()
        self.d = Signal(16)
        self.q = Signal(16)
    def elaborate(self, platform):
        m = Module()
        prev_le = Signal()
        q0 = Signal(16)
        t = Signal()
        m.d.sync += prev_le.eq(self.le)
        with m.If((self.le)):
            m.d.comb += self.q.eq(self.d)
            m.d.sync += q0.eq(self.d)
        with m.If((prev_le) & (~(self.le))): ## falling edge of LE
            m.d.sync += q0.eq(self.d)
        with m.If(~(self.le)):
            m.d.comb += self.q.eq(q0)

        return m


class AD9744(Elaboratable):
    def __init__(self):
        self.clock = Signal()
        self.d = Signal(14)
        self.a = Signal(14) # analog output
    def elaborate(self, platform):
        m = Module()
        prev_clock = Signal()
        d0 = Signal(14) # latched input
        m.d.sync += prev_clock.eq(self.clock)
        m.d.comb += self.a.eq(d0)

        with m.If((self.clock) & (~(prev_clock))): # falling edge of clock
            m.d.sync += d0.eq(self.d)
        return m

class LTC2246H(Elaboratable):
    def __init__(self):
        self.clock = Signal()
        self.a = Signal(14) # analog input
        self.d = Signal(14)
    def elaborate(self, platform):
        m = Module()
        prev_clock = Signal()
        m.d.sync += prev_clock.eq(self.clock)

        sample_n_minus_5 = Signal(14)
        sample_n_minus_4 = Signal(14)
        sample_n_minus_3 = Signal(14)
        sample_n_minus_2 = Signal(14)
        sample_n_minus_1 = Signal(14)
        sample_n = Signal(14)

        m.d.comb += self.d.eq(sample_n_minus_5)

        t = Signal()

        with m.If((self.clock) & (~(prev_clock))): # rising edge of clock
            m.d.comb += t.eq(1)
            m.d.sync += sample_n.eq(self.a)
            m.d.sync += sample_n_minus_1.eq(sample_n)
            m.d.sync += sample_n_minus_2.eq(sample_n_minus_1)
            m.d.sync += sample_n_minus_3.eq(sample_n_minus_2)
            m.d.sync += sample_n_minus_4.eq(sample_n_minus_3)
            m.d.sync += sample_n_minus_5.eq(sample_n_minus_4)
        return m


class OBI_Board(Elaboratable):
    def __init__(self):
        ## digital inputs
        self.x_latch = Signal()
        self.y_latch = Signal()
        self.a_latch = Signal()
        self.a_enable = Signal()
        self.d_clock = Signal()
        self.a_clock = Signal()
        ## simulated analog input
        self.adc_input = Signal(14)
        ## simulated hardware
        self.x_latch_chip = SN74ALVCH16373()
        self.y_latch_chip = SN74ALVCH16373()
        self.a_latch_chip = SN74ALVCH16373()
        self.x_dac_chip = AD9744()
        self.y_dac_chip = AD9744()
        self.a_adc_chip = LTC2246H()
    def elaborate(self, platform):
        m = Module()
        m.submodules["x_latch"] = self.x_latch_chip
        m.submodules["y_latch"] = self.y_latch_chip
        m.submodules["a_latch"] = self.a_latch_chip
        m.submodules["x_dac"] = self.x_dac_chip
        m.submodules["y_dac"] = self.y_dac_chip
        m.submodules["adc"] = self.a_adc_chip

        m.d.comb += self.x_latch_chip.le.eq(self.x_latch)
        m.d.comb += self.y_latch_chip.le.eq(self.y_latch)
        m.d.comb += self.a_latch_chip.le.eq(self.a_latch)
        m.d.comb += self.x_dac_chip.clock.eq(self.d_clock)
        m.d.comb += self.y_dac_chip.clock.eq(self.d_clock)
        m.d.comb += self.a_adc_chip.clock.eq(self.a_clock)
        m.d.comb += self.x_dac_chip.d.eq(self.x_latch_chip.q)
        m.d.comb += self.y_dac_chip.d.eq(self.y_latch_chip.q)
        m.d.comb += self.a_latch_chip.d.eq(self.a_adc_chip.d)
        m.d.comb += self.a_adc_chip.a.eq(self.adc_input)
        return m