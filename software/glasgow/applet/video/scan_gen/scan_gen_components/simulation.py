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

#from test_streams import _fifo_write_data_address, basic_vector_stream
from test_streams import _fifo_write_vector_point, test_vector_points, _fifo_read




sim_iface = SimulationMultiplexerInterface(ScanGenApplet)

in_fifo = sim_iface.get_in_fifo()
out_fifo = sim_iface.get_out_fifo()
    

def sim_iobus():
    dut = IOBus(out_fifo, in_fifo, is_simulation = True)
    def bench():
        # for n in basic_vector_stream:
        #     address, data = n
        #     yield from _fifo_write_data_address(dut.input_bus.out_fifo, address, data)
        for i in range(255):
            for n in test_vector_points:
                try:
                    yield from _fifo_write_vector_point(n, dut.out_fifo)
                except AssertionError:
                    yield
                try:
                    yield from _fifo_read(dut.in_fifo)
                except AssertionError:
                    yield


    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("applet_sim.vcd"):
        sim.run()

if __name__ == "__main__":
    sim_iobus()