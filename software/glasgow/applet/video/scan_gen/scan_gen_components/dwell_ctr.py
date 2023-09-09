import amaranth
from amaranth import *

class DwellCtr(Elaboratable):
    """
    a permanently on counter that counts up to 11

    Attributes
    ----------
    en : Signal, in
        The counter is incremented if ``en`` is asserted, and retains
        its value otherwise.
    rst : Signal, in
        if rst is asserted, the counter is reset to 0
    """
    def __init__(self):

        # Ports
        self.en  = Signal()
        self.rst = Signal()

        # State
        self.count = Signal(8)

    def elaborate(self, platform):
        m = Module()

        with m.If(self.rst):
            m.d.sync += self.count.eq(0) ## reset counter

        with m.Else():
            with m.If(self.en): ## if enabled
                m.d.sync += self.count.eq(self.count + 1) ## increment

        return m
    def ports(self):
        return[self.module.en, self.module.rst, self.module.count]