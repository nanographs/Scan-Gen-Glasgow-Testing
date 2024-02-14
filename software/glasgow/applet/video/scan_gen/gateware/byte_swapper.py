import amaranth
from amaranth import *
from amaranth.sim import Simulator


if "glasgow" in __name__: ## running as applet
    from ..gateware.structs import *
else:
    from structs import *

replace_16 = [[Const(16383), Const(16382)]]
replace_8 = [[Const(255), Const(254)]]

class ByteSwapper(Elaboratable):
    def __init__(self, replace_8=replace_8, replace_16=replace_16, test_mode=None, msb = 0, lsb = 14):
        self.replace_8 = replace_8
        self.replace_16 = replace_16
        self.test_mode = test_mode
        self.point_data = Signal(scan_dwell_8)
        self.shifted_point_data = Signal(scan_dwell_8)
        self.processed_point_data = Signal(scan_dwell_8)
        self.eight_bit_output = Signal()
        self.msb = msb
        self.lsb = lsb
    def elaborate(self, platform):
        m = Module()

        s = Signal()
        m.d.sync += s.eq(1)
        q = Signal()

            # data = [
            #     data_lines.D1,
            #     data_lines.D2,
            #     data_lines.D3,
            #     data_lines.D4,
            #     data_lines.D5,
            #     data_lines.D6,
            #     data_lines.D7,
            #     data_lines.D8,
            #     data_lines.D9,
            #     data_lines.D10,
            #     data_lines.D11,
            #     data_lines.D12,
            #     data_lines.D13,
            #     data_lines.D14
            # ]

        # m.d.comb += self.shifted_point_data.as_value().bit_select(0,13)\
        #                 .eq(self.point_data.as_value().bit_select(self.lsb, self.msb))
        #m.d.comb += self.shifted_point_data.eq(self.point_data)


        m.d.comb += self.shifted_point_data.as_value()[7].eq(self.point_data.as_value()[13])
        m.d.comb += self.shifted_point_data.as_value()[6].eq(self.point_data.as_value()[12])       
        m.d.comb += self.shifted_point_data.as_value()[5].eq(self.point_data.as_value()[11])
        m.d.comb += self.shifted_point_data.as_value()[4].eq(self.point_data.as_value()[10])
        m.d.comb += self.shifted_point_data.as_value()[3].eq(self.point_data.as_value()[9])
        m.d.comb += self.shifted_point_data.as_value()[2].eq(self.point_data.as_value()[8])
        m.d.comb += self.shifted_point_data.as_value()[1].eq(self.point_data.as_value()[7])
        m.d.comb += self.shifted_point_data.as_value()[0].eq(self.point_data.as_value()[6])



        for pair in replace_16:
            replaced = Signal(scan_dwell_8)
            replaced_with = Signal(scan_dwell_8)
            m.d.comb += replaced.eq(pair[0])
            m.d.comb += replaced_with.eq(pair[1])
            
            with m.If(self.shifted_point_data.as_value() == replaced.as_value()):
                m.d.comb += self.processed_point_data.as_value().eq(replaced_with.as_value())
                m.d.comb += q.eq(1)
            with m.Else():
                m.d.comb += self.processed_point_data.eq(self.shifted_point_data)

        with m.If(self.eight_bit_output):
            for pair in replace_8:
                replaced_onebyte = Signal(scan_dwell_8_onebyte)
                replaced_with_onebyte = Signal(scan_dwell_8_onebyte)
                m.d.comb += replaced_onebyte.eq(pair[0])
                m.d.comb += replaced_with_onebyte.eq(pair[1])

                with m.If(self.shifted_point_data.D1 == replaced_onebyte.D1):
                    m.d.comb += self.processed_point_data.D1.eq(replaced_with_onebyte.D1)
                    m.d.comb += q.eq(1)
                with m.Else():
                    m.d.comb += self.processed_point_data.eq(self.shifted_point_data)


        return m



if __name__ == "__main__":
    def test_byteswapper():
        dut = ByteSwapper(replace)
        def bench():
            yield dut.point_data.eq(16383)
            yield
            yield dut.point_data.eq(12289)
            yield
            yield
    
        sim = Simulator(dut)
        sim.add_clock(1e-6) # 1 MHz
        sim.add_sync_process(bench)
        with sim.write_vcd("byteswap_sim.vcd"):
            sim.run()
    test_byteswapper()