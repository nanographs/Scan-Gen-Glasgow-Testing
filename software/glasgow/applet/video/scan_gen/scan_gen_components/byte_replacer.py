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
        do_frame_sync: Signal, in, 1
            If true, "0" should be written to the in_fifo after the last
            pixel of each frame
            Data values must be limited to:
                8 bit mode: 1-255
                16 bit mode: 1-16383
        do_line_sync:
            If true, "1" should be written to the in_fifo after the last
                pixel of each frame
                Data values must be limited to:
                    8 bit mode: 2-255
                    16 bit mode: 2-16383

    '''
    def __init__(self, dac_bits = 14):
        self.dac_bits = dac_bits
        self.point_data = Signal(vector_dwell)
        self.processed_point_data = Signal(vector_dwell)
        self.eight_bit_output = Signal()
        self.do_frame_sync = Signal()
        self.do_line_sync = Signal()
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

        with m.If(self.do_frame_sync):
            with m.If(self.point_data.as_value() == zero.as_value()):
                m.d.comb += self.processed_point_data.eq(1)
            with m.If(self.eight_bit_output):
                with m.If(self.most_significant_8_bits == 0):
                    m.d.comb += self.processed_point_data.D1.eq(1)

        with m.If(self.do_line_sync):
            with m.If((self.point_data.as_value() == one.as_value())|(self.point_data.as_value() == zero.as_value())):
                m.d.comb += self.processed_point_data.eq(2)
            with m.If(self.eight_bit_output):
                with m.If((self.most_significant_8_bits == 1)|(self.most_significant_8_bits == 0)):
                    m.d.comb += self.processed_point_data.D1.eq(2)

        s = Signal()
        m.d.sync += s.eq(1)

        return m


def test_bytereplacer():
    ## this test is weird because it relies on unnecessary synchronous logic
    ## fix later
    dut = ByteReplacer()
    def bench():
        def test_settings (frame_sync, line_sync, eight_bit):
            yield dut.do_frame_sync.eq(frame_sync)
            yield dut.do_line_sync.eq(line_sync)
            yield dut.eight_bit_output.eq(eight_bit)
        def test_results(data, processed_data):
            yield dut.point_data.eq(data)
            yield
            assert(yield dut.processed_point_data.as_value() == processed_data)

        ## Sixteen bit output, frame sync
        yield from test_settings(1, 0, 0)

        yield from test_results (0, 1)
        yield from test_results (1, 1)
        yield from test_results (256, 256)

        ## Eight bit output, frame sync
        yield from test_settings(1, 0, 1)

        yield from test_results (0, 1)
        yield from test_results (1, 1)
        yield from test_results (256, 4)
        yield from test_results (16383, 255)

            
    
    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("bytereplace_sim.vcd"):
        sim.run()

if __name__ == "__main__":
    test_bytereplacer()