import amaranth
from amaranth import *
from amaranth.sim import Simulator
from amaranth.lib.fifo import SyncFIFO, SyncFIFOBuffered

if "glasgow" in __name__: ## running as applet
    from ..scan_gen_components.addresses import *
    from ..scan_gen_components.byte_packing import TwoByteInbox
    from ..scan_gen_components.mode_controller import ModeController
else:
    from addresses import *
    from byte_packing import TwoByteInbox
    from mode_controller import ModeController
    from test_streams import *
    from simulation import _fifo_write_scan_data

class InputBus(Elaboratable):
    '''
    Attributes:
        Input_data: An 8 bit value, from a data stream
        Mailboxes: Instances of TwoByteInbox
        Beam_controller: a module holding information about where the beam is supposed to be

        yellowpages: A dictionary that links an address to each mailbox
    '''

    def __init__(self, out_fifo = SyncFIFOBuffered(width = 8, depth = 10)):
        self.input_data = Signal(8)

        self.inbox = TwoByteInbox()
        # self.vx_mailbox = TwoByteInbox()
        # self.vy_mailbox = TwoByteInbox()
        # self.vd_mailbox = TwoByteInbox()
        # self.rx_mailbox = TwoByteInbox()
        # self.ry_mailbox = TwoByteInbox()
        # self.rd_mailbox = TwoByteInbox()
        # self.rux_mailbox = TwoByteInbox()
        # self.ruy_mailbox = TwoByteInbox()
        # self.rlx_mailbox = TwoByteInbox()
        # self.rly_mailbox = TwoByteInbox()


        # self.yellowpages_vector = {
        #     Vector_Data.X:self.vx_mailbox,
        #     Vector_Data.Y:self.vy_mailbox,
        #     Vector_Data.D:self.vd_mailbox,
        # }
        # self.yellowpages_raster = {
        #     Raster_Data.X:self.rx_mailbox,
        #     Raster_Data.Y:self.ry_mailbox,
        #     Raster_Data.D:self.rd_mailbox,
        #     Raster_Data.UX:self.rux_mailbox,
        #     Raster_Data.UY:self.ruy_mailbox,
        #     Raster_Data.LX:self.rlx_mailbox,
        #     Raster_Data.LY:self.rly_mailbox,
        # } ## Address     :   Mailbox

        self.mode_controller = ModeController()

        self.yellowpages_vector = {
            Vector_Data.X:self.mode_controller.v_x_mailbox,
            Vector_Data.Y:self.mode_controller.v_y_mailbox,
            Vector_Data.D:self.mode_controller.v_d_mailbox,
        }
        self.yellowpages_raster = {
            Raster_Data.X:self.mode_controller.r_x_mailbox,
            Raster_Data.Y:self.mode_controller.r_y_mailbox,
            Raster_Data.D:self.mode_controller.r_d_mailbox,
            Raster_Data.UX:self.mode_controller.r_ux_mailbox,
            Raster_Data.UY:self.mode_controller.r_uy_mailbox,
            Raster_Data.LX:self.mode_controller.r_lx_mailbox,
            Raster_Data.LY:self.mode_controller.r_ly_mailbox,
        } ## Address     :   Mailbox


        # self.mode_controller = ModeController(
        #     self.vx_mailbox, self.vy_mailbox, self.vd_mailbox,
        #     self.rx_mailbox, self.ry_mailbox, self.rd_mailbox,
        #     self.ruy_mailbox, self.rux_mailbox,
        #     self.rly_mailbox, self.rlx_mailbox,
        # )

        

        self.out_fifo = out_fifo

        self.reset = Signal()

        self.read_address_c = Signal(address_layout)
        self.read_address_s = Signal(address_layout)

        self.reading_address = Signal()
        self.waiting = Signal()

        self.lb = Signal()

    def elaborate(self, platform):
        m = Module()

        m.submodules["out_fifo"] = self.out_fifo
        m.submodules["2b_inbox"] = self.inbox
        m.submodules["ModeCtrl"] = self.mode_controller

        
        with m.FSM() as fsm:
            with m.State("Read_Address"):
                m.d.comb += self.reading_address.eq(1)
                m.d.comb += self.out_fifo.r_en.eq(1)
                with m.If(self.out_fifo.r_rdy):
                    #m.d.comb += self.input_data.eq(self.out_fifo.r_data)
                    m.d.comb += self.read_address_c.eq(self.out_fifo.r_data)
                    m.d.sync += self.read_address_s.eq(self.out_fifo.r_data)
                    m.d.sync += self.mode_controller.scan_mode.eq(self.read_address_c.ScanMode)
                    m.d.sync += self.mode_controller.dwell_mode.eq(self.read_address_c.DwellMode)
                    m.next = "Read_Data"
            with m.State("Read_Data"):
                m.d.comb += self.reading_address.eq(0)
                m.d.comb += self.out_fifo.r_en.eq(1)
                with m.If(self.out_fifo.r_rdy):
                    m.d.comb += self.inbox.input.eq(self.out_fifo.r_data)
                    m.d.comb += self.inbox.parsing.eq(1)
                    with m.If(self.inbox.last_byte):
                        with m.Switch(self.read_address_s.ScanMode):
                            with m.Case(ScanMode.Raster):
                                with m.Switch(self.read_address_s.DataType):
                                    for address in self.yellowpages_raster:
                                        mailbox = self.yellowpages_raster.get(address)
                                        with m.Case(address):
                                            with m.If(~mailbox.flag):
                                                m.d.comb += mailbox.flag_in.eq(1)
                                                m.d.sync += mailbox.value.eq(self.inbox.value)
                                                    
                            with m.Case(ScanMode.Vector):
                                with m.Switch(self.read_address_s.DataType):
                                    for address in self.yellowpages_vector:
                                        mailbox = self.yellowpages_vector.get(address)
                                        with m.Case(address):
                                            with m.If(~mailbox.flag):
                                                m.d.comb += mailbox.flag_in.eq(1)
                                                m.d.sync += mailbox.value.eq(self.inbox.value)
                                                

                        m.next = "Read_Address"

                    
        return m
    def ports(self):
        return self.reading_address



def sim_inputbus():
    dut = InputBus()
    def bench():
        yield dut.mode_controller.beam_controller.count_enable.eq(1)
        for n in basic_vector_stream:
            address, data = n
            yield from _fifo_write_scan_data(dut.out_fifo, address, data)
        
    
    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("multimode_sim.vcd"):
        sim.run()

if __name__ == "__main__":
    sim_inputbus()


# from amaranth.back import verilog

# def export_modecontroller():
#     top = InputBus()
#     with open("multimode_input.v", "w") as f:
#         f.write(verilog.convert(top, ports=[top.ports()]))

