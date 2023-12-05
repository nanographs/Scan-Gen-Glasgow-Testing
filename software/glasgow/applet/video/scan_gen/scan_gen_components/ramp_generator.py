import amaranth
from amaranth import *
from amaranth.sim import Simulator

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
        self.unf = Signal()

        self.current_count = Signal(14)
        self.next_count = Signal(14)

        self.reset = Signal()
        # # State
        # if isinstance(self.lower_limit, int):
        #     self.current_count = Signal(14, reset = self.lower_limit)
        # else:
        #     self.current_count = Signal(14, reset = self.lower_limit.value)

    def elaborate(self, platform):
        m = Module()
        ## evaluate whether counter is at its limit
        m.d.comb += self.ovf.eq(self.current_count >= self.upper_limit)
        m.d.comb += self.unf.eq(self.current_count < self.lower_limit)

        ## incrementing the counter
        with m.If(self.reset):
            m.d.sync += self.current_count.eq(self.lower_limit)
        with m.Else():
            with m.If(self.increment):
                with m.If(self.unf):
                    ## if the counter is at overflow, set it to lower limit
                    m.d.sync += self.current_count.eq(self.lower_limit)
                with m.Elif(self.ovf):
                    ## if the counter is at overflow, set it to lower limit
                    m.d.sync += self.current_count.eq(self.lower_limit)
                with m.Else():
                    ## else, increment the counter by 1
                    m.d.comb += self.next_count.eq(self.current_count + 1)
                    m.d.sync += self.current_count.eq(self.next_count)



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

        def increment():
            yield dut.increment.eq(1) ## Tell the counter to increment
            yield
            print("-")
            yield dut.increment.eq(0)
            yield
            print("-")

        for n in range(test_lower_limit, test_upper_limit+1):
            yield from increment()
            print("checking count", n)
            assert(yield dut.current_count == n) ## Assert that counter equals the next value
            print("count", n, "passed")
        assert(yield dut.ovf)
        yield dut.lower_limit.eq(0)
        yield dut.upper_limit.eq(10)
        for n in range(10):
            yield from increment()

        yield dut.lower_limit.eq(2)
        yield dut.upper_limit.eq(5)
        for n in range(6):
            yield from increment()

        yield dut.lower_limit.eq(7)
        yield dut.upper_limit.eq(10)

        for n in range(10):
            yield from increment()


    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("ramp_sim.vcd"):
        sim.run()



def test_ramp(dut, test_lower_limit, test_upper_limit):
    def increment():
        yield dut.increment.eq(1) ## Tell the counter to increment
        yield
        print("-")
        yield dut.increment.eq(0)
        yield
        print("-")

    for n in range(test_lower_limit, test_upper_limit+1):
        yield from increment()
        #print("checking count", n)
        #assert(yield dut.current_count == n) ## Assert that counter equals the next value
        #print("count", n, "passed")
    #assert(yield dut.ovf)


def test_ramp_basic(
    test_lower_limit, test_upper_limit
):
    dut = RampGenerator() # Ramp Generator module
    def bench():
        yield dut.lower_limit.eq(test_lower_limit)
        yield dut.upper_limit.eq(test_upper_limit)
        yield

        yield from test_ramp(dut, test_lower_limit, test_upper_limit)
    
    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("ramp_sim.vcd"):
        sim.run()


if __name__ == "__main__":
    test_rampgenerator()
    #test_ramp_basic(1,6)