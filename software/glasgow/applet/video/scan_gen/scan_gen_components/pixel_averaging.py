import amaranth
from amaranth import *
from amaranth.sim import Simulator
from ramps import RampGenerator

### turn a tiff into a stream of bits
from tifffile import imread, imwrite
import numpy as np
import random
from statistics import mean

image = imread("software/glasgow/applet/video/scan_gen/scan_gen_components/WD25.tif")
height, width = image.shape

## turn a tiff into a stream of integers or bits
# image_bits = []
image_bytes = []
for i in range(height):
    for j in range(width):
        p = image[i][j]
        n_stack = [p]*10
        variation = np.random.randint(1,10,10)
        n_stack_varied = np.add(n_stack,variation)
        image_bytes += n_stack_varied.tolist()
        # for n in n_stack_varied:
        #     n_binary = '{0:08b}'.format(n)
        #     image_bits.append(n_binary)
#image_bits_ = iter(image_bits)
image_bytes_ = iter(image_bytes)

print(image_bytes[:30])

EXTERNAL = 0x00
WRITE = 0x01
CALCULATE = 0x02
INCREMENT = 0x03
SHUFFLE = 0x04

class Pixel_Average(Elaboratable):
    def __init__(self):
        self.running_average = Signal(15)
        self.average_output = Signal(14)
        self.Running_Averager_Load_Data = Signal()
        self.DwellAveragerReset = Signal()
        self.running_average_two = Signal(14)
        self.in_pixel_2 = Signal()
        
        
        self.P1 = Signal(14)
        self.P2 = Signal(14)
        self.dwell_time = 10
        self.ovf = Signal()
        self.state = Signal(8)
    def elaborate(self,platform):
        m = Module()
        self.in_pixel = Signal(14)
        m.submodules.dwell_ctr = dwell_ctr = RampGenerator(self.dwell_time)
        m.d.comb += [dwell_ctr.en.eq(0)]
        # m.d.sync += [
        # self.current_pixel.eq(self.in_pixel)]
        # with m.If(dwell_ctr.ovf):
        #     m.d.comb += self.running_average.eq(0)
        # with m.Else():
        #     m.d.comb += self.running_average.eq((self.running_average + self.current_pixel)//2)

        with m.FSM():
            with m.State("External"):
                m.d.comb += self.state.eq(EXTERNAL)
                m.next = "Write"
            with m.State("Write"):
                m.d.comb += self.state.eq(WRITE)
                m.d.sync += [
                    self.Running_Averager_Load_Data.eq(1),
                    self.P1.eq(self.in_pixel),
                    
                    ]
                with m.If(self.P2):
                    m.next = "Calculate"
                with m.Else():
                    m.d.sync += [
                        self.running_average.eq(self.P1),
                        self.DwellAveragerReset.eq(1)
                        ]
                    m.next = "Increment"
            with m.State("Calculate"):
                m.d.comb += self.state.eq(CALCULATE)
                m.d.sync += self.running_average.eq((self.P1 + self.P2)//2)
                m.next = "Increment"
            with m.State("Increment"):
                m.d.comb += self.state.eq(INCREMENT)
                m.d.comb += dwell_ctr.en.eq(1)
                m.next = "Shuffle"
            with m.State("Shuffle"):
                m.d.comb += [
                    self.state.eq(SHUFFLE)
                ]
                with m.If(dwell_ctr.ovf):
                    m.d.sync += [self.average_output.eq(self.running_average),
                    self.P2.eq(0)]

                with m.Else():
                    m.d.sync += self.P2.eq(self.running_average)
                m.next = "External"

        with m.If(self.Running_Averager_Load_Data):
            with m.If(self.DwellAveragerReset):
                m.d.sync += [
                    self.DwellAveragerReset.eq(0),
                    self.running_average_two.eq(self.in_pixel),
                    self.Running_Averager_Load_Data.eq(0)
                ]
            with m.Else():
                m.d.sync += [
                    self.running_average_two.eq((self.running_average_two + self.in_pixel)//2),
                    self.Running_Averager_Load_Data.eq(0)
                ]



        return m
    def ports(self):
        return[self.submodules.dwell_ctr, self.ovf, self.running_average, 
        self.in_pixel, self.P1, self.P2, self.state, self.average_output]

def test():
    
    dut = Pixel_Average()
    def bench():
        clock_cycles = 100
        for n in range(clock_cycles):
            next_pixel = Const(next(image_bytes_),unsigned(14))
            yield dut.in_pixel.eq(next_pixel)
            yield
        ## these assertions never fail so i don't think they're actually being checked
        ## but at least this produces a good simulation
        # for n in range(1):
        #     assert(yield dut.state == EXTERNAL)
        #     next_pixel = Const(next(image_bytes_),unsigned(14))
        #     yield dut.in_pixel.eq(next_pixel)
        #     assert (dut.state.eq(WRITE))
        #     assert (dut.P1.eq(next_pixel))
        #     #yield
        #     #assert (yield dut.state.eq(INCREMENT))
        #     yield
        #     assert (dut.state.eq(SHUFFLE))
        #     for n in range(dut.dwell_time):
        #         yield
        #         assert dut.state.eq(EXTERNAL)
        #         yield dut.in_pixel.eq(Const(next(image_bytes_),unsigned(14)))
        #         assert dut.state.eq(WRITE)
        #         yield
        #         assert dut.state.eq(CALCULATE)
        #         yield
        #         assert dut.state.eq(INCREMENT)
        #         yield
        #         assert dut.state.eq(SHUFFLE)
    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("scan_sim_average.vcd"):
        sim.run()

if __name__ == "__main__":

    # test - reconstitute the original image
    # split = np.array([round(mean(image_bytes[i:i+10])) for i in range(0,len(image_bytes),10)],dtype = np.uint8)
    # split = np.reshape(split,(height, width))
    # print(split)
    # imwrite("WD25-out.tif",split)
    test()
