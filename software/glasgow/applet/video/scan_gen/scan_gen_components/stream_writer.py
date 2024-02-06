import amaranth
from amaranth import *
from amaranth.sim import Simulator

if "glasgow" in __name__: ## running as applet
    from ..scan_gen_components.structs import *
else:
    from structs import *


class StreamWriter(Elaboratable):
    def __init__(self, datatype):
        self.dtype = datatype
        
        self.data_c = Signal(datatype)
        self.data = Signal(datatype)
        self.in_fifo_w_data = Signal(8)
        self.write_happened = Signal()
        self.data_valid = Signal()
        self.data_complete = Signal()
        self.strobe_in = Signal()
        self.data_fresh = Signal()

    def elaborate(self, platform):
        m = Module()

        fields = self.dtype._fields
        field_strs = list(fields.keys())
        first_field = field_strs[0]
        last_field = field_strs[-1]

        if len(field_strs) > 1:
            second_field = field_strs[1]
        else:
            second_field = "Waiting" # only writing a single byte, 
                                    # so stay in a single state
        

        w = Signal()
        f = Signal(3)
        lf = Signal()

        with m.FSM() as fsm:
            with m.State("Waiting"):
                m.d.comb += w.eq(1)
                with m.If(self.strobe_in):
                    m.d.comb += self.data_valid.eq(1)
                    m.d.comb += self.in_fifo_w_data.eq(self.data_c.__getitem__(first_field))
                    m.d.sync += self.data.eq(self.data_c)
                    if second_field == "Waiting": #if only writing one byte
                        m.d.comb += self.data_complete.eq(1)
                    with m.If(self.write_happened):
                        m.next = second_field
                    with m.Else():
                        m.next = first_field
            for n in range(len(fields)-1):
                field = list(fields)[n]
                next_field = list(fields)[n+1]
                with m.State(field):
                    m.d.comb += f.eq(n+1)
                    m.d.comb += self.data_valid.eq(1)
                    m.d.comb += self.in_fifo_w_data.eq(self.data_c.__getitem__(field))
                    with m.If(self.write_happened):
                        m.next = next_field
            with m.State(last_field):
                m.d.comb += self.data_complete.eq(1)
                m.d.comb += lf.eq(1)
                m.d.comb += self.data_valid.eq(1)
                m.d.comb += self.in_fifo_w_data.eq(self.data_c.__getitem__(last_field))
                with m.If(self.write_happened):
                    m.next = "Waiting"


        return m

if __name__ == "__main__":
    def sim_reader():
        dut = StreamWriter(scan_dwell_8)
        
        def bench():
            yield dut.data_c.eq(8)
            yield dut.strobe_in.eq(1)
            yield
            yield dut.strobe_in.eq(0)
            yield dut.write_happened.eq(1)
            yield
            yield dut.write_happened.eq(0)
            yield
            


        sim = Simulator(dut)
        sim.add_clock(1e-6) # 1 MHz
        sim.add_sync_process(bench)
        with sim.write_vcd("stream_writer_sim.vcd"):
            sim.run()

    sim_reader()