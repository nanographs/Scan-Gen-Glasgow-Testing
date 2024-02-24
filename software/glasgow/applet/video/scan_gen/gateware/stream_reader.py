import amaranth
from amaranth import *
from amaranth.sim import Simulator

if "glasgow" in __name__: ## running as applet
    from ..gateware.structs import *
else:
    from structs import *


'''
    Inputs:
        datatype: An Amaranth data struct that is divided into bytes
    out_fifo_r_data: Signal, in, 8
        This signal is combinatorially driven by the top level out_fifo.r_data
    
    data: Signal, internal, {datatype}
        Each cycle that the out_fifo is read from, a byte is synchronously written 
        to vector_point_data. 
    data_c: Signal, out, 48
        This is the signal that the next values for the beam controller are read from.
        This signal is combinatorially assigned to the value of data and the latest byte from the out_fifo. 
        This is so that the data can be used immediately. If the data can't be used immediately, the last
        byte is synchronously added to data and the state machine moves to 
        the HOLD state.

    data_complete: Signal, out, 1:
        Asserted when all bytes of a data have been assembled. When this is true,
        the value of data_c is valid to assign as the next beam controller values
    read_happened: Signal, in, 1:
        Asserted when the out_fifo is ready to be read from. This signal is driven by 
        mode_ctrl.read_happened, which is driven by the top level read_strobe
    data_point_used: Signal, in, 1:
        Asserted when the data held in data is used. On the cycle after this is
        asserted, the module will return to state X1 and be ready to read a new point in
    data_fresh: Signal, in, 1:
        Asserted when a data point is both complete and unused
        actually, I'm not sure what this does

    State Machine:
        F1 -> F2 ... -> FN -> Hold
        ↑---------------↲-------↲
    
    For struct scan_data_8:
        D1 -> D2 -> Hold
        ↑-----↲-------↲

    Inspiration taken from https://github.com/maia-sdr/maia-sdr/blob/main/maia-hdl/maia_hdl/packer.py
    
    '''
class StreamReader(Elaboratable):
    
    def __init__(self, datatype):
        self.dtype = datatype
        
        self.out_fifo_r_data = Signal(8)
        self.data_c = Signal(datatype)
        self.data = Signal(datatype)
        
        self.data_complete = Signal()
        self.read_happened = Signal()
        self.data_used = Signal()
        self.data_fresh = Signal()

    def elaborate(self, platform):
        m = Module()

        s = Signal()
        fields = list(self.dtype._fields)
        field_strs = list(fields.keys())
        first_field = field_strs[0]
        last_field = field_strs[-1]

        # from amaranth.lib import data
        # vector_point_layout = data.StructLayout({
        #     "x": unsigned(16),
        #     "y": unsigned(16),
        #     "dwell": unsigned(16),
        # })
        # vector_point = Signal(vector_point_layout)
        # vector_point.y # equivalent to vector_point.as_value()[16:32]


        with m.FSM() as fsm:
            for n, field in enumerate(fields[:-1]):
                next_field = fields[n+1]
                with m.State(field):
                    with m.If(self.read_happened):
                        m.d.sync += self.data[field].eq(self.out_fifo_r_data)
                        m.next = next_field

            with m.State(last_field):
                with m.If(self.read_happened):
                    for field in fields[:-1]:
                        m.d.comb += self.data_c[field].eq(self.data[field])
                    m.d.comb += self.data_c[last_field].eq(self.out_fifo_r_data)
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