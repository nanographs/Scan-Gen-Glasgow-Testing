import amaranth
from amaranth import *
from amaranth.sim import Simulator
from amaranth.lib.fifo import SyncFIFO, SyncFIFOBuffered


if "glasgow" in __name__: ## running as applet
    from ..gateware.stream_reader import StreamReader
    from ..gateware.stream_writer import StreamWriter
    from ..gateware.xy_scan_gen import XY_Scan_Gen
    from ..gateware.structs import *
else:
#if __name__ == "__main__":
    from stream_reader import StreamReader
    from stream_writer import StreamWriter
    from xy_scan_gen import XY_Scan_Gen
    from structs import *
    from test_streams import test_vector_points, _fifo_write_vector_point

class RasterModeController(Elaboratable):
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
    
    XYScanGen: A module with two nested counters that iterates through all points
    in a two-dimensional array

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
        self.writer = StreamWriter(scan_dwell_8)
        self.onebyte_writer = StreamWriter(scan_dwell_8_onebyte)
        self.reader = StreamReader(scan_dwell_8)
        
        self.xy_scan_gen = XY_Scan_Gen()
        self.xy_scan_gen_increment = Signal()

        self.adc_data_avgd = Signal(scan_dwell_8)

        self.beam_controller_end_of_dwell = Signal()
        self.beam_controller_next = Signal(scan_point_16)

        #self.raster_fifo = SyncFIFOBuffered(width = 16, depth = 256)
        
        self.load_next_point = Signal()
        self.write_this_point = Signal()

    def elaborate(self, platform):
        m = Module()
        m.submodules["Raster1byteWriter"] = self.onebyte_writer
        m.submodules["RasterWriter"] = self.writer
        m.submodules["RasterReader"] = self.reader
        #m.submodules["RasterFIFO"] = self.raster_fifo
        m.submodules["XYScanGen"] = self.xy_scan_gen


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
            m.d.comb += self.beam_controller_next.Y.eq(self.xy_scan_gen.current_y)
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