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
        self.i = Signal(width.bit_length())
        self.done = Signal()
        self.width = width

    def elaborate(self, platform):
        m = Module()

        

        with m.If(~((self.divisor) == 0)):
            with m.If(~(self.i == self.width)):
                with m.If(self.remainder < self.divisor):
                    m.d.sync += self.i.eq(self.i + 1)
                    m.d.sync += self.quotient.eq(self.quotient.shift_left(1))
                    m.d.sync += self.dividend.eq(self.dividend.shift_left(1))
                    m.d.sync += self.remainder.eq(Cat(self.dividend[self.width-1], self.remainder[0:(self.width-1)])) 
            with m.If(self.remainder >= self.divisor):
                m.d.sync += self.quotient[0].eq(1)
                m.d.sync += self.remainder.eq(self.remainder - self.divisor)
            with m.If((self.i == self.width)):
                with m.If(self.remainder < self.divisor):
                    m.d.comb += self.done.eq(self.i == self.width)

        return m




if __name__ == "__main__":
    def test_division(dividend:int, divisor:int):
        width = dividend.bit_length()
        dut = Division(width) 
        def bench():
            yield dut.divisor.eq(divisor)
            yield dut.dividend.eq(dividend)
            i = 0
            while not (yield dut.done):
                yield
                i += 1
            assert (yield dut.quotient == dividend//divisor)
            assert (yield dut.remainder == dividend%divisor)
            print(f'Quotient: {dividend}//{divisor} = {dividend//divisor}')
            print(f'Remainder {dividend}%{divisor} = {dividend%divisor}')
            print(f'{i} cycles')
        
        sim = Simulator(dut)
        sim.add_clock(1e-6) # 1 MHz
        sim.add_sync_process(bench)
        with sim.write_vcd("div_sim.vcd"):
            sim.run()

    test_division(14, 3)
    test_division(500, 21)
    test_division(16384,500)
    test_division(16384,1024)
