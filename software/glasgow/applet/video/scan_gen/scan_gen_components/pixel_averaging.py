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


class Pixel_Average(Elaboratable):
    def __init__(self):
        self.running_average = Signal(15)
        self.in_pixel = Signal(14)
        self.current_pixel = Signal(14)
        self.dwell_time = 10
        self.ovf = Signal()
    def elaborate(self,platform):
        m = Module()
        m.submodules.dwell_ctr = dwell_ctr = RampGenerator(self.dwell_time)
        m.d.comb += [self.in_pixel.eq(0), dwell_ctr.en.eq(1)]
        m.d.sync += [
        self.current_pixel.eq(self.in_pixel)]
        with m.If(dwell_ctr.ovf):
            m.d.comb += self.running_average.eq(0)
        with m.Else():
            m.d.comb += self.running_average.eq((self.running_average + self.current_pixel)//2)
        return m
    def ports(self):
        return[self.submodules.dwell_ctr, self.ovf, self.running_average, 
        self.in_pixel, self.current_pixel]

def test():
    
    dut = Pixel_Average()
    def bench():
        for _ in range(200):
            yield dut.in_pixel.eq(Const(next(image_bytes_),unsigned(14)))
            yield
    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("scan_sim_average.vcd"):
        sim.run()

if __name__ == "__main__":

    ## test - reconstitute the original image
    # split = np.array([round(mean(image_bytes[i:i+10])) for i in range(0,len(image_bytes),10)],dtype = np.uint8)
    # split = np.reshape(split,(height, width))
    # print(split)
    # imwrite("WD25-out.tif",split)
    test()
