import amaranth
from amaranth import *
from amaranth.sim import Simulator


if "glasgow" in __name__: ## running as applet
    from ..scan_gen_components.addresses import *
else:
    from addresses import *

class ByteReplacer(Elaboratable):
    def __init__(self):
        self.point_data = Signal(vector_dwell)
        self.processed_point_data = Signal(vector_dwell)
        self.eight_bit_output = Signal()
        self.do_frame_sync = Signal()
        self.do_line_sync = Signal()
    def elaborate(self, platform):
        m = Module()

        zero = Signal(vector_dwell)
        m.d.comb += zero.D1.eq(0)
        m.d.comb += zero.D2.eq(0)

        one = Signal(vector_dwell)
        m.d.comb += one.D1.eq(1)
        m.d.comb += one.D2.eq(0)

        with m.If(self.eight_bit_output):
            m.d.comb += self.processed_point_data.as_value().eq(Cat(self.point_data.D1, zero.D1))
        with m.Else():
            m.d.comb += self.processed_point_data.eq(self.point_data)

        
        test = Signal()
        

        with m.If(self.do_frame_sync):
            with m.If(self.point_data.as_value() == zero.as_value()):
                m.d.comb += self.processed_point_data.eq(1)
            with m.If(self.eight_bit_output):
                with m.If(self.point_data.D1 == 0):
                    m.d.comb += self.processed_point_data.D1.eq(1)
                    m.d.comb += test.eq(1)

        with m.If(self.do_line_sync):
            with m.If((self.point_data.as_value() == one.as_value())|(self.point_data.as_value() == zero.as_value())):
                m.d.comb += self.processed_point_data.eq(2)
            with m.If(self.eight_bit_output):
                with m.If((self.point_data.D1 == 1)|(self.point_data.D1 == 0)):
                    m.d.comb += self.processed_point_data.D1.eq(2)
                    m.d.comb += test.eq(1)
    


        s = Signal()
        m.d.sync += s.eq(1)
        return m


def test_bytereplacer():
    dut = ByteReplacer()
    def bench():
        yield dut.do_frame_sync.eq(1)
        yield dut.do_line_sync.eq(1)
        yield dut.eight_bit_output.eq(1)
        for n in range(0,513):
            yield dut.point_data.eq(n)
            yield
            
    
    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("bytereplace_sim.vcd"):
        sim.run()

if __name__ == "__main__":
    test_bytereplacer()