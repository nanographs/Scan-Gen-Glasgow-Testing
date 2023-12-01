import os, sys
import logging
import asyncio
from amaranth import *
from amaranth.build import *
from amaranth.sim import Simulator

from addresses import *

sys.path.append("/Users/isabelburgos/Scan-Gen-Glasgow-Testing/software")
from glasgow import *
from glasgow.access.simulation import SimulationMultiplexerInterface, SimulationDemultiplexerInterface
from glasgow.applet.video.scan_gen import ScanGenApplet, IOBusSubtarget
from glasgow.applet.video.scan_gen.scan_gen_components.main_iobus import IOBus
from glasgow.applet.video.scan_gen.scan_gen_components.test_streams import *
from glasgow.device.hardware import GlasgowHardwareDevice
from glasgow.support.bits import bits

#from test_streams import _fifo_write_data_address, basic_vector_stream
from test_streams import _fifo_write_vector_point, test_vector_points, _fifo_read





sim_iface = SimulationMultiplexerInterface(ScanGenApplet)
sim_iface.in_fifo = sim_iface.get_in_fifo()
sim_iface.out_fifo = sim_iface.get_out_fifo()
sim_app_iface = SimulationDemultiplexerInterface(GlasgowHardwareDevice, ScanGenApplet, sim_iface)


def write_vector_point(n, iface):
    x, y, d = n
    x1, x2 = get_two_bytes(x)
    yield from iface.write(bits(x2))
    yield from iface.write(bits(x1))
    y1, y2 = get_two_bytes(y)
    yield from iface.write(bits(y2))
    yield from iface.write(bits(y1))
    d1, d2 = get_two_bytes(d)
    yield from iface.write(bits(d2))
    yield from iface.write(bits(d1))

    

def sim_iobus():
    dut = IOBus(sim_iface.in_fifo, sim_iface.out_fifo, is_simulation = True)
    def bench():
        for i in range(10):
            for n in test_vector_points:
                x, y, d = n
                yield from write_vector_point(n, sim_app_iface)
        for i in range(10):
            yield
        for i in range(9):
            output = yield from sim_app_iface.read(18)
            print(output)


    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("applet_sim.vcd"):
        sim.run()

if __name__ == "__main__":
    sim_iobus()