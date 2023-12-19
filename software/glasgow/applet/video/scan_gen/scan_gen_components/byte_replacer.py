import amaranth
from amaranth import *
from amaranth.sim import Simulator


if "glasgow" in __name__: ## running as applet
    from ..scan_gen_components.addresses import *
else:
    from addresses import *

class ByteReplacer(Elaboratable):
    '''
        point_data: Signal, in, 16
            A raw signal to be transmitted by the in_fifo
            Driven by mode_ctrl.adc_data
        processed_point_data: Signal, out, 16
            A modified, filtered version of that signal

        eight_bit_output: Signal, in, 1
            True: 8 bits per data point are streamed to the in_fifo
            False: 16 bits per data point are streamed to the in_fifo
        replace_0_to_1: Signal, in, 1
            Data values must be limited to:
                8 bit mode: 1-255
                16 bit mode: 1-16383
        replace_0_to_2: Signal, in, 1
            Data values must be limited to:
                8 bit mode: 2-255
                16 bit mode: 2-16383

        replace_FF_to_FE: Signal, in , 1
            If true, "255" should be replaced with "254"
            We don't need to do anything to 16-bit values right now,
            because we are using 14 bit DACs and ADCs, so our
            range is already limited.
    '''
    def __init__(self, dac_bits = 14):
        self.dac_bits = dac_bits
        self.point_data = Signal(vector_dwell)
        self.processed_point_data = Signal(vector_dwell)
        self.eight_bit_output = Signal()
        self.replace_0_to_1 = Signal()
        self.replace_0_to_2 = Signal()
        self.replace_FF_to_FE = Signal()
        self.most_significant_8_bits = Signal(8)
    def elaborate(self, platform):
        m = Module()

        ## TODO: test with actual ADC readout
        #m.d.comb += self.most_significant_8_bits.eq(self.point_data.as_value()[(self.dac_bits - 8):self.dac_bits])
        m.d.comb += self.most_significant_8_bits.eq(self.point_data.D1)

        with m.If(self.eight_bit_output):
            m.d.comb += self.processed_point_data.D1.eq(self.most_significant_8_bits)
            m.d.comb += self.processed_point_data.D2.eq(0)
        with m.Else():
            m.d.comb += self.processed_point_data.eq(self.point_data)

        zero = Signal(vector_dwell)
        m.d.comb += zero.D1.eq(0)
        m.d.comb += zero.D2.eq(0)

        one = Signal(vector_dwell)
        m.d.comb += one.D1.eq(1)
        m.d.comb += one.D2.eq(0)

        with m.If(self.replace_0_to_1):
            with m.If(self.point_data.as_value() == zero.as_value()):
                m.d.comb += self.processed_point_data.eq(1)
            with m.If(self.eight_bit_output):
                with m.If(self.most_significant_8_bits == 0):
                    m.d.comb += self.processed_point_data.D1.eq(1)

        with m.If(self.replace_0_to_2):
            with m.If((self.point_data.as_value() == one.as_value())|(self.point_data.as_value() == zero.as_value())):
                m.d.comb += self.processed_point_data.eq(2)
            with m.If(self.eight_bit_output):
                with m.If((self.most_significant_8_bits == 1)|(self.most_significant_8_bits == 0)):
                    m.d.comb += self.processed_point_data.D1.eq(2)

        with m.If(self.replace_FF_to_FE):
            with m.If(self.eight_bit_output):
                with m.If((self.most_significant_8_bits == 255)):
                    m.d.comb += self.processed_point_data.D1.eq(254)


        s = Signal()
        m.d.sync += s.eq(1)

        return m


def test_bytereplacer():
    ## this test is weird because it relies on unnecessary synchronous logic
    ## fix later
    dut = ByteReplacer()
    def bench():
        def test_settings (replace_0_to_1, replace_0_to_2, eight_bit, replace_FF_to_FE):
            yield dut.replace_0_to_1.eq(replace_0_to_1)
            yield dut.replace_0_to_2.eq(replace_0_to_2)
            yield dut.eight_bit_output.eq(eight_bit)
            yield dut.replace_FF_to_FE.eq(replace_FF_to_FE)
        def test_results(data, processed_data):
            yield dut.point_data.eq(data)
            yield
            assert(yield dut.processed_point_data.as_value() == processed_data)

        ## Sixteen bit output, frame sync
        yield from test_settings(1, 0, 0,0)

        yield from test_results (0, 1)
        yield from test_results (1, 1)
        yield from test_results (256, 256)

        ## Eight bit output, frame sync
        yield from test_settings(1, 0, 1,0)

        yield from test_results (0, 1)
        yield from test_results (1, 1)
        yield from test_results (256, 1)
        yield from test_results (16383, 255)

        yield from test_settings(0, 0, 1, 1)
        yield from test_results(255, 254)

            
    
    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("bytereplace_sim.vcd"):
        sim.run()

if __name__ == "__main__":
    test_bytereplacer()