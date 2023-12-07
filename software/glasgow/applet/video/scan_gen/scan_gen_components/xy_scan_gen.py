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
    def __init__(self):
        self.x_full_frame_resolution = Signal(16)
        self.y_full_frame_resolution = Signal(16)

        self.x_lower_limit = Signal(16)
        self.x_upper_limit = Signal(16)

        self.y_lower_limit = Signal(16)
        self.y_upper_limit = Signal(16)

        #self.full_frame_size = Signal(14)

        self.increment = Signal()

        self.x_counter = RampGenerator()
        self.y_counter = RampGenerator()

        self.full_frame_size = Signal(16)

        # self.x_interpolator = PixelRatioInterpolator(self.full_frame_size)
        # self.y_interpolator = PixelRatioInterpolator(self.full_frame_size)

        self.x_bigger = Signal()
        self.y_bigger = Signal()

        # self.x_scan = Signal(14)
        # self.y_scan = Signal(14)
        self.current_x = Signal(16)
        self.current_y = Signal(16)

        self.reset = Signal()
        self.frame_sync = Signal()
        self.line_sync = Signal()

        self.aa = Signal()


    def elaborate(self, platform):
        m = Module()
        m.submodules["x_counter"] = self.x_counter
        m.submodules["y_counter"] = self.y_counter
        # m.submodules["x_interpolator"] = self.x_interpolator
        # m.submodules["y_interpolator"] = self.y_interpolator

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

        # m.d.comb += self.x_interpolator.input.eq(self.current_x)
        # m.d.comb += self.y_interpolator.input.eq(self.current_y)

        # m.d.comb += self.x_scan.eq(self.x_interpolator.output)
        # m.d.comb += self.y_scan.eq(self.y_interpolator.output)


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