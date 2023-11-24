import amaranth
from amaranth import *
from amaranth.sim import Simulator

class RampGenerator(Elaboratable):
    """
    A n-bit up counter with a fixed limit.

    Parameters
    ----------
    lower_limit : Signal (14)
        The value at which the counter starts
    upper_limit : Signal (14)
        The value at which the counter overflows.

    Attributes
    ----------
    increment : Signal, in
        The counter is incremented if ``en`` is asserted, and retains
        its value otherwise.
    ovf : Signal, out
        ``ovf`` is asserted when the counter reaches its limit.
    current_count: Signal, out
        The current number that the counter is at
    """
    def __init__(self):
        ## Number of unique steps to count up to
        self.lower_limit = Signal(14)
        self.upper_limit = Signal(14, reset = 1)

        # Ports
        self.increment  = Signal()
        self.ovf = Signal()

        self.current_count = Signal(14)
        # # State
        # if isinstance(self.lower_limit, int):
        #     self.current_count = Signal(14, reset = self.lower_limit)
        # else:
        #     self.current_count = Signal(14, reset = self.lower_limit.value)

    def elaborate(self, platform):
        m = Module()
        ## evaluate whether counter is at its limit
        m.d.comb += self.ovf.eq(self.current_count == self.upper_limit)
        m.d.comb += self.increment.eq(0)

        ## incrementing the counter
        with m.If(self.increment):
            with m.If(self.ovf):
                ## if the counter is at overflow, set it to lower limit
                m.d.sync += self.current_count.eq(self.lower_limit)
            with m.Else():
                ## else, increment the counter by 1
                m.d.sync += self.current_count.eq(self.current_count + 1)

        return m



# --- TEST ---
def test_rampgenerator():
    test_lower_limit = 2
    test_upper_limit = 5 ## The limit to set for the ramp generator to count up to
    dut = RampGenerator() # Ramp Generator module
    def bench():
        yield dut.lower_limit.eq(test_lower_limit)
        yield dut.upper_limit.eq(test_upper_limit)
        yield
        for n in range(test_lower_limit, test_upper_limit):
            yield dut.increment.eq(1) ## Tell the counter to increment
            yield
            print("checking count", n)
            assert(yield dut.current_count == n) ## Assert that counter equals the next value
            print("count", n, "passed")
            yield
            print("-")
            

        print("limit overflow", test_upper_limit)
        assert(yield dut.current_count == test_upper_limit)
        assert(yield dut.ovf) ## counter should overflow
        yield dut.increment.eq(1)
        yield # Clock cycle for increment to be high
        yield # Clock cycle where we expect the value to have been incremented
        print("-")
        assert(yield dut.current_count == test_lower_limit) ## Counter should reset to lower limit
        assert(yield dut.ovf == 0) ## Overflow should no longer be high
        print("reset to 0")
            
    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("ramp_sim.vcd"):
        sim.run()

test_rampgenerator()