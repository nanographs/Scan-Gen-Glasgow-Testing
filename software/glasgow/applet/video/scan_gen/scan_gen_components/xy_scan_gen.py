import amaranth
from amaranth import *
from amaranth.sim import Simulator

from ramp_generator import RampGenerator
from pixel_ratio_interpolator import PixelRatioInterpolator


class XY_Scan_Gen(Elaboratable):
    def __init__(self):
        self.x_lower_limit = Signal(14)
        self.x_upper_limit = Signal(14)

        self.y_lower_limit = Signal(14)
        self.y_upper_limit = Signal(14)

        #self.full_frame_size = Signal(14)

        self.increment = Signal()

        self.x_counter = RampGenerator()
        self.y_counter = RampGenerator()

        self.x_interpolator = PixelRatioInterpolator(self.x_upper_limit - self.x_lower_limit)
        self.y_interpolator = PixelRatioInterpolator(self.y_upper_limit - self.y_lower_limit)

        self.x_scan = Signal(14)
        self.y_scan = Signal(14)

        self.reset = Signal()
        self.frame_sync = Signal()


    def elaborate(self, platform):
        m = Module()
        m.submodules["x_counter"] = self.x_counter
        m.submodules["y_counter"] = self.y_counter
        m.submodules["x_interpolator"] = self.x_interpolator
        m.submodules["y_interpolator"] = self.y_interpolator

        with m.If(self.increment):
            m.d.comb += self.x_counter.increment.eq(self.increment)
            m.d.comb += self.y_counter.increment.eq(self.x_counter.ovf)

        with m.If(self.reset):
            m.d.comb += self.x_counter.reset.eq(1)
            m.d.comb += self.y_counter.reset.eq(1)

        m.d.comb += self.frame_sync.eq((self.x_counter.ovf) & (self.y_counter.ovf))
        

        m.d.comb += self.x_counter.upper_limit.eq(self.x_upper_limit - self.x_lower_limit)
        m.d.comb += self.y_counter.upper_limit.eq(self.y_upper_limit - self.y_lower_limit)
        
        m.d.comb += self.x_interpolator.input.eq(self.x_lower_limit + self.x_counter.current_count)
        m.d.comb += self.y_interpolator.input.eq(self.y_lower_limit + self.y_counter.current_count)

        m.d.comb += self.x_scan.eq(self.x_interpolator.output)
        m.d.comb += self.y_scan.eq(self.y_interpolator.output)


        return m
    def ports(self):
        return [self.increment, self.frame_sync, self.x_scan, self.y_scan]


# --- TEST ---
def test_scangenerator():
    dut = XY_Scan_Gen()
    
    def bench():
        test_x_lower_limit = 0
        test_x_upper_limit = 10
        yield dut.x_lower_limit.eq(test_x_lower_limit)
        yield dut.x_upper_limit.eq(test_x_upper_limit)

        test_y_lower_limit = 0
        test_y_upper_limit = 10
        yield dut.y_lower_limit.eq(test_y_lower_limit)
        yield dut.y_upper_limit.eq(test_y_upper_limit)

        test_width = test_x_upper_limit - test_x_lower_limit
        test_height = test_y_upper_limit - test_y_lower_limit
        frame_size = max(test_width, test_height)
        #yield dut.full_frame_size.eq(frame_size)

        for i in range(test_height):
            for j in range(test_width):
                assert not (yield dut.x_counter.ovf.eq(0))
                yield dut.increment.eq(1)
                yield
                print("-")
                print("x", (j*16383)//frame_size)
                #assert(yield dut.x_counter.current_count == j)
                #assert(yield dut.x_scan == (j*16383)//frame_size)
                print("x passed")
                yield dut.increment.eq(0)
                yield
                print("-")

            yield dut.increment.eq(1)
            yield

            print("x line sync")
            assert(yield dut.x_counter.ovf) #line sync
            assert(yield dut.x_scan == 16383)
            print("x line sync passed")

            print("y", i)
            assert(yield dut.y_counter.current_count == i)
            assert(yield dut.y_scan == (i*16383)//frame_size)
            print("y passed")

            yield dut.increment.eq(0)
            yield
            

        yield
        print("-")
        print("y frame sync", test_height)
        assert(yield dut.y_counter.current_count == test_height)



    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("xy_scan_gen_sim.vcd"):
        sim.run()



def sim_scangenerator():
    dut = XY_Scan_Gen()
    
    def bench():
        test_lower_limit = 0
        test_upper_limit = 10
        yield dut.x_lower_limit.eq(test_lower_limit)
        yield dut.x_upper_limit.eq(test_upper_limit)
        yield dut.y_lower_limit.eq(test_lower_limit)
        yield dut.y_upper_limit.eq(test_upper_limit)
        yield dut.full_frame_size.eq(test_upper_limit)
        yield
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

test_scangenerator()