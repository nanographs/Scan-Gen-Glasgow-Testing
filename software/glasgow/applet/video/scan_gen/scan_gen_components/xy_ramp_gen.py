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
    def __init__(self, lower_limit, upper_limit):
        ## Number of unique steps to count up to
        self.lower_limit = lower_limit
        self.upper_limit = upper_limit

        # Ports
        self.increment  = Signal()
        self.ovf = Signal()

        # State
        self.current_count = Signal(14, reset = self.lower_limit)

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



class FrameGenerator(Elaboratable):
    '''
    Height: Number of lines per frame / pixel height of image, 14 bits
    Width: Number of pixels per line / pixel width of image, 14 bits
    '''
    def __init__(self, height, width):
        self.height = height
        self.width = width

        ## state
        self.en = Signal()
        self.line_sync = Signal()
        self.frame_sync = Signal()

        ## frame counter
        self.frame_size = self.width*self.width
        
        ## x and y position values
        self.x_data = Signal(14)
        self.y_data = Signal(14)

        
    def elaborate(self,platform):
        m = Module()

        m.submodules.x_ramp = x_ramp = RampGenerator(self.width)
        m.submodules.y_ramp = y_ramp = RampGenerator(self.height)
        m.d.comb += [x_ramp.en.eq(0),y_ramp.en.eq(0)]

        m.d.comb += [            
        self.line_sync.eq(x_ramp.ovf),
        self.frame_sync.eq(y_ramp.ovf),
        self.x_data.eq(x_ramp.count),
        self.y_data.eq(y_ramp.count)
        ]

        with m.If(self.en):
            ## start counting when enabled
            m.d.comb += x_ramp.en.eq(1)
            with m.If(x_ramp.ovf):
                ## if the x counter is max, increment y
                m.d.comb += y_ramp.en.eq(1)
        return m
        def ports(self):
            return[self.en, self.line_sync, self.frame_sync,
            self.x_data,self.y_data]


# --- TEST ---
def test_rampgenerator():
    test_lower_limit = 2
    test_upper_limit = 5 ## The limit to set for the ramp generator to count up to
    dut = RampGenerator(test_lower_limit, test_upper_limit) # Ramp Generator module
    def bench():
        
        for n in range(test_lower_limit, test_upper_limit):
            yield dut.increment.eq(1)
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
        yield
        yield
        print("-")
        assert(yield dut.current_count == test_lower_limit)
        assert(yield dut.ovf == 0)
        print("reset to 0")
            
    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("ramp_sim.vcd"):
        sim.run()

test_rampgenerator()

def test_framegenerator():
    test_width = 3
    test_height = 4
    dut = FrameGenerator(test_height, test_width)
    def bench():
        for i in range(test_height):
            for j in range(test_width):
                yield dut.en.eq(1)
                yield
                print("-")
                print("x", j)
                assert(yield dut.x_data == j)
            yield
            print("-")
            print("x line sync", test_width)
            assert(yield dut.x_data == test_width)
            assert(yield dut.line_sync)
            print("y", i)
            assert(yield dut.y_data == i)
        yield
        print("-")
        print("y frame sync", test_height)
        assert(yield dut.y_data == test_height)




    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    sim.run()


# print("Ramp Generator Test:")
# test_rampgenerator()
# print("\nFrame Generator Test:")
# test_framegenerator()


class PixelPitchInterpolator(Elaboratable):
    '''
    Takes the output of a counter and convertes it to a value for the DAC

    Paramaters:
    - output_width: Full scale DAC Value

    Atributes:
    - input_width: Signal In
        - width of the frame to scan
    - input: Signal In
        - The value to convert to DAC value
    - output: Signal Out
        - The value for the DAC
    '''

    
    def __init__(self, output_width = 16384):
        self.output_width = output_width ## Full scale DAC value
        self.frame_size = Signal(14) ## Width of the frame to scan

        self.input = Signal(14) ## Current pixel number
        self.output = Signal(14) ## Current pixel number converted to DAC value


    def elaborate(self, platform):
        m = Module()

        m.d.comb += [
            self.output.eq((self.input * self.output_width) // self.frame_size)
            ]

        return m

def test_pixelpitch():
    dut = PixelPitchInterpolator()

    def bench():
        yield dut.input_width.eq(2000)
        for n in range(2000):
            yield dut.increment.eq(1)
            yield
        yield

    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("pitch_sim.vcd"):
        sim.run()

