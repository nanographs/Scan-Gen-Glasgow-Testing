import amaranth
from amaranth import *

class MinDwellCtr(Elaboratable):
    """
    a permanently on counter that counts up to 11

    Attributes
    ----------
    en : Signal, in
        The counter is incremented if ``en`` is asserted, and retains
        its value otherwise.
    ovf : Signal, out
        ``ovf`` is asserted when the counter reaches its limit.
    """
    def __init__(self):
        ## Number of unique steps to count up to
        self.limit = 11

        # Ports
        self.en  = Signal()
        self.ovf = Signal()

        # State
        self.count = Signal(self.limit.bit_length())

    def elaborate(self, platform):
        m = Module()
        ## evaluate whether counter is at its limit
        m.d.comb += self.ovf.eq(self.count == self.limit)

        ## incrementing the counter
        with m.If(1): ## always enabled
            with m.If(self.ovf):
                ## if the counter is at overflow, set it to 0
                m.d.sync += self.count.eq(0)
            with m.Else():
                ## else, increment the counter by 1
                m.d.sync += self.count.eq(self.count + 1)

        return m
    def ports(self):
        return[self.module.en, self.module.ovf, self.module.count]