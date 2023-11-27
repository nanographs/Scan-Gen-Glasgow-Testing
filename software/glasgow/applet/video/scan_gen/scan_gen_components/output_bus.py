import amaranth
from amaranth import *
from amaranth.sim import Simulator
from amaranth.lib import data, enum
from amaranth.lib.fifo import SyncFIFO

if "glasgow" in __name__: ## running as applet
    from ..scan_gen_components.addresses import *
    from ..scan_gen_components.byte_packing import TwoByteOutbox
    from ..scan_gen_components.output_handling import VideoSink
else:
    from addresses import *
    from byte_packing import TwoByteOutbox
    from output_handling import VideoSink


class OutputBus(Elaboratable):
    def __init__(self, out_fifo, is_simulation):
        self.video_sink = VideoSink()
        if is_simulation:
            self.out_fifo = SyncFIFO(width = 8, depth = 16, fwft = True)
        else:
            self.out_fifo = out_fifo
        #self.pixel_in = Signal(16)
        self.video_outbox = TwoByteOutbox(self.video_sink.pixel_out)
        self.strobe = Signal()
        
    def elaborate(self,platform):
        m = Module()

        m.submodules["VSink"] = self.video_sink
        m.submodules["VMailbox"] = self.video_outbox
        m.submodules["OUT_FIFO"] = self.out_fifo
        

        m.d.comb += self.out_fifo.w_data.eq(self.video_outbox.value)

        with m.FSM() as fsm:
            with m.State("Reading Data"):
                m.d.sync += self.out_fifo.w_en.eq(0)
                with m.If(self.strobe):
                    m.d.comb += self.video_sink.sinking.eq(1)
                    with m.If(self.video_sink.pipeline_offsetter.pipeline_full):
                        m.d.sync += self.video_outbox.parsing.eq(1)
                        m.d.sync += self.out_fifo.w_en.eq(1)
                        with m.If(self.video_outbox.flag):
                            m.next = "Writing Second Byte"
            with m.State("Writing Second Byte"):
                m.next = "Reading Data"

        return m