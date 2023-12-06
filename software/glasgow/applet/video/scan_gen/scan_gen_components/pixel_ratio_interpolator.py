import amaranth
from amaranth import *
from amaranth.sim import Simulator


class PixelRatioInterpolator(Elaboratable):
    '''
    Takes the output of a counter and convertes it to a value for the DAC

    Parameters:
    - output_width: Full scale DAC Value
    - frame_size: Signal In
        - width of the frame to scan

    Attributes:
    - input: Signal In
        - The value to convert to DAC value
    - output: Signal Out
        - The value for the DAC
    '''

    
    def __init__(self, output_width = 16383):
        self.output_width = output_width ## Full scale DAC value
        self.frame_size = Signal(16) ## Width of the frame to scan

        self.input = Signal(16) ## Current pixel number
        self.output = Signal(16) ## Current pixel number converted to DAC value

        self.product = Signal(32)


    def elaborate(self, platform):
        m = Module()

        m.d.comb += self.output.eq((self.input * self.output_width) // self.frame_size)


        return m




