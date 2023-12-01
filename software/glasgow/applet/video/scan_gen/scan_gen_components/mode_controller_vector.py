import amaranth
from amaranth import *
from amaranth.sim import Simulator
from amaranth.lib.fifo import SyncFIFO, SyncFIFOBuffered

print("hello")
print("name:", __name__)
if "glasgow" in __name__: ## running as applet
    from ..scan_gen_components.beam_controller import BeamController
    from ..scan_gen_components.xy_scan_gen import XY_Scan_Gen
    from ..scan_gen_components.addresses import *
if __name__ == "__main__":
    from beam_controller import BeamController
    from xy_scan_gen import XY_Scan_Gen
    from addresses import *
    
    from test_streams import test_vector_points, _fifo_write_vector_point


class VectorInput(Elaboratable): 
    def __init__(self):
        self.out_fifo_r_data = Signal(8)
        self.out_fifo_r_en = Signal()
        self.out_fifo_r_rdy = Signal()

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




class VectorOutput(Elaboratable):
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
                    m.d.sync += self.vector_dwell_data.eq(self.vector_dwell_data_c)
                    m.d.comb += self.in_fifo_w_data.eq(self.vector_dwell_data_c.D1)
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
    '''
    def __init__(self):
        self.beam_controller = BeamController()

        self.vector_point_data = Signal(vector_point)

        self.vector_fifo = SyncFIFOBuffered(width = 48, depth = 12)

        self.vector_input = VectorInput()
        self.vector_output = VectorOutput()

    def elaborate(self, platform):
        m = Module()
        m.submodules["BeamController"] = self.beam_controller
        m.submodules["VectorInput"] = self.vector_input
        m.submodules["VectorOutput"] = self.vector_output
        m.submodules["VectorFIFO"] = self.vector_fifo

        m.d.comb += self.beam_controller.dwelling.eq(1)
        m.d.comb += self.vector_input.strobe_out.eq(self.vector_fifo.w_rdy)

        with m.If((self.vector_input.data_complete) & (self.vector_fifo.w_rdy)):
            m.d.comb += self.vector_fifo.w_en.eq(1)
            m.d.comb += self.vector_fifo.w_data.eq(self.vector_input.vector_point_data_c)

        with m.If(self.vector_fifo.r_rdy & self.beam_controller.end_of_dwell):
            m.d.comb += self.vector_fifo.r_en.eq(1)
            m.d.comb += self.vector_point_data.eq(self.vector_fifo.r_data)
            m.d.comb += self.vector_output.strobe_in_xy.eq(1)
            with m.If(~(self.beam_controller.start_dwell)):
                m.d.comb += self.vector_output.strobe_in_dwell.eq(1)
                m.d.comb += self.vector_output.vector_dwell_data_c.eq(self.beam_controller.dwell_time)
            m.d.comb += self.vector_output.vector_position_data_c.eq(Cat(self.vector_point_data.X1,
                                                                        self.vector_point_data.X2,
                                                                        self.vector_point_data.Y1,
                                                                        self.vector_point_data.Y2))
            m.d.comb += self.beam_controller.next_x_position.eq(Cat(self.vector_point_data.X1, 
                                                                    self.vector_point_data.X2))
            m.d.comb += self.beam_controller.next_y_position.eq(Cat(self.vector_point_data.Y1, 
                                                                    self.vector_point_data.Y2))
            m.d.comb += self.beam_controller.next_dwell.eq(Cat(self.vector_point_data.D1, 
                                                                    self.vector_point_data.D2))
            m.d.comb += self.beam_controller.next_x_position.eq(Cat(self.vector_point_data.X1, 
                                                                    self.vector_point_data.X2))
            m.d.comb += self.beam_controller.next_y_position.eq(Cat(self.vector_point_data.Y1, 
                                                                    self.vector_point_data.Y2))
            m.d.comb += self.beam_controller.next_dwell.eq(Cat(self.vector_point_data.D1, 
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