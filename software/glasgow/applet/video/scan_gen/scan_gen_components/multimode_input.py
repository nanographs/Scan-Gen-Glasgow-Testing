import amaranth
from amaranth import *
from amaranth.sim import Simulator
from amaranth.lib import data, enum
from amaranth.lib.fifo import SyncFIFO
from addresses import *
from byte_packing import TwoByteInbox

from mode_controller import ModeController

# import amaranth_boards
# from amaranth_boards.icestick import ICEStickPlatform

# import glasgow
# from glasgow.platform.all import GlasgowPlatformRevC123

class InputBus(Elaboratable):
    '''
    Attributes:
        Input_data: An 8 bit value, from a data stream
        Mailboxes: Instances of TwoByteInbox
        Beam_controller: a module holding information about where the beam is supposed to be

        yellowpages: A dictionary that links an address to each mailbox

        States:
            There is only one state, but it starts over and over
    '''

    def __init__(self):
        self.input_data = Signal(8)
        self.vx_mailbox = TwoByteInbox(self.input_data)
        self.vy_mailbox = TwoByteInbox(self.input_data)
        self.vd_mailbox = TwoByteInbox(self.input_data)
        self.rx_mailbox = TwoByteInbox(self.input_data)
        self.ry_mailbox = TwoByteInbox(self.input_data)
        self.rd_mailbox = TwoByteInbox(self.input_data)

        self.yellowpages = {
            Vector_Address.X:self.vx_mailbox,
            Vector_Address.Y:self.vy_mailbox,
            Vector_Address.D:self.vd_mailbox,
            Constant_Raster_Address.X:self.rx_mailbox,
            Constant_Raster_Address.Y:self.ry_mailbox,
            Constant_Raster_Address.D:self.rd_mailbox,
        } ## Address     :   Mailbox
        # self.beam_controller = BeamController(self.x_mailbox, 
        # self.y_mailbox, self.d_mailbox)

        # ## alternate code - for listing all addresses through enumeration
        # ## instead of individually instantiating each mailbox
        # # self.yellowpages = {}
        # # for n, address in enumerate(Vector_Data):
        # #     mailbox = TwoByteMailbox(self.input_data)
        # #     self.yellowpages.update({address.value:mailbox})

        self.mode_controller = ModeController(
            self.vx_mailbox, self.vy_mailbox, self.vd_mailbox,
            self.rx_mailbox, self.ry_mailbox, self.rd_mailbox
        )

        self.in_fifo = SyncFIFO(width = 8, depth = 16, fwft = True)

        self.input_type = Signal()
        self.scan_mode = Signal()
        self.dwell_mode = Signal()
        self.data_type = Signal(3)

    def elaborate(self, platform):
        m = Module()
        m.submodules["vx"] = self.vx_mailbox
        m.submodules["vy"] = self.vy_mailbox
        m.submodules["vd"] = self.vd_mailbox
        m.submodules["rx"] = self.rx_mailbox
        m.submodules["ry"] = self.ry_mailbox
        m.submodules["rd"] = self.rd_mailbox

        # m.submodules["BeamController"] = self.beam_controller
        m.submodules["IN_FIFO"] = self.in_fifo
        m.submodules["ModeCtrl"] = self.mode_controller


        with m.FSM() as fsm:
            with m.State("Read_Address"):
                m.d.comb += self.in_fifo.r_en.eq(1)
                m.d.comb += self.input_data.eq(self.in_fifo.r_data)

                m.d.comb += self.input_type.eq(self.input_data[2])
                m.d.comb += self.scan_mode.eq(self.input_data[3])
                #m.d.comb += self.mode_controller.scan_mode.eq(self.scan_mode)
                m.d.comb += self.dwell_mode.eq(self.input_data[4])
                m.d.comb += self.data_type.eq(self.input_data[5:8])

                with m.Switch(self.input_data):
                    for address in self.yellowpages:
                        mailbox = self.yellowpages.get(address)
                        with m.Case(address):
                            m.d.sync += mailbox.parsing.eq(1)
                            with m.If(mailbox.flag):
                                m.next = "Read_Address"


                    
        return m
    def ports(self):
        return [self.input_data]



stream = [
    # [Vector_Address.X, 1000], #X, 1000
    # [Vector_Address.Y, 2000], #Y, 2000
    # [Vector_Address.D, 13],  #D, 50
    # [Vector_Address.X, 1250], #X, 1000
    # [Vector_Address.Y, 1700], #Y, 2000
    # [Vector_Address.D, 14],  #D, 50
    [Constant_Raster_Address.X, 3], #X, 1250
    [Constant_Raster_Address.Y, 4], #Y, 2500
    [Constant_Raster_Address.D, 3],  #D, 75
    [Constant_Raster_Address.X, 4], #X, 1250
    [Constant_Raster_Address.Y, 3], #Y, 2500
    [Constant_Raster_Address.D, 3],  #D, 75
    [Vector_Address.X, 1200], #X, 1000
    [Vector_Address.Y, 1300], #Y, 2000
    [Vector_Address.D, 15],  #D, 50
    
]

def sim_inputbus():
    dut = InputBus()
    def bench():
        for n in stream:
            address, data = n
            bytes_data = Const(data, unsigned(16))
            print("address:", address)
            yield dut.in_fifo.w_en.eq(1)
            yield dut.in_fifo.w_data.eq(address)
            # yield dut.input_data.eq(address)
            yield
            print("data 1:", bytes_data[0:7])
            # yield dut.input_data.eq(bytes_data[0:7])
            yield dut.in_fifo.w_en.eq(1)
            yield dut.in_fifo.w_data.eq(bytes_data[0:7])
            yield
            print("data 2:", bytes_data[7:15])
            # yield dut.input_data.eq(bytes_data[7:15])
            yield dut.in_fifo.w_en.eq(1)
            yield dut.in_fifo.w_data.eq(bytes_data[7:15])
            yield
        for n in range(300):
            yield
    
    
    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("multimode_sim.vcd"):
        sim.run()

# #sim_inputbus()

#GlasgowPlatformRevC123().build(InputBus())
