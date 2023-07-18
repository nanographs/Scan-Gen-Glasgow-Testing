import amaranth
from amaranth import *

class RampGenerator(Elaboratable):
    """
    A n-bit up counter with a fixed limit.

    Parameters
    ----------
    limit : int
        The value at which the counter overflows.

    Attributes
    ----------
    en : Signal, in
        The counter is incremented if ``en`` is asserted, and retains
        its value otherwise.
    ovf : Signal, out
        ``ovf`` is asserted when the counter reaches its limit.
    rst: Signal, in
        Count is reset when rst is asserted
    """
    def __init__(self, limit: int):
        ## Number of unique steps to count up to
        self.limit = limit

        # Ports
        self.en  = Signal()
        self.ovf = Signal()
        self.rst = Signal()

        # State
        self.count = Signal(limit.bit_length())
       

    def elaborate(self, platform):
        m = Module()
        with m.If(self.rst):
            m.d.sync += self.count.eq(0)
        
        with m.Else():
            ## evaluate whether counter is at its limit
            m.d.comb += self.ovf.eq(self.count == self.limit-1)

            ## incrementing the counter
            with m.If(self.en):
                with m.If(self.ovf):
                    ## if the counter is at overflow, set it to 0
                    m.d.sync += self.count.eq(0)
                with m.Else():
                    ## else, increment the counter by 1
                    m.d.sync += self.count.eq(self.count + 1)

        return m
    def ports(self):
        return[self.module.en, self.module.ovf, self.module.count]
