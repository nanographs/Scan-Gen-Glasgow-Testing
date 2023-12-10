import amaranth
from amaranth import *
from amaranth.sim import Simulator

if "glasgow" in __name__: ## running as applet
    from ..scan_gen_components.ramp_generator import RampGenerator
    from ..scan_gen_components.pixel_ratio_interpolator import PixelRatioInterpolator
else:
    from ramp_generator import RampGenerator, test_ramp
    from pixel_ratio_interpolator import PixelRatioInterpolator

class XY_Scan_Gen(Elaboratable):
    ''' 
    x_counter: see RampGenerator
    y_counter: see RampGenerator

    increment: Signal, in, 1
        If high, the x_counter will be incremented
    line_sync: Signal, out, 1
        Asserted if the x counter is in overflow
    frame_sync: Signal, out, 1
        Asserted if both counters are in overflow
                            _________
                            |   y   |->ovf
            _________       |counter|   |
            |   x   |->ovf->|inc----|   |
            |counter|   |               |
       inc->|inc----|   --->line sync---&-->frame sync

    x_full_frame_resolution: Signal, in, 16
        Number of discrete data points in X
        This is a register-driven value
    y_full_frame_resolution: Signal, in, 16
        Number of discrete data points in Y
        This is a register-driven value

    x_bigger: Signal, 1, out:
        High if x_full_frame_resolution > y_full_frame_resolution
    y_bigger: Signal, 1, out:
        High if x_full_frame_resolution < y_full_frame_resolution
    full_frame_resolution: Signal, 16, out
        The maximum of x_full_frame_resolution or y_full_frame_resolution.
        The number of discrete steps to divide across the full DAC range

    x_upper_limit = Signal, in, 16
    x_lower_limit = Signal, in, 16
    y_upper_limit = Signal, in, 16
    y_lower_limit = Signal, in, 16
        Register-driven values that describe a reduced rectangle area

            0   x_lower    x_upper  x_full
            |-----|-----------|------|
            |     |           |      |
    y_lower-|-----|-----------|------|
            |     |...........|      |
            |     |...........|      |
            |     |...........|      |
    y_upper-|-----|-----------|-------
            |     |           |      |
    y_full -|------------------------|

    '''
    def __init__(self):
        self.x_counter = RampGenerator()
        self.y_counter = RampGenerator()

        self.increment = Signal()
        self.frame_sync = Signal()
        self.line_sync = Signal()

        self.x_full_frame_resolution = Signal(16)
        self.y_full_frame_resolution = Signal(16)

        self.x_bigger = Signal()
        self.y_bigger = Signal()
        self.full_frame_size = Signal(16)
        
        self.x_lower_limit = Signal(16)
        self.x_upper_limit = Signal(16)

        self.y_lower_limit = Signal(16)
        self.y_upper_limit = Signal(16)

        self.current_x = Signal(16)
        self.current_y = Signal(16)

        self.reset = Signal()

    
    def elaborate(self, platform):
        m = Module()
        m.submodules["x_counter"] = self.x_counter
        m.submodules["y_counter"] = self.y_counter

        with m.If(self.increment):
            m.d.comb += self.x_counter.increment.eq(self.increment)
            m.d.comb += self.y_counter.increment.eq(self.x_counter.ovf)

        with m.If(self.reset):
            m.d.comb += self.x_counter.reset.eq(1)
            m.d.comb += self.y_counter.reset.eq(1)

        with m.If(self.x_full_frame_resolution >= self.y_full_frame_resolution):
            m.d.comb += self.full_frame_size.eq(self.x_full_frame_resolution)
            m.d.comb += self.x_bigger.eq(1)

        with m.If(self.x_full_frame_resolution < self.y_full_frame_resolution):
            m.d.comb += self.full_frame_size.eq(self.y_full_frame_resolution)
            m.d.comb += self.y_bigger.eq(1)

        with m.If(self.x_upper_limit <= self.x_lower_limit):
            m.d.comb += self.x_counter.upper_limit.eq(self.x_full_frame_resolution)
        with m.Else():
            m.d.comb += self.x_counter.upper_limit.eq(self.x_upper_limit)

        with m.If(self.y_upper_limit <= self.y_lower_limit):
            m.d.comb += self.y_counter.upper_limit.eq(self.y_full_frame_resolution)
        with m.Else():
            m.d.comb += self.y_counter.upper_limit.eq(self.y_upper_limit)

        with m.If(self.y_upper_limit == 0):
            m.d.comb += self.y_counter.upper_limit.eq(self.y_full_frame_resolution)
            m.d.comb += self.aa.eq(1)
        
        with m.If(self.x_upper_limit == 0):
            m.d.comb += self.x_counter.upper_limit.eq(self.x_full_frame_resolution)

        m.d.comb += self.x_counter.lower_limit.eq(self.x_lower_limit)
        m.d.comb += self.y_counter.lower_limit.eq(self.y_lower_limit)

        m.d.comb += self.frame_sync.eq((self.x_counter.ovf) & (self.y_counter.ovf))
        m.d.comb += self.line_sync.eq((self.x_counter.ovf) & ~(self.y_counter.ovf))
        
        m.d.comb += self.current_x.eq(self.x_counter.current_count)
        m.d.comb += self.current_y.eq(self.y_counter.current_count)

        return m
    def ports(self):
        return [self.increment, self.frame_sync, self.x_scan, self.y_scan]


# --- TEST ---
def test_scangenerator():
    dut = XY_Scan_Gen()
    
    def bench():
        test_x_pixels = 10
        test_y_pixels= 10
        yield dut.x_full_frame_resolution.eq(test_x_pixels)
        yield dut.y_full_frame_resolution.eq(test_y_pixels)

        test_x_lower = 3
        test_x_upper = 7
        test_y_lower = 2
        test_y_upper = 5
        yield dut.x_lower_limit.eq(test_x_lower)
        yield dut.y_lower_limit.eq(test_y_lower)
        yield dut.x_upper_limit.eq(test_x_upper)
        yield dut.y_upper_limit.eq(test_y_upper)
        # yield dut.x_upper_crop.eq(test_x_pixels - test_x_upper)
        # yield dut.y_upper_crop.eq(test_y_pixels - test_y_upper)

        frame_size = max(test_x_pixels, test_y_pixels)
        #yield dut.full_frame_size.eq(frame_size)
        #yield

        yield dut.increment.eq(1)
        yield
        yield dut.increment.eq(0)
        yield
        print("-")

        for i in range(test_y_lower, test_y_upper):
            for j in range(test_x_lower, test_x_upper):
                assert not (yield dut.x_counter.ovf.eq(0))

                print("x", (j*16383)//frame_size)
                assert(yield dut.x_interpolator.input == j)
                assert(yield dut.x_scan == (j*16383)//frame_size)
                print("x passed")

                yield dut.increment.eq(1)
                yield
                yield dut.increment.eq(0)
                yield
                print("-")
                
                yield
                print("-")

            
            print("x line sync")
            assert(yield dut.x_counter.ovf) #line sync
            assert(yield dut.x_scan == (test_x_upper*16383)//frame_size)
            print("x line sync passed")

            yield dut.increment.eq(1)
            yield
            yield dut.increment.eq(0)
            yield
            print("-")

            print("y", i)
            assert(yield dut.y_interpolator.input == i)
            assert(yield dut.y_scan == (i*16383)//frame_size)
            print("y passed")


        yield
        print("-")
        print("y last line", test_y_upper)
        assert(yield dut.y_interpolator.input == test_y_upper)
        assert(yield dut.y_counter.ovf)

        for j in range(test_x_lower, test_x_upper):
            assert not (yield dut.x_counter.ovf.eq(0))
            yield dut.increment.eq(1)
            yield
            print("-")
            print("x", (j*16383)//frame_size)
            assert(yield dut.x_interpolator.input == j)
            assert(yield dut.x_scan == (j*16383)//frame_size)
            print("x passed")
            yield dut.increment.eq(0)
            yield
            print("-")

        yield dut.increment.eq(1)
        yield
        print("-")
        
        print("x line sync")
        assert(yield dut.x_counter.ovf) #line sync
        assert(yield dut.x_scan == (test_x_upper*16383)//frame_size)
        print("x line sync passed")
        assert(yield dut.frame_sync)
        print("frame sync passed")



    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("xy_scan_gen_sim.vcd"):
        sim.run()

def test_scangenerator_new():
    dut = XY_Scan_Gen()
    
    def bench():
        test_x_pixels = 10
        test_y_pixels= 10
        yield dut.x_full_frame_resolution.eq(test_x_pixels)
        yield dut.y_full_frame_resolution.eq(test_y_pixels)
        yield

        for i in range(0,10):
            for j in range(0,10):
                yield from test_ramp(dut, 0,10)

    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("xy_scan_gen_sim.vcd"):
        sim.run()



def sim_scangenerator():
    dut = XY_Scan_Gen()

    def increment():
        yield dut.increment.eq(1)
        yield
        yield dut.increment.eq(0)
        yield
        print("-")
    
    def bench():
        test_x_pixels = 10
        test_y_pixels= 10
        yield dut.x_full_frame_resolution.eq(test_x_pixels)
        yield dut.y_full_frame_resolution.eq(test_y_pixels)
        
        for n in range(3):
            yield from increment()

        # yield dut.x_counter.reset.eq(1)
        # yield

        test_x_lower = 3
        test_x_upper = 7
        test_y_lower = 2
        test_y_upper = 5

        yield dut.x_lower_limit.eq(test_x_lower)
        yield dut.y_lower_limit.eq(test_y_lower)
        yield dut.x_upper_limit.eq(test_x_upper)
        yield dut.y_upper_limit.eq(test_y_upper)
        #yield

        for n in range(10*10):
            yield dut.increment.eq(1)
            yield
            yield dut.increment.eq(0)
            yield


    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("xy_scan_gen_sim.vcd"):
        sim.run()

if __name__ == "__main__":
    test_scangenerator_new()
    #sim_scangenerator()