import amaranth
from amaranth import *
from amaranth.sim import Simulator

### turn a tiff into a stream of bits
from tifffile import imread, imwrite, imshow, TiffFile
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

## test - reconstitute the original image
# split = np.array([round(mean(image_bytes[i:i+10])) for i in range(0,len(image_bytes),10)],dtype = np.uint8)
# split = np.reshape(split,(height, width))
# print(split)
# imwrite("WD25-out.tif",split)


class Pixel_Average(Elaboratable):
    def __init__(self):
        self.in_pixel = Signal(14)
        self.s = Signal()
    def elaborate(self,platform):
        m = Module()
        m.d.sync += self.s.eq(1)
        m.d.comb += self.in_pixel.eq(0)
        return m

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
    test()
