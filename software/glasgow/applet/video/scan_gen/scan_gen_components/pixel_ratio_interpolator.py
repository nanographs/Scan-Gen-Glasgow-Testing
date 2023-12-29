import amaranth
from amaranth import *
from amaranth.sim import Simulator


class PixelRatioInterpolator(Elaboratable):
    '''
    Takes the output of a counter and converts it to a value for the DAC

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
        self.step_size = Signal(8)


    def elaborate(self, platform):
        m = Module()

        #m.d.comb += self.output.eq((self.input * self.output_width) // self.frame_size)
        #m.d.comb += self.product.eq(self.input * self.output_width)
        #m.d.comb += self.output.eq(self.product // self.frame_size)
        m.d.comb += self.output.eq(self.input*self.step_size)


        return m


    

class Division(Elaboratable):
    '''
    reference: https://projectf.io/posts/division-in-verilog/
    '''
    def __init__(self, width):
        self.divisor = Signal(width)
        self.dividend = Signal(width)
        self.remainder = Signal(width)
        self.quotient = Signal(width)
        self.width = width

    def elaborate(self, platform):
        m = Module()
        i = Signal(self.width.bit_length())

        with m.If(~((self.divisor) == 0)):
            with m.If(~(i == self.width)):
                with m.If(self.remainder < self.divisor):
                    m.d.sync += i.eq(i + 1)
                    m.d.sync += self.quotient.eq(self.quotient.shift_left(1))
                    m.d.sync += self.dividend.eq(self.dividend.shift_left(1))
                    m.d.sync += self.remainder.eq(Cat(self.dividend[self.width-1], self.remainder[0:(self.width-1)]))
                with m.Elif(self.remainder >= self.divisor):
                    m.d.sync += self.quotient[0].eq(1)
                    m.d.sync += self.remainder.eq(self.remainder - self.divisor)

        return m




if __name__ == "__main__":
    def test_division():
        dut = Division(4) 
        def bench():
            yield dut.divisor.eq(3)
            yield dut.dividend.eq(14)
            yield
            for n in range(6):
                yield
        
        sim = Simulator(dut)
        sim.add_clock(1e-6) # 1 MHz
        sim.add_sync_process(bench)
        with sim.write_vcd("div_sim.vcd"):
            sim.run()

    test_division()