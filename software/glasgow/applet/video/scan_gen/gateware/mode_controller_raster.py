import amaranth
from amaranth import *
from amaranth.sim import Simulator
from amaranth.lib.fifo import SyncFIFO, SyncFIFOBuffered


if "glasgow" in __name__: ## running as applet
    from ..scan_gen_components.byte_replacer import ByteReplacer
    from ..scan_gen_components.stream_reader import StreamReader
    from ..scan_gen_components.stream_writer import StreamWriter
    from ..scan_gen_components.xy_scan_gen import XY_Scan_Gen
    from ..scan_gen_components.structs import *
else:
#if __name__ == "__main__":
    from byte_replacer import ByteReplacer
    from stream_reader import StreamReader
    from stream_writer import StreamWriter
    from xy_scan_gen import XY_Scan_Gen
    from structs import *
    from test_streams import test_vector_points, _fifo_write_vector_point

class RasterModeController(Elaboratable):
    '''
    raster_writer: See RasterWriter
        This module takes 32-bit wide raster position data (not used)
        and 16-bit wide dwell time or brightness data, and disassembles
        it into bytes to write to the in_fifo

    raster_reader: See RasterReader
        This module takes 8-bit values from the out_fifo and combines them
        into 16-bit dwell time values for raster pattern streaming
    
    raster_point_data: Signal, internal, 48
        This signal is driven by the x and y values from the xy_scan_gen module,
        and the dwell time from the dwell register (currently hardcoded).
        This signal drives the next x, y, and dwell values for the beam controller.
        The first 32 bits of this signal also drive the raster_position_c
        value of raster_output. In this way, the x and y position of each 
        point can be read into the output stream (but are not)

    raster_point_output: Signal, in, 16
        This signal is driven by the ADC data sampled at each point.
        In test_mode = data_loopback, beam controller x position is returned.

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

    do_frame_sync: Signal, in, 1
        If true, RasterWriter will write 0 to the in_fifo
    '''
    def __init__(self):
        self.writer = StreamWriter(scan_dwell_8)
        self.onebyte_writer = StreamWriter(scan_dwell_8_onebyte)
        self.reader = StreamReader(scan_dwell_8)
        
        self.xy_scan_gen = XY_Scan_Gen()

        self.adc_data_avgd = Signal(scan_dwell_8)

        self.beam_controller_end_of_dwell = Signal()
        self.beam_controller_start_dwell = Signal()
        self.beam_controller_next = Signal(scan_point_16)

        self.reader_data_complete = Signal()
        self.reader_data_fresh = Signal()
        self.reader_read_happened = Signal()
        self.writer_data_complete = Signal()
        self.writer_data_valid = Signal()
        self.writer_write_happened = Signal()
        self.write_this_point = Signal()

        #self.raster_fifo = SyncFIFOBuffered(width = 16, depth = 256)
        self.xy_scan_gen_increment = Signal()
        self.load_next_point = Signal()
        
        self.in_fifo_w_data = Signal(8)
        self.out_fifo_r_data = Signal(8)

        self.eight_bit_output = Signal()

    def elaborate(self, platform):
        m = Module()
        m.submodules["Raster1byteWriter"] = self.onebyte_writer
        m.submodules["RasterWriter"] = self.writer
        m.submodules["RasterReader"] = self.reader
        #m.submodules["RasterFIFO"] = self.raster_fifo
        m.submodules["XYScanGen"] = self.xy_scan_gen


        # m.d.comb += self.reader_data_complete.eq(self.reader.data_complete)
        # m.d.comb += self.reader_data_fresh.eq(self.reader.data_fresh)
        # m.d.comb += self.reader.read_happened.eq(self.reader_read_happened)
        # m.d.comb += self.writer_data_complete.eq(self.writer.data_complete)
        # m.d.comb += self.writer_data_valid.eq(self.writer.data_valid)
        # m.d.comb += self.writer.write_happened.eq(self.writer_write_happened)
        # m.d.comb += self.in_fifo_w_data.eq(self.writer.in_fifo_w_data)
        # m.d.comb += self.reader.out_fifo_r_data.eq(self.out_fifo_r_data)

        # with m.If((self.raster_reader.data_complete) & (self.raster_fifo.w_rdy)):
        #     m.d.comb += self.raster_reader.data_point_used.eq(1)
        #     m.d.comb += self.raster_fifo.w_en.eq(1)
        #     m.d.comb += self.raster_fifo.w_data.eq(self.raster_reader.data_c)

        inner_xy_scan_gen_increment = Signal()
        with m.If((inner_xy_scan_gen_increment) | (self.xy_scan_gen_increment)):
            m.d.comb += self.xy_scan_gen.increment.eq(1)

        with m.If(self.eight_bit_output):
            m.d.comb += self.onebyte_writer.data_c.eq(self.adc_data_avgd)
        with m.Else():
            m.d.comb += self.writer.data_c.eq(self.adc_data_avgd)

        with m.If(self.write_this_point):
            with m.If(self.eight_bit_output):
                m.d.comb += self.onebyte_writer.strobe_in.eq(1)
            with m.Else():
                m.d.comb += self.writer.strobe_in.eq(1)

        with m.If(self.load_next_point):
            m.d.comb += inner_xy_scan_gen_increment.eq(1)
            m.d.comb += self.beam_controller_next.X.eq(self.xy_scan_gen.current_x)
            m.d.comb += self.beam_controller_next.Y.eq(self.xy_scan_gen.current_x)
            m.d.comb += self.reader.data_used.eq(1)
            m.d.comb += self.beam_controller_next.D.eq(self.reader.data_c)
            # with m.If(self.raster_fifo.r_rdy):
            #     m.d.comb += self.beam_controller_next_dwell.eq(self.raster_fifo.r_data)
            #     m.d.comb += self.raster_fifo.r_en.eq(1)


        
        

        return m


def test_rasmodecontroller():

    dut = RasterModeController()

    def bench():
        yield dut.xy_scan_gen.x_full_frame_resolution.eq(8)
        yield dut.xy_scan_gen.y_full_frame_resolution.eq(8)
        yield
        for n in range(64):
            yield dut.beam_controller_end_of_dwell.eq(1)
            yield

    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("rasmode_sim.vcd"):
        sim.run()


if __name__ == "__main__":
    test_rasmodecontroller()