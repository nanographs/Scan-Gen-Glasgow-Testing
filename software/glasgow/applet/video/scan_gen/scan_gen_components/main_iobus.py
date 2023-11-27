import amaranth
from amaranth import *
from amaranth.sim import Simulator
from amaranth.lib import data, enum
from amaranth.lib.fifo import SyncFIFO


if "glasgow" in __name__: ## running as applet
    from ..scan_gen_components.output_bus import OutputBus
    from ..scan_gen_components.output_bus import InputBus
    from ..scan_gen_components.data_latch_bus import BusMultiplexer
else:
    from multimode_input import InputBus
    from output_bus import OutputBus
    from data_latch_bus import BusMultiplexer



class IOBus(Elaboratable):
    def __init__(self, is_simulation = True,
    out_fifo = None, in_fifo = None):
        if is_simulation:
            self.input_bus = InputBus()
            self.output_bus = OutputBus()
        else:
            self.out_fifo = out_fifo
            self.in_fifo = in_fifo
            self.input_bus = InputBus(is_simulation = False, in_fifo = self.out_fifo)
            self.output_bus = OutputBus(is_simulation = False, out_fifo = self.in_fifo)

        self.bus_multiplexer = BusMultiplexer()
        self.pins = Signal(14)
    def elaborate(self, platform):
        m = Module()
        m.submodules["InBus"] = self.input_bus
        m.submodules["OutBus"] = self.output_bus
        m.submodules["MuxBus"] = self.bus_multiplexer

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
        m.d.comb += self.input_bus.mode_controller.beam_controller.count_enable.eq(self.bus_multiplexer.released)
        return m

stream = [
    [Vector_Address.X, 1000], #X, 1000
    [Vector_Address.Y, 2000], #Y, 2000
    [Vector_Address.D, 10],  #D, 50
    [Vector_Address.X, 1250], #X, 1000
    [Vector_Address.Y, 1700], #Y, 2000
    [Vector_Address.D, 11],  #D, 50
    [Vector_Address.X, 1000], #X, 1000
    [Vector_Address.Y, 2000], #Y, 2000
    [Vector_Address.D, 13],  #D, 50
    [Vector_Address.X, 1250], #X, 1000
    [Vector_Address.Y, 1700], #Y, 2000
    [Vector_Address.D, 14],  #D, 50
    [Vector_Address.X, 1100], #X, 1000
    [Vector_Address.Y, 2100], #Y, 2000
    [Vector_Address.D, 10],  #D, 50
    [Vector_Address.X, 1350], #X, 1000
    [Vector_Address.Y, 1700], #Y, 2000
    [Vector_Address.D, 11],  #D, 50
    # [Constant_Raster_Address.X, 15], #X, 1250
    # [Constant_Raster_Address.Y, 25], #Y, 2500
    # [Constant_Raster_Address.D, 12],  #D, 75
    
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
        for n in range(len(stream)*2):
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

#GlasgowPlatformRevC123().build(IOBus())