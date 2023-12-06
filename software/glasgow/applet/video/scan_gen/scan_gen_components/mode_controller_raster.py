import amaranth
from amaranth import *
from amaranth.sim import Simulator
from amaranth.lib.fifo import SyncFIFO, SyncFIFOBuffered


if "glasgow" in __name__: ## running as applet
    from ..scan_gen_components.beam_controller import BeamController
    from ..scan_gen_components.xy_scan_gen import XY_Scan_Gen
    from ..scan_gen_components.addresses import *
else:
#if __name__ == "__main__":
    from beam_controller import BeamController
    from xy_scan_gen import XY_Scan_Gen
    from addresses import *
    from test_streams import test_vector_points, _fifo_write_vector_point


class RasterOutput(Elaboratable):
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
        self.strobe_out = Signal()


    def elaborate(self, platform):
        m = Module()

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
                    m.next = "D2"
            with m.State("D1"):    
                with m.If(self.enable):
                    m.d.comb += self.in_fifo_w_data.eq(self.raster_dwell_data.D1)
                    m.next = "D2"
            with m.State("D2"):  
                with m.If(self.enable):
                    m.d.comb += self.in_fifo_w_data.eq(self.raster_dwell_data.D2)
                    m.next = "Dwell_Waiting"
        return m



class RasterModeController(Elaboratable):
    '''
    raster_output: See RasterOutput
        This module takes 32-bit wide raster position data (not used)
        and 16-bit wide dwell time or brightness data, and disassembles
        it into bytes to write to the in_fifo
    
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

    ### TO DO: Implement raster patterning mode
        - Create a RasterInput module to read a stream of 16-bit dwell times
        - Possibly create a RasterFIFO, to ensure there is still data to
        read from when the out_fifo isn't available, and thus keep the beam moving
    '''
    def __init__(self):
        self.raster_output = RasterOutput()
        self.xy_scan_gen = XY_Scan_Gen()

        self.raster_point_data = Signal(vector_point)
        self.raster_point_output = Signal(16)

        self.beam_controller_end_of_dwell = Signal()
        self.beam_controller_start_dwell = Signal()
        self.beam_controller_next_x_position = Signal(16)
        self.beam_controller_next_y_position = Signal(16)
        self.beam_controller_next_dwell = Signal(16)
        # self.raster_fifo = SyncFIFOBuffered(width = 8, depth = 12)

    def elaborate(self, platform):
        m = Module()
        m.submodules["RasterOutput"] = self.raster_output
        # m.submodules["RasterFIFO"] = self.raster_fifo
        m.submodules["XYScanGen"] = self.xy_scan_gen


        m.d.comb += self.beam_controller_next_dwell.eq(1)

        m.d.comb += self.raster_output.raster_dwell_data_c.eq(self.raster_point_output)
        with m.If(self.beam_controller_end_of_dwell):
            m.d.comb += self.xy_scan_gen.increment.eq(1)
            m.d.comb += Cat(self.raster_point_data.X1,self.raster_point_data.X2).eq(self.xy_scan_gen.current_x)
            m.d.comb += Cat(self.raster_point_data.Y1,self.raster_point_data.Y2).eq(self.xy_scan_gen.current_y)
            m.d.comb += self.raster_output.strobe_in_xy.eq(1)
            # with m.If(~(self.beam_controller_start_dwell)):
            #     m.d.comb += self.raster_output.strobe_in_dwell.eq(1)
            #     #m.d.comb += self.raster_output.raster_dwell_data_c.eq(self.beam_controller.dwell_time)
            #     m.d.comb += self.raster_output.raster_dwell_data_c.eq(self.raster_point_output)
            m.d.comb += self.raster_output.raster_position_data_c.eq(Cat(self.raster_point_data.X1,
                                                                        self.raster_point_data.X2,
                                                                        self.raster_point_data.Y1,
                                                                        self.raster_point_data.Y2))
            m.d.comb += self.beam_controller_next_x_position.eq(Cat(self.raster_point_data.X1, 
                                                                    self.raster_point_data.X2))
            m.d.comb += self.beam_controller_next_y_position.eq(Cat(self.raster_point_data.Y1, 
                                                                    self.raster_point_data.Y2))
            # m.d.comb += self.beam_controller_next_dwell.eq(Cat(self.raster_point_data.D1, 
            #                                                         self.raster_point_data.D2))


        
        

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