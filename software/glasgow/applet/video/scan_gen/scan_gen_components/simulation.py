import os, sys
import logging
import asyncio
from amaranth import *
from amaranth.build import *
from amaranth.sim import Simulator

from addresses import *

sys.path.append("/Users/isabelburgos/Scan-Gen-Glasgow-Testing/software")
from glasgow import *
from glasgow.access.simulation import SimulationMultiplexerInterface, SimulationDemultiplexer
from glasgow.applet.video.scan_gen import ScanGenApplet, IOBusSubtarget
from glasgow.applet.video.scan_gen.scan_gen_components.main_iobus import IOBus
from glasgow.applet.video.scan_gen.scan_gen_components.test_streams import *
from glasgow.device.hardware import GlasgowHardwareDevice





# see access.simulation.demultiplexer -> SimulationDemultiplexer
def _fifo_write(fifo, data):
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
    print("data 1:", bytes_data[0:8])
    yield from _fifo_write(fifo, bytes_data[0:8])
    print("data 2:", bytes_data[8:15])
    yield from _fifo_write(fifo, bytes_data[8:15])


def sim_iobus():
    sim_iface = SimulationMultiplexerInterface(ScanGenApplet)

    in_fifo = sim_iface.get_in_fifo()
    out_fifo = sim_iface.get_out_fifo()

    dut = IOBus(out_fifo, in_fifo, is_simulation = True)
    def bench():
        for n in basic_vector_stream:
            address, data = n
            yield from _fifo_write_scan_data(dut.input_bus.out_fifo, address, data)

    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("applet_sim.vcd"):
        sim.run()

if __name__ == "__main__":
    sim_iobus()