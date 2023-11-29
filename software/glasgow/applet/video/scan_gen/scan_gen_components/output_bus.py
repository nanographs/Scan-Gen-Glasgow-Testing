import amaranth
from amaranth import *
from amaranth.sim import Simulator
from amaranth.lib import data, enum
from amaranth.lib.fifo import SyncFIFO, SyncFIFOBuffered

if "glasgow" in __name__: ## running as applet
    from ..scan_gen_components.addresses import *
    from ..scan_gen_components.byte_packing import TwoByteOutbox
    from ..scan_gen_components.output_handling import VideoSink
else:
    from addresses import *
    from byte_packing import TwoByteOutbox
    from output_handling import VideoSink, test_pixel_stream


class OutputBus(Elaboratable):
    def __init__(self, in_fifo = SyncFIFOBuffered(width = 8, depth = 16)):
        self.video_sink = VideoSink()
        self.in_fifo = in_fifo
        #self.pixel_in = Signal(16)
        self.video_outbox = TwoByteOutbox()
        self.strobe = Signal()
        
    def elaborate(self,platform):
        m = Module()

        m.submodules["VSink"] = self.video_sink
        m.submodules["VMailbox"] = self.video_outbox
        m.submodules["in_fifo"] = self.in_fifo
        
        m.d.comb += self.video_outbox.input.eq(self.video_sink.pixel_out)
        m.d.comb += self.in_fifo.w_data.eq(self.video_outbox.value)

        with m.FSM() as fsm:
            with m.State("Reading Data"):
                with m.If(self.in_fifo.w_rdy):
                    with m.If(self.strobe):
                        m.d.comb += self.video_sink.sinking.eq(1)
                        with m.If(self.video_sink.pipeline_offsetter.pipeline_full):
                            m.d.comb += self.video_outbox.parsing.eq(1)
                            m.d.comb += self.in_fifo.w_en.eq(1)
                            m.next = "Writing Second Byte"
            with m.State("Writing Second Byte"):
                with m.If(self.in_fifo.w_rdy):
                    m.d.comb += self.in_fifo.w_en.eq(1)
                    m.next = "Reading Data"

        return m


def sim_outputbus():
    dut = OutputBus()
    def bench():
        yield dut.video_sink.dwelling.eq(1)
        for n in range(0, len(test_pixel_stream)):
            next_pixel = test_pixel_stream[n]
            print("pixel", n, "=", next_pixel)
            yield dut.video_sink.pixel_in.eq(next_pixel)
            yield dut.strobe.eq(1)
            yield
            yield
    
    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("outputbus_sim.vcd"):
        sim.run()

if __name__ == "__main__":
    sim_outputbus()