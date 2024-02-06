import amaranth
from amaranth import *
from amaranth.sim import Simulator
from amaranth.lib.fifo import SyncFIFO, SyncFIFOBuffered

if "glasgow" in __name__: ## running as applet
    from ..scan_gen_components.stream_reader import StreamReader
    from ..scan_gen_components.stream_writer import StreamWriter
    from ..scan_gen_components.structs import *
#if __name__ == "__main__":
else:
    from structs import *
    from stream_reader import StreamReader
    from stream_writer import StreamWriter
    from test_streams import test_vector_points, _fifo_write_vector_point


class VectorModeController(Elaboratable):
    '''
    vector_fifo: FIFO, 48 bits wide, 12 values deep
        This FIFO holds full vector points

    vector_reader: See VectorReader
        This module handles reading data from the out_fifo and 
        assembling into 48-bit vector point format
    vector_writer: See VectorWriter
        This module takes 32-bit wide vector position data and
        16-bit wide dwell time or brightness data, and disassembles
        it into bytes to write to the in_fifo
    
    vector_point_data: Signal, internal, 48
        This signal is driven by the value read from the vector FIFO,
        and drives the next x, y, and dwell values for the beam controller.
        The first 32 bits of this signal also drive the vector_position_c
        value of vector_output. In this way, the x and y position of each 
        point are read into the output stream

    vector_point_output: Signal, in, 16
        This signal is driven by the ADC data sampled at each point.
        In test_mode = data_loopback, the dwell time is returned directly.

    beam_controller_end_of_dwell: Signal, in, 1
        Driven by the beam controller module when the dwell counter has
        reached the current dwell time
    beam_controller_start_dwell: Signal, in, 1
        Driven by the beam controller module when the dwell counter is 0

    beam_controller_next_x_position: Signal, out, 16:
        Drives beam_controller.next_x_position
    beam_controller_next_y_position: Signal, out, 16:
        Drives beam_controller.next_y_position
    beam_controller_next_dwell: Signal, out, 16:
        Drives beam_controller.next_dwell

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

        self.reader_data_complete = Signal()
        self.reader_read_happened = Signal()
        self.reader_data_fresh = Signal()
        self.writer_data_complete = Signal()
        self.writer_data_valid = Signal()
        self.writer_write_happened = Signal()
        self.write_this_point = Signal()

        self.load_next_point = Signal()
        self.in_fifo_w_data = Signal(8)
        self.out_fifo_r_data = Signal(8)

    def elaborate(self, platform):
        m = Module()
        m.submodules["VectorReader"] = self.reader
        m.submodules["VectorWriter"] = self.writer
        #m.submodules["VectorFIFO"] = self.vector_fifo

        # m.d.comb += self.reader_data_complete.eq(self.reader.data_complete)
        # m.d.comb += self.reader_data_fresh.eq(self.reader.data_fresh)

        # m.d.comb += self.reader.read_happened.eq(self.reader_read_happened)

        # m.d.comb += self.writer_data_complete.eq(self.writer.data_complete)
        # m.d.comb += self.writer_data_valid.eq(self.writer.data_valid)

        # m.d.comb += self.writer.write_happened.eq(self.writer_write_happened)
        # m.d.comb += self.in_fifo_w_data.eq(self.writer.in_fifo_w_data)
        # m.d.comb += self.reader.out_fifo_r_data.eq(self.out_fifo_r_data)
        #m.d.comb += self.vector_reader.strobe_out.eq(self.vector_fifo.w_rdy)

        # with m.If((self.vector_reader.data_complete) & (self.vector_fifo.w_rdy)):
        #     m.d.comb += self.vector_fifo.w_en.eq(1)
        #     m.d.comb += self.vector_fifo.w_data.eq(self.vector_reader.vector_point_data_c)

        #with m.If((self.vector_reader.data_complete)):
            #m.d.sync += self.vector_fifo_data.eq(self.vector_reader.vector_point_data_c)

        with m.If(self.write_this_point):
            m.d.comb += self.writer.strobe_in.eq(1)

        m.d.comb += self.writer.data_c.eq(self.adc_data_avgd)
        #with m.If(self.vector_fifo.r_rdy & self.beam_controller_end_of_dwell)::
        with m.If(self.load_next_point):
            #m.d.comb += self.vector_fifo.r_en.eq(1)
            #m.d.comb += self.vector_point_data.eq(self.vector_fifo.r_data)
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