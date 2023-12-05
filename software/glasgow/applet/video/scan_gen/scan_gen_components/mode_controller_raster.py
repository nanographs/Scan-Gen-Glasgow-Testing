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
    def __init__(self):
        #self.out_fifo = out_fifo
        self.in_fifo_w_data = Signal(8)
        self.in_fifo_w_en = Signal()
        self.in_fifo_w_rdy = Signal()

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
    '''
    def __init__(self):

        #self.beam_controller = BeamController()

        self.beam_controller_end_of_dwell = Signal()
        self.beam_controller_start_dwell = Signal()
        self.beam_controller_next_x_position = Signal(16)
        self.beam_controller_next_y_position = Signal(16)
        self.beam_controller_next_dwell = Signal(16)

        self.raster_point_data = Signal(vector_point)

        self.raster_point_output = Signal(16)

        self.raster_output = RasterOutput()

        self.xy_scan_gen = XY_Scan_Gen()

       # self.raster_fifo = SyncFIFOBuffered(width = 8, depth = 12)


    def elaborate(self, platform):
        m = Module()
        #m.submodules["BeamController"] = self.beam_controller
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