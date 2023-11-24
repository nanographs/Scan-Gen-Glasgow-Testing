import amaranth
from amaranth import *
from amaranth.sim import Simulator
from amaranth.lib import data, enum
from amaranth.lib.fifo import SyncFIFO

from output_handling import *
from xy_scan_gen import *
from multimode_input import InputBus

from addresses import *
from byte_packing import *
from data_latch_bus import *

import glasgow
from glasgow.platform.all import GlasgowPlatformRevC123


# class BeamController(Elaboratable):
#     '''
#     Parameters:
#         X Mailbox: TwoByteInbox()
#         Y Mailbox: TwoByteInbox()
#         D Mailbox: TwoByteInbox()
    
#     Attributes:
#         X position, y position: 14-bit values
#         Dwell time : 14 bit value
#         Dwelling - True when counter will be incremented next cycle
#         Counter - Value that is incremented each cycle and compared to dwell time

#     '''
#     def __init__(self, x_mailbox, y_mailbox, d_mailbox):
#         self.x_mailbox = x_mailbox
#         self.y_mailbox = y_mailbox
#         self.d_mailbox = d_mailbox

#         self.x_position = Signal(14)
#         self.y_position = Signal(14)
#         self.dwell_time = Signal(14)
#         self.dwelling = Signal()
#         self.end_of_dwell = Signal()

#         self.counter = Signal(14)

#         self.scan_mode = Signal()
#         self.frame_generator = XY_Scan_Gen()

#     def elaborate(self, platform):
#         m = Module()

#         with m.If(self.dwelling):
#             m.d.comb += self.end_of_dwell.eq(self.counter == self.dwell_time)
#             m.d.sync += self.counter.eq(self.counter + 1)
#             with m.If(self.end_of_dwell):
#                 m.d.sync += self.dwelling.eq(0)
#                 m.d.sync += self.counter.eq(0)
#         with m.Else():
#             with m.If(self.scan_mode.eq(ScanMode.Vector)):
#                 with m.If(self.d_mailbox.flag):
#                     m.d.sync += self.dwell_time.eq(self.d_mailbox.value)
#                     m.d.sync += self.dwelling.eq(1)
#                 with m.If(self.x_mailbox.flag):
#                     m.d.sync += self.x_position.eq(self.x_mailbox.value)
#                 with m.If(self.y_mailbox.flag):
#                     m.d.sync += self.y_position.eq(self.y_mailbox.value)
#             with m.If(self.scan_mode == ScanMode.Raster):
#                 self.frame_generator.increment.eq(1)

#         return m






# class InputBus(Elaboratable):
#     '''
#     Attributes:
#         Input_data: An 8 bit value, from a data stream
#         Mailboxes: Instances of TwoByteInbox
#         Beam_controller: a module holding information about where the beam is supposed to be

#         yellowpages: A dictionary that links an address to each mailbox

#         States:
#             There is only one state, but it starts over and over
#     '''

#     def __init__(self):
#         self.input_data = Signal(8)
#         self.x_mailbox = TwoByteInbox(self.input_data)
#         self.y_mailbox = TwoByteInbox(self.input_data)
#         self.d_mailbox = TwoByteInbox(self.input_data)
#         self.yellowpages = {
#             Vector_Address.X:self.x_mailbox,
#             Vector_Address.Y:self.y_mailbox,
#             Vector_Address.D:self.d_mailbox
#         } ## Address     :   Mailbox
#         self.beam_controller = BeamController(self.x_mailbox, 
#         self.y_mailbox, self.d_mailbox)
#         self.frame_generator = XY_Scan_Gen()

#         ## alternate code - for listing all addresses through enumeration
#         ## instead of individually instantiating each mailbox
#         # self.yellowpages = {}
#         # for n, address in enumerate(Vector_Data):
#         #     mailbox = TwoByteMailbox(self.input_data)
#         #     self.yellowpages.update({address.value:mailbox})

#         self.in_fifo = SyncFIFO(width = 8, depth = 16, fwft = True)

#     def elaborate(self, platform):
#         m = Module()

#         m.submodules["BeamController"] = self.beam_controller
#         m.submodules["IN_FIFO"] = self.in_fifo

#         with m.FSM() as fsm:

#             with m.State("Read_Address"):
#                 m.d.comb += self.in_fifo.r_en.eq(1)
#                 m.d.comb += self.input_data.eq(self.in_fifo.r_data)
#                 with m.Switch(self.input_data):
#                     for address in self.yellowpages:
#                         mailbox = self.yellowpages.get(address)
#                         #m.submodules += mailbox
#                         m.submodules[f"mailbox_{address}"] = mailbox
#                         print(m.submodules)
#                         #m.submodules[] = mailbox
#                         with m.Case(address):
#                             m.d.sync += mailbox.parsing.eq(1)
#                             with m.If(mailbox.flag):
#                                 m.next = "Read_Address"
                
                    
#         return m



class OutputBus(Elaboratable):
    def __init__(self):
        self.video_sink = VideoSink()
        self.out_fifo = SyncFIFO(width = 8, depth = 16, fwft = True)
        #self.pixel_in = Signal(16)
        self.video_outbox = TwoByteOutbox(self.video_sink.pixel_out)
        self.strobe = Signal()
        
    def elaborate(self,platform):
        m = Module()

        m.submodules["VSink"] = self.video_sink
        m.submodules["VMailbox"] = self.video_outbox
        m.submodules["OUT_FIFO"] = self.out_fifo
        
        #m.d.comb += self.pixel_in.eq(self.video_sink.pixel_out)
        
        #m.d.comb += self.video_outbox.parsing.eq()

        m.d.comb += self.out_fifo.w_data.eq(self.video_outbox.value)

        with m.FSM() as fsm:
            with m.State("Reading Data"):
                m.d.sync += self.out_fifo.w_en.eq(0)
                with m.If(self.strobe):
                    m.d.comb += self.video_sink.sinking.eq(1)
                    with m.If(self.video_sink.pipeline_offsetter.pipeline_full):
                        m.d.sync += self.video_outbox.parsing.eq(1)
                        m.d.sync += self.out_fifo.w_en.eq(1)
                        with m.If(self.video_outbox.flag):
                            m.next = "Writing Second Byte"
            with m.State("Writing Second Byte"):
                m.next = "Reading Data"


        #         # m.d.comb += self.out_fifo.w_data.eq(self.video_sink.pixel_out[0:7])
        #         # m.d.comb += self.out_fifo.w_en.eq(1)
        #             m.next = "Second Byte"
        #     with m.State("Second Byte"):
        #         m.d.comb += self.video_outbox.parsing.eq(1)
        #         m.d.comb += self.out_fifo.w_data.eq(self.video_outbox.value)
        #         m.d.comb += self.out_fifo.w_en.eq(1)
        #         # m.d.comb += self.out_fifo.w_data.eq(self.video_sink.pixel_out[7:15])
        #         # m.d.comb += self.out_fifo.w_en.eq(1)
        #         m.next = "First Byte"

        return m



class IOBus(Elaboratable):
    def __init__(self):
        self.input_bus = InputBus()
        self.output_bus = OutputBus()
        self.bus_multiplexer = BusMultiplexer()
        self.pins = Signal(14)
    def elaborate(self, platform):
        m = Module()
        m.submodules["InBus"] = self.input_bus
        m.submodules["OutBus"] = self.output_bus
        m.submodules["MuxBus"] = self.bus_multiplexer

        # x_enable = Resource("X_ENABLE", 0, Pins("B1", dir="o"), Attrs(IO_STANDARD="SB_LVCMOS33")),
        # # x_latch = Resource("X_LATCH", 0, Pins("C4", dir="o"), Attrs(IO_STANDARD="SB_LVCMOS33")),
        # # y_enable = Resource("Y_ENABLE", 0, Pins("C2", dir="o"), Attrs(IO_STANDARD="SB_LVCMOS33")),
        # # y_latch = Resource("Y_LATCH", 0, Pins("E1", dir="o"), Attrs(IO_STANDARD="SB_LVCMOS33")),
        # # a_enable = Resource("A_ENABLE", 0, Pins("D2", dir="o"), Attrs(IO_STANDARD="SB_LVCMOS33")),
        # # a_latch = Resource("A_LATCH", 0, Pins("E2", dir="o"), Attrs(IO_STANDARD="SB_LVCMOS33")),
        # # d_clock = Resource("D_CLOCK", 0, Pins("F1", dir="o"), Attrs(IO_STANDARD="SB_LVCMOS33")),
        # # a_clock = Resource("A_CLOCK", 0, Pins("F4", dir="o"), Attrs(IO_STANDARD="SB_LVCMOS33")),

        # m.d.comb += x_enable.eq(self.bus_multiplexer.x_dac.oe)


        m.d.comb += pins_a.o.eq(self.pins[0:7])
        m.d.comb += pins_b.o.eq(self.pins[7:15])

        m.d.comb += self.bus_multiplexer.sampling.eq(self.input_bus.mode_controller.beam_controller.dwelling)
        with m.If(self.bus_multiplexer.is_x):
            m.d.comb += self.pins.eq(self.input_bus.mode_controller.beam_controller.x_position)
        with m.If(self.bus_multiplexer.is_y):
            m.d.comb += self.pins.eq(self.input_bus.mode_controller.beam_controller.y_position)
        with m.If(self.bus_multiplexer.is_a):
            m.d.comb += self.output_bus.video_sink.pixel_in.eq(self.pins)
            # Loopback
            #m.d.comb += self.output_bus.video_sink.pixel_in.eq(self.input_bus.mode_controller.beam_controller.dwell_time)
        m.d.comb += self.output_bus.video_sink.dwelling.eq(self.input_bus.mode_controller.beam_controller.dwelling)
        #m.d.comb += self.output_bus.video_sink.dwell_time_averager.start_new_average.eq(self.input_bus.beam_controller.end_of_dwell)
        m.d.comb += self.output_bus.strobe.eq(self.input_bus.mode_controller.beam_controller.end_of_dwell)
        return m

stream = [
    [Vector_Address.X, 1000], #X, 1000
    [Vector_Address.Y, 2000], #Y, 2000
    [Vector_Address.D, 10],  #D, 50
    [Vector_Address.X, 1250], #X, 1000
    [Vector_Address.Y, 1700], #Y, 2000
    [Vector_Address.D, 11],  #D, 50
    [Constant_Raster_Address.X, 15], #X, 1250
    [Constant_Raster_Address.Y, 25], #Y, 2500
    [Constant_Raster_Address.D, 12],  #D, 75
    
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
        for n in range(100):
            yield
    
    
    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("vector_sim.vcd"):
        sim.run()


    



def sim_outputbus():
    dut = OutputBus()
    def bench():
        yield dut.strobe.eq(1)
        for n in range(len(test_pixel_stream)):
            yield dut.video_sink.dwell_time_averager.start_new_average.eq(1)
            next_pixel = test_pixel_stream[n]
            # yield dut.video_sink.dwelling.eq(1)
            # yield dut.video_sink.sinking.eq(1)
            yield dut.video_sink.pixel_in.eq(next_pixel)
            #if n >= 6:
                #assert(yield(dut.video_sink.pipeline_full))
            yield
            # yield dut.video_sink.sinking.eq(0)
            yield
        yield dut.strobe.eq(0)
        yield
    
    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("outputbus_sim.vcd"):
        sim.run()


def sim_iobus():
    dut = IOBus()
    def bench():
        for n in stream:
            address, data = n
            bytes_data = Const(data, unsigned(16))
            print("address:", address)
            yield dut.input_bus.in_fifo.w_en.eq(1)
            yield dut.input_bus.in_fifo.w_data.eq(address)
            # yield dut.input_data.eq(address)
            yield
            print("data 1:", bytes_data[0:7])
            # yield dut.input_data.eq(bytes_data[0:7])
            yield dut.input_bus.in_fifo.w_en.eq(1)
            yield dut.input_bus.in_fifo.w_data.eq(bytes_data[0:7])
            yield
            print("data 2:", bytes_data[7:15])
            # yield dut.input_data.eq(bytes_data[7:15])
            yield dut.input_bus.in_fifo.w_en.eq(1)
            yield dut.input_bus.in_fifo.w_data.eq(bytes_data[7:15])
            yield
        for n in range(100):
            yield
    
    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("iobus_sim.vcd"):
        sim.run()

#sim_inputbus()
#sim_outputbus()
#sim_iobus()
#test_twobyteoutbox()
#test_beamcontroller()

GlasgowPlatformRevC123().build(IOBus())