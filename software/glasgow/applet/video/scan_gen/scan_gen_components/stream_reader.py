import amaranth
from amaranth import *
from amaranth.sim import Simulator

if "glasgow" in __name__: ## running as applet
    from ..scan_gen_components.structs import *
else:
    from structs import *


class StreamReader(Elaboratable):
    def __init__(self, datatype):
        print(datatype)
        print(vars(datatype))
        self.dtype = datatype
        
        self.data_c = Signal(datatype)
        self.data = Signal(datatype)
        self.out_fifo_r_data = Signal(8)
        self.read_happened = Signal()
        self.data_used = Signal()
        self.data_complete = Signal()
        self.data_fresh_s = Signal()
        self.data_fresh = Signal()

    def elaborate(self, platform):
        m = Module()

        s = Signal()
        fields = self.dtype._fields
        field_strs = list(fields.keys())
        first_field = field_strs[0]
        last_field = field_strs[-1]
        second_to_last_field = field_strs[-2]

        # with m.If(self.data_complete):
        #     m.d.sync += self.data_fresh_s.eq(1)
        # with m.If(self.data_used):
        #     m.d.sync += self.data_fresh_s.eq(0)
        # with m.If(self.data_fresh_s):
        #     m.d.comb += self.data_fresh.eq(1)

        with m.FSM() as fsm:
            for n in range(len(fields)-1):
                field = list(fields)[n]
                next_field = list(fields)[n+1]
                with m.State(field):
                    with m.If(self.read_happened):
                        m.d.sync += self.data.__getitem__(field).eq(self.out_fifo_r_data)
                        m.next = next_field
            with m.State(last_field):
                with m.If(self.read_happened):
                    for n in range(len(fields)-1):
                        field = list(fields)[n]
                        m.d.comb += self.data_c.__getitem__(field).eq(self.data.__getitem__(field))
                    m.d.comb += self.data_c.__getitem__(last_field).eq(self.out_fifo_r_data)
                    m.d.comb += self.data_fresh.eq(1)
                    with m.If(self.data_used):
                        m.d.sync += self.data.eq(0)
                        m.next = first_field
                    with m.Else():
                        m.d.sync += self.data.eq(self.data_c)
                        m.next = "Hold"
                    
            with m.State("Hold"):
                m.d.comb += self.data_fresh.eq(1)
                m.d.comb += s.eq(1)
                m.d.comb += self.data_complete.eq(1)
                m.d.comb += self.data_c.eq(self.data)
                with m.If(self.data_used):
                    m.d.sync += self.data.eq(0)
                    m.next = first_field
                    


        return m

if __name__ == "__main__":
    def sim_reader():
        dut = StreamReader(vector_dwell)
        
        def bench():
            for n in range(1,5):
                yield dut.out_fifo_r_data.eq(n)
                yield dut.read_happened.eq(1)
                yield
            yield
            yield
            yield
            yield dut.data_used.eq(1)
            yield
            yield dut.data_used.eq(0)
            for n in range(5,8):
                yield dut.out_fifo_r_data.eq(n)
                yield dut.read_happened.eq(1)
                yield
            yield dut.out_fifo_r_data.eq(8)
            yield dut.read_happened.eq(1)
            yield dut.data_used.eq(1)
            yield


        sim = Simulator(dut)
        sim.add_clock(1e-6) # 1 MHz
        sim.add_sync_process(bench)
        with sim.write_vcd("stream_reader_sim.vcd"):
            sim.run()

    sim_reader()