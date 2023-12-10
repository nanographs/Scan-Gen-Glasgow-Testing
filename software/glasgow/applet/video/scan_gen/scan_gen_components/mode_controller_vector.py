import amaranth
from amaranth import *
from amaranth.sim import Simulator
from amaranth.lib.fifo import SyncFIFO, SyncFIFOBuffered
print(__name__)

if "glasgow" in __name__: ## running as applet
    from ..scan_gen_components.beam_controller import BeamController
    from ..scan_gen_components.xy_scan_gen import XY_Scan_Gen
    from ..scan_gen_components.addresses import *
#if __name__ == "__main__":
else:
    from beam_controller import BeamController
    from xy_scan_gen import XY_Scan_Gen
    from addresses import *
    
    from test_streams import test_vector_points, _fifo_write_vector_point


class VectorReader(Elaboratable): 
    '''
    out_fifo_r_data: Signal, in, 8
        This signal is combinatorially driven by the top level out_fifo.r_data
    
    vector_point_data: Signal, internal, 48
        Each cycle that the out_fifo is read from, a byte is synchronously written 
        to vector_point_data. 
    vector_point_data_c: Signal, out, 48
        This is the signal that the next values for the beam controller are read from.
        This signal is combinatorially assigned to the value of vector_point_data
        and the latest byte from the out_fifo. This is so that the full vector point
        data can be used immediately. If the data can't be used immediately, the last
        byte is synchronously added to vector_point_data and the state machine moves to 
        the HOLD state.

    data_complete: Signal, out, 1:
        Asserted when all 6 bytes of a vector point have been assembled. When this is true,
        the value of vector_point_c is valid to assign as the next beam controller values
    enable: Signal, in, 1:
        Asserted when the out_fifo is ready to be read from. This signal is driven by 
        mode_ctrl.output_enable, which is driven by the top level io_strobe
    strobe_out: Signal, in, 1:
        Asserted when the data held in vector_point_data is used. On the cycle after this is
        asserted, the module will return to state X1 and be ready to read a new point in

    State Machine:
        X1 -> X2 -> Y1 -> Y2 -> D1 -> D2 -> Hold
                                    X1 ↲    X1 ↲

    Inspiration taken from https://github.com/maia-sdr/maia-sdr/blob/main/maia-hdl/maia_hdl/packer.py
    
    '''
    def __init__(self):
        self.out_fifo_r_data = Signal(8)

        self.vector_point_data = Signal(vector_point)
        self.vector_point_data_c = Signal(vector_point)
        
        self.data_complete = Signal()
        self.enable = Signal()
        self.strobe_out = Signal()

    def elaborate(self, platform):
        m = Module()

        with m.FSM() as fsm:
            with m.State("X1"):    
                with m.If(self.enable):
                    m.d.sync += self.vector_point_data.X1.eq(self.out_fifo_r_data)
                    m.next = "X2"
            with m.State("X2"):    
                with m.If(self.enable):
                    m.d.sync += self.vector_point_data.X2.eq(self.out_fifo_r_data)
                    m.next = "Y1"
            with m.State("Y1"):    
                with m.If(self.enable):
                    m.d.sync += self.vector_point_data.Y1.eq(self.out_fifo_r_data)
                    m.next = "Y2"
            with m.State("Y2"):    
                with m.If(self.enable):
                    m.d.sync += self.vector_point_data.Y2.eq(self.out_fifo_r_data)
                    m.next = "D1"
            with m.State("D1"):    
                with m.If(self.enable):
                    m.d.sync += self.vector_point_data.D1.eq(self.out_fifo_r_data)
                    m.next = "D2"
            with m.State("D2"):    
                with m.If(self.enable):
                    m.d.comb += self.data_complete.eq(1)
                    m.d.comb += self.vector_point_data_c.eq(Cat(self.vector_point_data.X1, self.vector_point_data.X2,
                                                                self.vector_point_data.Y1, self.vector_point_data.Y2,
                                                                self.vector_point_data.D1, self.out_fifo_r_data))
                    with m.If(self.strobe_out):
                        m.next = "X1"
                        m.d.sync += self.vector_point_data.eq(0)
                    with m.Else():
                        m.d.sync += self.vector_point_data.D2.eq(self.out_fifo_r_data)
                        m.next = "Hold"
            with m.State("Hold"):
                    m.d.comb += self.data_complete.eq(1)
                    m.d.comb += self.vector_point_data_c.eq(self.vector_point_data)
                    with m.If(self.strobe_out):
                        m.next = "X1"

        return m




class VectorWriter(Elaboratable):
    '''
    in_fifo_w_data: Signal, out, 8
        This signal combinatorially drives the top level in_fifo.w_data

    vector_position_data_c: Signal, in, 32:
        This signal is combinatorially driven by the same value that sets
        the next x and y position for the beam controller.
    vector_position_data: Signal, internal, 32
        When strobe_in_xy is asserted, this signal is synchronously set
        to the value of vector_position_data_c
    vector_dwell_data_c: Signal, in, 16:
        This signal is combinatorially driven by vec_mode_ctrl.vector_output_data.
        This data is driven from the ADC input data, or if testing in loopback, 
        the beam controller next dwell time
    vector_position_data: Signal, internal, 16
        When strobe_in_dwell is asserted, this signal is synchronously set
        to the value of vector_dwell_data_c

    enable: Signal, in, 1:
        Asserted when the in_fifo is ready to be written to. This signal is driven by 
        mode_ctrl.output_enable, which is driven by the top level io_strobe
    strobe_in_xy: Signal, in, 1
        Asserted when valid data is present at vector_position_data_c
    strobe_in_dwell: Signal, in, 1
        Asserted when valid data is present at vector_dwell_data_c
    strobe_out: Signal, out, 1
        Asserted when the data at in_fifo_w_data is *not* valid. 
        If strobe_out is high, data will *not* be written to the in_fifo

    eight_bit_output: Signal, in, 1:
        If true, only one byte per brightness data point will be written 
        to the in_fifo. Two bytes of data will still be transmitted for
        each x and y position.

    State Machine:
            ↓------------------------------------------------------↑
        Waiting -> X1 -> X2 -> Y1 -> Y2 -> Dwell Waiting -> D1 -> D2
            ↳------------↑                       ↳-----------------↑
    With eight bit output:
            ↓------------------------------------------------↑
        Waiting -> X1 -> X2 -> Y1 -> Y2 -> Dwell Waiting -> D1
            ↳------------↑                       ↳-----------↑
    '''
    def __init__(self):
        self.in_fifo_w_data = Signal(8)

        self.vector_position_data = Signal(vector_position)
        self.vector_position_data_c = Signal(vector_position)
        self.vector_dwell_data = Signal(vector_dwell)
        self.vector_dwell_data_c = Signal(vector_dwell)
        
        self.enable = Signal()
        self.strobe_in_xy = Signal()
        self.strobe_in_dwell = Signal()
        self.strobe_out = Signal()

        self.eight_bit_output = Signal()

    def elaborate(self, platform):
        m = Module()

        with m.FSM() as fsm:
            with m.State("Waiting"):
                m.d.comb += self.strobe_out.eq(~self.strobe_in_xy)
                with m.If((self.strobe_in_xy) & ~(self.enable)):
                    m.d.sync += self.vector_position_data.eq(self.vector_position_data_c)
                    m.next = "X1"
                with m.If((self.strobe_in_xy) & (self.enable)):
                    m.d.sync += self.vector_position_data.eq(self.vector_position_data_c)
                    m.d.comb += self.in_fifo_w_data.eq(self.vector_position_data_c.X1)
                    m.next = "X2"
            with m.State("X1"):    
                with m.If(self.enable):
                    m.d.comb += self.in_fifo_w_data.eq(self.vector_position_data.X1)
                    m.next = "X2"
            with m.State("X2"):    
                with m.If(self.enable):
                    m.d.comb += self.in_fifo_w_data.eq(self.vector_position_data.X2)
                    m.next = "Y1"
            with m.State("Y1"):    
                with m.If(self.enable):
                    m.d.comb += self.in_fifo_w_data.eq(self.vector_position_data.Y1)
                    m.next = "Y2"
            with m.State("Y2"):    
                with m.If(self.enable):
                    m.d.comb += self.in_fifo_w_data.eq(self.vector_position_data.Y2)
                    m.next = "Dwell_Waiting"
            with m.State("Dwell_Waiting"):
                m.d.comb += self.strobe_out.eq(1)
                with m.If((self.strobe_in_dwell) & ~(self.enable)):
                    m.d.sync += self.vector_dwell_data.eq(self.vector_dwell_data_c)
                    m.next = "D1"
                with m.If((self.strobe_in_dwell) & (self.enable)):
                    m.d.comb += self.strobe_out.eq(0)
                    m.d.sync += self.vector_dwell_data.eq(self.vector_dwell_data_c)
                    m.d.comb += self.in_fifo_w_data.eq(self.vector_dwell_data_c.D1)
                    with m.If(self.eight_bit_output):
                        m.next = "Waiting"
                    with m.Else():
                        m.next = "D2"
            with m.State("D1"):    
                with m.If(self.enable):
                    m.d.comb += self.in_fifo_w_data.eq(self.vector_dwell_data.D1)
                    m.next = "D2"
            with m.State("D2"):  
                with m.If(self.enable):
                    m.d.comb += self.in_fifo_w_data.eq(self.vector_dwell_data.D2)
                    m.next = "Waiting"
        return m



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
        self.vector_fifo = SyncFIFOBuffered(width = 48, depth = 86)

        self.vector_reader = VectorReader()
        self.vector_writer = VectorWriter()

        self.vector_point_data = Signal(vector_point)
        self.vector_point_output = Signal(16)

        self.beam_controller_end_of_dwell = Signal()
        self.beam_controller_start_dwell = Signal()
        self.beam_controller_next_x_position = Signal(16)
        self.beam_controller_next_y_position = Signal(16)
        self.beam_controller_next_dwell = Signal(16)

    def elaborate(self, platform):
        m = Module()
        m.submodules["VectorReader"] = self.vector_reader
        m.submodules["VectorWriter"] = self.vector_writer
        m.submodules["VectorFIFO"] = self.vector_fifo

        m.d.comb += self.vector_reader.strobe_out.eq(self.vector_fifo.w_rdy)

        with m.If((self.vector_reader.data_complete) & (self.vector_fifo.w_rdy)):
            m.d.comb += self.vector_fifo.w_en.eq(1)
            m.d.comb += self.vector_fifo.w_data.eq(self.vector_reader.vector_point_data_c)

        m.d.comb += self.vector_writer.vector_dwell_data_c.eq(self.vector_point_output)
        with m.If(self.vector_fifo.r_rdy & self.beam_controller_end_of_dwell):
            m.d.comb += self.vector_fifo.r_en.eq(1)
            m.d.comb += self.vector_point_data.eq(self.vector_fifo.r_data)
            m.d.comb += self.vector_writer.strobe_in_xy.eq(1)

            m.d.comb += self.vector_writer.vector_position_data_c.eq(Cat(self.vector_point_data.X1,
                                                                        self.vector_point_data.X2,
                                                                        self.vector_point_data.Y1,
                                                                        self.vector_point_data.Y2))
            m.d.comb += self.beam_controller_next_x_position.eq(Cat(self.vector_point_data.X1, 
                                                                    self.vector_point_data.X2))
            m.d.comb += self.beam_controller_next_y_position.eq(Cat(self.vector_point_data.Y1, 
                                                                    self.vector_point_data.Y2))
            m.d.comb += self.beam_controller_next_dwell.eq(Cat(self.vector_point_data.D1, 
                                                                    self.vector_point_data.D2))

        
        

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