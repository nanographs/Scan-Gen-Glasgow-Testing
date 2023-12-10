import amaranth
from amaranth import *
from amaranth.sim import Simulator
from amaranth.lib.fifo import SyncFIFO, SyncFIFOBuffered


if "glasgow" in __name__: ## running as applet
    from ..scan_gen_components.byte_replacer import ByteReplacer
    from ..scan_gen_components.beam_controller import BeamController
    from ..scan_gen_components.xy_scan_gen import XY_Scan_Gen
    from ..scan_gen_components.addresses import *
else:
#if __name__ == "__main__":
    from byte_replacer import ByteReplacer
    from beam_controller import BeamController
    from xy_scan_gen import XY_Scan_Gen
    from addresses import *
    from test_streams import test_vector_points, _fifo_write_vector_point

class RasterReader(Elaboratable): 
    '''
    out_fifo_r_data: Signal, in, 8
        This signal is combinatorially driven by the top level out_fifo.r_data
    
    raster_point_data: Signal, internal, 48
        Each cycle that the out_fifo is read from, a byte is synchronously written 
        to vector_point_data. 
    raster_point_data_c: Signal, out, 48
        This is the signal that the next values for the beam controller are read from.
        This signal is combinatorially assigned to the value of vector_point_data
        and the latest byte from the out_fifo. This is so that the full vector point
        data can be used immediately. If the data can't be used immediately, the last
        byte is synchronously added to raster_point_data and the state machine moves to 
        the HOLD state.

    data_complete: Signal, out, 1:
        Asserted when all 2 bytes of a dwell time have been assembled. When this is true,
        the value of raster_point_c is valid to assign as the next beam controller dwell
    enable: Signal, in, 1:
        Asserted when the out_fifo is ready to be read from. This signal is driven by 
        mode_ctrl.output_enable, which is driven by the top level io_strobe
    strobe_out: Signal, in, 1:
        Asserted when the data held in raster_point_data is used. On the cycle after this is
        asserted, the module will return to state X1 and be ready to read a new point in

    State Machine:
        D1 -> D2 -> Hold
        ↑-----↲----- ↲

    Inspiration taken from https://github.com/maia-sdr/maia-sdr/blob/main/maia-hdl/maia_hdl/packer.py
    
    '''
    def __init__(self):
        self.out_fifo_r_data = Signal(8)

        # self.raster_point_data = Signal(vector_point)
        # self.raster_point_data_c = Signal(vector_point)

        self.raster_dwell_data = Signal(vector_dwell)
        self.raster_dwell_data_c = Signal(vector_dwell)
        
        self.data_complete = Signal()
        self.enable = Signal()
        self.strobe_out = Signal()

        self.eight_bit_output = Signal()

    def elaborate(self, platform):
        m = Module()

        with m.FSM() as fsm:
            with m.State("D1"):    
                with m.If(self.enable):
                    m.d.sync += self.raster_dwell_data.D1.eq(self.out_fifo_r_data)
                    with m.If(self.eight_bit_output):
                        m.next = "Hold"
                    with m.Else():
                        m.next = "D2"
            with m.State("D2"):    
                with m.If(self.enable):
                    m.d.comb += self.data_complete.eq(1)
                    m.d.comb += self.raster_dwell_data_c.eq(Cat(self.raster_dwell_data.D1, 
                                                                self.out_fifo_r_data))
                    with m.If(self.strobe_out):
                        m.next = "D1"
                        m.d.sync += self.raster_dwell_data.eq(0)
                    with m.Else():
                        m.d.sync += self.raster_dwell_data.D2.eq(self.out_fifo_r_data)
                        m.next = "Hold"
            with m.State("Hold"):
                    m.d.comb += self.data_complete.eq(1)
                    m.d.comb += self.raster_dwell_data_c.eq(self.raster_dwell_data)
                    with m.If(self.strobe_out):
                        m.next = "D1"

        return m

class RasterWriter(Elaboratable):
    '''
    in_fifo_w_data: Signal, out, 8
        This signal combinatorially drives the top level in_fifo.w_data

    raster_position_data_c: Signal, in, 32:
        This signal is combinatorially driven by the same value that sets
        the next x and y position for the beam controller.
    raster_position_data: Signal, internal, 32
        When strobe_in_xy is asserted, this signal is synchronously set
        to the value of raster_position_data_c
    The position data of each point is stored but not used. This leaves the
    option of reconfiguring to return X and Y data as well as brightness
    for points in a raster scan.

    raster_dwell_data_c: Signal, in, 16:
        This signal is combinatorially driven by ras_mode_ctrl.raster_output_data.
        This data is driven from the ADC input data, or if testing in loopback, 
        the beam controller next dwell time
    raster_position_data: Signal, internal, 16
        When strobe_in_dwell is asserted, this signal is synchronously set
        to the value of vector_dwell_data_c

    enable: Signal, in, 1:
        Asserted when the in_fifo is ready to be written to. This signal is driven by 
        mode_ctrl.output_enable, which is driven by the top level io_strobe
    strobe_in_xy: Signal, in, 1
        Asserted when valid data is present at raster_position_data_c
        This signal also indicates that the beam controller has recieved new position
        data, so this module should prepare to recieve new brightness/dwell time data

    strobe_in_dwell: Signal, in, 1
        Asserted when valid data is present at raster_dwell_data_c
    strobe_out: Signal, out, 1
        Asserted when the data at in_fifo_w_data is *not* valid. 
        If strobe_out is high, data will *not* be written to the in_fifo

    State Machine:
                    ↓----------------------↑
        Waiting -> Dwell Waiting -> D1 -> D2
                    ↳----------------------↑                   
    '''
    def __init__(self):
        self.in_fifo_w_data = Signal(8)

        self.raster_position_data = Signal(vector_position)
        self.raster_position_data_c = Signal(vector_position)
        self.raster_dwell_data = Signal(vector_dwell)
        self.raster_dwell_data_c = Signal(vector_dwell)
        
        self.enable = Signal()
        self.strobe_in_xy = Signal()
        self.strobe_in_dwell = Signal()
        self.strobe_in_frame_sync = Signal()
        self.prev_strobe_in_frame_sync = Signal()
        self.strobe_in_line_sync = Signal()
        self.prev_strobe_in_line_sync = Signal()
        self.strobe_out = Signal()

        self.eight_bit_output = Signal()

    def elaborate(self, platform):
        m = Module()

        m.d.sync += self.prev_strobe_in_frame_sync.eq(self.strobe_in_frame_sync)
        m.d.sync += self.prev_strobe_in_line_sync.eq(self.strobe_in_line_sync)
        ## the line and frame sync strobes only occur on the first byte, D1
        ## so to make sure the frame sync is inserted at the right point after
        ## a two-byte output, we need to delay those signals another cycle
        

        with m.FSM() as fsm:
            with m.State("Waiting"):
                m.d.comb += self.strobe_out.eq(1)
                with m.If(self.strobe_in_xy):
                    m.d.sync += self.raster_position_data.eq(self.raster_position_data_c)
                    m.next = "Dwell_Waiting"
            with m.State("Dwell_Waiting"):
                m.d.comb += self.strobe_out.eq(1)
                with m.If((self.strobe_in_dwell) & ~(self.enable)):
                    m.d.comb += self.strobe_out.eq(0)
                    m.d.sync += self.raster_dwell_data.eq(self.raster_dwell_data_c)
                    m.next = "D1"
                with m.If((self.strobe_in_dwell) & (self.enable)):
                    m.d.comb += self.strobe_out.eq(0)
                    m.d.sync += self.raster_dwell_data.eq(self.raster_dwell_data_c)
                    m.d.comb += self.in_fifo_w_data.eq(self.raster_dwell_data_c.D1)
                    with m.If(self.eight_bit_output):
                        with m.If(self.strobe_in_frame_sync):
                            m.next = "Frame_Sync_B1"
                        with m.Elif(self.strobe_in_line_sync):
                            m.next = "Line_Sync_B1"
                        with m.Else():
                            m.next = "Dwell_Waiting"
                    with m.Else():
                        m.next = "D2"
            with m.State("D1"):  
                m.d.comb += self.strobe_out.eq(1)  
                with m.If(self.enable):
                    m.d.comb += self.strobe_out.eq(0)
                    m.d.comb += self.in_fifo_w_data.eq(self.raster_dwell_data.D1)
                    with m.If(self.eight_bit_output):
                        with m.If(self.strobe_in_frame_sync):
                            m.next = "Frame_Sync_B1"
                        with m.Elif(self.strobe_in_line_sync):
                            m.next = "Line_Sync_B1"
                        with m.Else():
                            m.next = "Dwell_Waiting"
                    with m.Else():
                        m.next = "D2"
            with m.State("D2"):  
                m.d.comb += self.strobe_out.eq(1) 
                with m.If(self.enable):
                    m.d.comb += self.strobe_out.eq(0) 
                    m.d.comb += self.in_fifo_w_data.eq(self.raster_dwell_data.D2)
                    with m.If(self.prev_strobe_in_frame_sync):
                            m.next = "Frame_Sync_B1"
                    with m.Elif(self.prev_strobe_in_line_sync):
                            m.next = "Line_Sync_B1"
                    with m.Else():
                            m.next = "Dwell_Waiting"
            with m.State("Frame_Sync_B1"):
                m.d.comb += self.in_fifo_w_data.eq(0)
                with m.If(self.enable):
                    with m.If(self.eight_bit_output):
                        m.next = "Dwell_Waiting"
                    with m.Else():
                        m.next = "Frame_Sync_B2"
            with m.State("Frame_Sync_B2"):
                m.d.comb += self.in_fifo_w_data.eq(0)
                with m.If(self.enable):
                    m.next = "Dwell_Waiting"
            with m.State("Line_Sync_B1"):
                m.d.comb += self.in_fifo_w_data.eq(1)
                with m.If(self.enable):
                    with m.If(self.eight_bit_output):
                        m.next = "Dwell_Waiting"
                    with m.Else():
                        m.next = "Line_Sync_B2"
            with m.State("Line_Sync_B2"):
                m.d.comb += self.in_fifo_w_data.eq(1)
                with m.If(self.enable):
                    m.next = "Dwell_Waiting"
        return m



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
        self.raster_writer = RasterWriter()
        self.raster_reader = RasterReader()
        self.xy_scan_gen = XY_Scan_Gen()
        self.byte_replacer = ByteReplacer()

        self.raster_point_data = Signal(vector_point)
        self.raster_point_output = Signal(vector_dwell)

        self.beam_controller_end_of_dwell = Signal()
        self.beam_controller_start_dwell = Signal()
        self.beam_controller_next_x_position = Signal(16)
        self.beam_controller_next_y_position = Signal(16)
        self.beam_controller_next_dwell = Signal(16)

        self.eight_bit_output = Signal()
        self.do_frame_sync = Signal()
        self.do_line_sync = Signal()

        self.raster_fifo = SyncFIFOBuffered(width = 16, depth = 256)

    def elaborate(self, platform):
        m = Module()
        m.submodules["RasterWriter"] = self.raster_writer
        m.submodules["RasterReader"] = self.raster_reader
        m.submodules["RasterFIFO"] = self.raster_fifo
        m.submodules["XYScanGen"] = self.xy_scan_gen
        m.submodules["ByteReplace"] = self.byte_replacer

        m.d.comb += self.raster_reader.strobe_out.eq(self.raster_fifo.w_rdy)
        with m.If((self.raster_reader.data_complete) & (self.raster_fifo.w_rdy)):
            m.d.comb += self.raster_fifo.w_en.eq(1)
            m.d.comb += self.raster_fifo.w_data.eq(self.raster_reader.raster_dwell_data_c)

        m.d.comb += self.byte_replacer.do_frame_sync.eq(self.do_frame_sync)
        m.d.comb += self.byte_replacer.do_line_sync.eq(self.do_line_sync)
        m.d.comb += self.byte_replacer.eight_bit_output.eq(self.eight_bit_output)

        m.d.comb += self.byte_replacer.point_data.eq(self.raster_point_output)
        m.d.comb += self.raster_writer.raster_dwell_data_c.eq(self.byte_replacer.processed_point_data)

        with m.If(self.beam_controller_end_of_dwell):
            with m.If(self.do_frame_sync):
                m.d.sync += self.raster_writer.strobe_in_frame_sync.eq(self.xy_scan_gen.frame_sync) ### one cycle delay
            with m.If(self.do_line_sync):
                m.d.sync += self.raster_writer.strobe_in_line_sync.eq(self.xy_scan_gen.line_sync) ### one cycle delay
            m.d.comb += self.xy_scan_gen.increment.eq(1)
            m.d.comb += Cat(self.raster_point_data.X1,self.raster_point_data.X2).eq(self.xy_scan_gen.current_x)
            m.d.comb += Cat(self.raster_point_data.Y1,self.raster_point_data.Y2).eq(self.xy_scan_gen.current_y)
            m.d.comb += self.raster_writer.strobe_in_xy.eq(1)
            m.d.comb += self.raster_writer.raster_position_data_c.eq(Cat(self.raster_point_data.X1,
                                                                        self.raster_point_data.X2,
                                                                        self.raster_point_data.Y1,
                                                                        self.raster_point_data.Y2))
            m.d.comb += self.beam_controller_next_x_position.eq(Cat(self.raster_point_data.X1, 
                                                                    self.raster_point_data.X2))
            m.d.comb += self.beam_controller_next_y_position.eq(Cat(self.raster_point_data.Y1, 
                                                                    self.raster_point_data.Y2))
            with m.If(self.raster_fifo.r_rdy):
                m.d.comb += self.beam_controller_next_dwell.eq(self.raster_fifo.r_data)
                m.d.comb += self.raster_fifo.r_en.eq(1)


        
        

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