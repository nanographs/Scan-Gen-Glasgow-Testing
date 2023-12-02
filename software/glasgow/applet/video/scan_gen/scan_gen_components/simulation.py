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
from glasgow.applet.video.scan_gen import ScanGenApplet, IOBusSubtarget, ScanGenInterface
from glasgow.applet.video.scan_gen.scan_gen_components.main_iobus import IOBus
from glasgow.applet.video.scan_gen.scan_gen_components.test_streams import *
from glasgow.device.hardware import GlasgowHardwareDevice
from glasgow.device.simulation import GlasgowSimulationDevice
from glasgow.target.simulation import GlasgowSimulationTarget
from glasgow.support.bits import bits

from test_streams import *



sim_iface = SimulationMultiplexerInterface(ScanGenApplet)
sim_iface.in_fifo = sim_iface.get_in_fifo(auto_flush=False)
sim_iface.out_fifo = sim_iface.get_out_fifo()
# print(vars(ScanGenApplet))
# print(vars(GlasgowSimulationTarget))
sim_app_iface = SimulationDemultiplexerInterface(GlasgowHardwareDevice, ScanGenApplet, sim_iface)
sim_scangen_iface = ScanGenInterface(sim_app_iface,sim_app_iface.logger, sim_app_iface.device, 
                    2, is_simulation = True)


def raster_sim(n=16384):
    output = yield from sim_app_iface.read(n)
    print(sim_scangen_iface.decode_rdwell_packet(output))


def vector_sim(r):
    i = 0
    while i < r:
        for n in test_vector_points:
            x, y, d = n
            i += 6
            #yield from write_vector_point(n, sim_app_iface)
            yield from sim_scangen_iface.sim_write_vpoint(n)



def sim_iobus():
    scan_mode = Signal(2)
    dut = IOBus(sim_iface.in_fifo, sim_iface.out_fifo, scan_mode, is_simulation = True)
    def bench():
        # yield scan_mode.eq(ScanMode.Raster)
        # yield from raster_sim(500)
        # # yield scan_mode.eq(2) ## not defined, so just do nothing/pause
        # # for n in range(10):
        # #     yield
        #yield scan_mode.eq(3)
        #yield
        try:
            yield from vector_sim(512)
            output = yield from sim_app_iface.read(512)
            print(sim_scangen_iface.decode_vpoint_packet(output))
        except AssertionError:
            yield
        
    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("applet_sim.vcd"):
        sim.run()

if __name__ == "__main__":
    sim_iobus()