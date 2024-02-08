import amaranth
from amaranth import *
from amaranth.sim import Simulator
from amaranth.lib.fifo import SyncFIFO, SyncFIFOBuffered

if "glasgow" in __name__: ## running as applet
    from ..gateware.stream_reader import StreamReader
    from ..gateware.stream_writer import StreamWriter
    from ..gateware.structs import *
#if __name__ == "__main__":
else:
    from structs import *
    from stream_reader import StreamReader
    from stream_writer import StreamWriter
    from test_streams import test_vector_points, _fifo_write_vector_point


class VectorModeController(Elaboratable):
    '''
    writer: See StreamWriter
        This module takes 16-bit wide dwell time or brightness data, and disassembles
        it into bytes to write to the in_fifo

    onebyte_writer: See StreamWriter
        This module takes 8-bit wide dwell time or brightness data, and passes it
        to the in_fifo

    reader: See StreamReader
        This module takes 8-bit values from the out_fifo and combines them
        into 16-bit dwell time values for raster pattern streaming
    
    xy_scan_gen_increment: Signal, in, 1
        Buffer for signals from other modules to assert xy_scan_gen.increment
    
    inner_xy_scan_gen_increment: Signal, internal, 1
        Buffer for xy_scan_gen.increment to be asserted from within this module

    adc_data_avgd: Signal, in, 16, scan_dwell_8
        Adc_data -> [Dwell Time Avgr] -> running_average -> [Byte Replacer] -> adc_data_avgd
    
    beam_controller_next: Signal, internal, 48, scan_point_16
        This signal is driven by the x and y values from the xy_scan_gen module,
        and the dwell time from the dwell register.
        This signal drives the next x, y, and dwell values for the beam controller.

    beam_controller_end_of_dwell: Signal, in, 1
        Driven by the beam controller module when the dwell counter has
        reached the current dwell time

    load_this_point: Signal, in, 1
        Asserted when it's time for the beam controller module to move to the next point
    write_this_point: Signal, in, 1
        Asserted when it's time for the current input at adc_data_avgd to be written into the in_fifo
    
    '''

    def __init__(self):
        #self.vector_fifo = SyncFIFOBuffered(width = 48, depth = 1)

        self.reader = StreamReader(scan_point_8)
        self.writer = StreamWriter(scan_dwell_8)

        self.adc_data_avgd = Signal(16)

        #self.vector_fifo_data = Signal(48)

        self.beam_controller_end_of_dwell = Signal()
        self.beam_controller_start_dwell = Signal()
        self.beam_controller_next = Signal(scan_point_16)

        self.load_next_point = Signal()
        self.write_this_point = Signal()


    def elaborate(self, platform):
        m = Module()
        m.submodules["VectorReader"] = self.reader
        m.submodules["VectorWriter"] = self.writer
        #m.submodules["VectorFIFO"] = self.vector_fifo


        # with m.If((self.reader.data_complete) & (self.vector_fifo.w_rdy)):
        #     m.d.comb += self.vector_fifo.w_en.eq(1)
        #     m.d.comb += self.vector_fifo.w_data.eq(self.vector_reader.vector_point_data_c)

        #with m.If((self.reader.data_complete)):
            #m.d.sync += self.vector_fifo_data.eq(self.vector_reader.vector_point_data_c)

        with m.If(self.write_this_point):
            m.d.comb += self.writer.strobe_in.eq(1)

        m.d.comb += self.writer.data_c.eq(self.adc_data_avgd)
        #with m.If(self.vector_fifo.r_rdy & self.beam_controller_end_of_dwell)::
        with m.If(self.load_next_point):
            #m.d.comb += self.vector_fifo.r_en.eq(1)
            #m.d.comb += self.beam_controller_next.eq(self.vector_fifo.r_data)
            m.d.comb += self.reader.data_used.eq(1)
            m.d.comb += self.beam_controller_next.eq(self.reader.data)
        
        

        return m


def test_vectorinput():
    dut = VectorInput()
    def bench():
        for n in test_vector_points:
            yield from write_point_in(n, dut.out_fifo)
    
    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("vectorin_sim.vcd"):
        sim.run()


def test_modecontroller():

    dut = ModeController()

    def bench():
        for n in test_vector_points:
            yield from _fifo_write_vector_point(n, dut.vector_input.out_fifo)
        yield

    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("vecmode_sim.vcd"):
        sim.run()

#test_vectorinput()

if __name__ == "__main__":
    print(test_vector_points)
    test_modecontroller()