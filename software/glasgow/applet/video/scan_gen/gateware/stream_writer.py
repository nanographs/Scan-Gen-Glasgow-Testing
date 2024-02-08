import amaranth
from amaranth import *
from amaranth.sim import Simulator

if "glasgow" in __name__: ## running as applet
    from ..gateware.structs import *
else:
    from structs import *


class StreamWriter(Elaboratable):
    '''
    Inputs:
        datatype: An Amaranth data struct that is divided into bytes

    in_fifo_w_data: Signal, out, 8
        This signal combinatorially drives the top level in_fifo.w_data

    data_c: Signal, in, {datatype}:
        This signal is combinatorially driven by the processed ADC input data, 
        or if testing in loopback is set to an internal value (x position or dwell)
    data: Signal, internal, 16
        When strobe_inis asserted, this signal is synchronously set equal to data_c

    write_happened: Signal, in, {datatype}:
        Asserted when the in_fifo is ready to be written to. This signal is driven by 
        the top level write_strobe through mode_ctrl.write_happened
    data_valid: Signal, out, 1
        Asserted when the data at in_fifo_w_data is valid. 
        If strobe_out is high, data will be written to the in_fifo
    data_complete: Signal, out, 1
        Asserted on the last byte of data
    strobe_in: Signal, out, 1
        Asserted when valid data is present at data_c

    State Machine:
            ↓------------------------------↑
        Waiting -> F1 -> F2 ... FN - 1 -> FN
            ↳------------↑                       

    For struct scan_data_8:
            ↓------------↑
        Waiting -> D1 -> D2 
            ↳------------↑    

    '''
    def __init__(self, datatype):
        self.dtype = datatype

        self.in_fifo_w_data = Signal(8)
        self.data_c = Signal(datatype)
        self.data = Signal(datatype)
        
        self.write_happened = Signal()
        self.data_valid = Signal()
        self.data_complete = Signal()
        self.strobe_in = Signal()

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