import amaranth
from amaranth import *
from amaranth.sim import Simulator
from amaranth.lib import data, enum
import os, sys

if "glasgow" in __name__: ## running as applet
    from ..scan_gen_components.output_bus import OutputBus
    from ..scan_gen_components.multimode_input import InputBus
    from ..scan_gen_components.data_latch_bus import BusMultiplexer
    from ..scan_gen_components.addresses import *
else:
    from multimode_input import InputBus
    from output_bus import OutputBus
    from data_latch_bus import BusMultiplexer
    from addresses import *
    sys.path.append("/Users/isabelburgos/Scan-Gen-Glasgow-Testing/software")
    from glasgow import *
    from glasgow.access.simulation import SimulationMultiplexerInterface, SimulationDemultiplexerInterface


# sim_iface = SimulationMultiplexerInterface()

class IOBus(Elaboratable):
    def __init__(self, in_fifo, out_fifo, is_simulation):
        self.is_simulation = is_simulation
        
        self.out_fifo = out_fifo
        self.in_fifo = in_fifo
        self.input_bus = InputBus(self.out_fifo)
        self.output_bus = OutputBus(self.in_fifo)

        self.bus_multiplexer = BusMultiplexer()
        self.pins = Signal(14)

        self.x_latch = Signal()
        self.x_enable = Signal()
        self.y_latch = Signal()
        self.y_enable = Signal()
        self.a_latch = Signal()
        self.a_enable = Signal()

        self.a_clock = Signal()
        self.d_clock = Signal()
    def elaborate(self, platform):
        m = Module()
        m.submodules["InBus"] = self.input_bus
        m.submodules["OutBus"] = self.output_bus
        m.submodules["MuxBus"] = self.bus_multiplexer

        m.d.comb += self.x_latch.eq(self.bus_multiplexer.x_dac.latch.le)
        m.d.comb += self.x_enable.eq(self.bus_multiplexer.x_dac.latch.oe)
        m.d.comb += self.y_latch.eq(self.bus_multiplexer.y_dac.latch.le)
        m.d.comb += self.y_enable.eq(self.bus_multiplexer.y_dac.latch.oe)
        m.d.comb += self.a_latch.eq(self.bus_multiplexer.a_adc.latch.le)
        m.d.comb += self.a_enable.eq(self.bus_multiplexer.a_adc.latch.oe)

        m.d.comb += self.a_clock.eq(self.bus_multiplexer.sample_clock.clock)
        m.d.comb += self.d_clock.eq(self.bus_multiplexer.sample_clock.clock)
        

        m.d.sync += self.bus_multiplexer.sampling.eq(self.input_bus.mode_controller.beam_controller.dwelling)
        #m.d.sync += self.bus_multiplexer.sampling.eq(0)
        with m.If(self.bus_multiplexer.is_x):
            m.d.comb += self.pins.eq(self.input_bus.mode_controller.beam_controller.x_position)
        with m.If(self.bus_multiplexer.is_y):
            m.d.comb += self.pins.eq(self.input_bus.mode_controller.beam_controller.y_position)
        with m.If(self.bus_multiplexer.is_a):
            if self.is_simulation:
                m.d.comb += self.output_bus.video_sink.pixel_in.eq(self.input_bus.mode_controller.beam_controller.dwell_time)
            else:
                m.d.comb += self.output_bus.video_sink.pixel_in.eq(self.pins)
            # Loopback
        m.d.comb += self.output_bus.video_sink.dwelling.eq(self.input_bus.mode_controller.beam_controller.dwelling)
        m.d.comb += self.output_bus.video_sink.dwell_time_averager.start_new_average.eq(self.input_bus.mode_controller.beam_controller.end_of_dwell)
        #m.d.comb += self.output_bus.strobe.eq(self.bus_multiplexer.a_adc.released)
        m.d.comb += self.output_bus.strobe.eq(1)
        m.d.comb += self.input_bus.mode_controller.beam_controller.count_enable.eq(1)

        m.d.comb += self.output_bus.in_fifo.w_data.eq(self.input_bus.input_data)
        return m







    
## see access.simulation.demultiplexer -> SimulationDemultiplexer
def _fifo_write(fifo, data):
    print(fifo)
    assert (yield fifo.w_rdy)
    yield fifo.w_data.eq(data)
    yield fifo.w_en.eq(1)
    yield
    yield fifo.w_en.eq(0)
    yield

def _fifo_write_scan_data(fifo, address, data):
        bytes_data = Const(data, unsigned(16))
        print("address:", address)
        yield from _fifo_write(fifo, address)
        print("data 1:", bytes_data[0:7])
        yield from _fifo_write(fifo, bytes_data[0:7])
        print("data 2:", bytes_data[7:15])
        yield from _fifo_write(fifo, bytes_data[7:15])

def sim_iobus():
    dut = IOBus()
    def bench():
        for n in stream:
            address, data = n
            yield from _fifo_write_scan_data(dut.in_fifo, address, data)
            
            # yield dut.input_bus.in_fifo.w_en.eq(1)
            # yield dut.input_bus.in_fifo.w_data.eq(address)

        #     yield
        #     

        #     yield dut.input_bus.in_fifo.w_en.eq(1)
        #     yield dut.input_bus.in_fifo.w_data.eq(bytes_data[0:7])
        #     yield
        #     

        #     yield dut.input_bus.in_fifo.w_en.eq(1)
        #     yield dut.input_bus.in_fifo.w_data.eq(bytes_data[7:15])
        #     yield
        # for n in range(len(stream)*2):
        #     yield
    
    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("iobus_sim.vcd"):
        sim.run()

#sim_inputbus()
#sim_outputbus()
#if __name__ == "__main__":
    #sim_iobus()
#test_twobyteoutbox()
#test_beamcontroller()

#GlasgowPlatformRevC123().build(IOBus())