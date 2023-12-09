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
from glasgow.applet.video.scan_gen.output_formats.even_newer_gui import run_gui
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
                    2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, is_simulation = True)


def raster_sim(n=16384, eight_bit_output=False):
    output = yield from sim_app_iface.read(n)
    if eight_bit_output:
        print(list(output))
    else:
        print(sim_scangen_iface.decode_rdwell_packet(output))
    


def vector_sim(r):
    i = 0
    while i < r:
        for n in short_test_vector_points:
            x, y, d = n
            i += 6
            #yield from write_vector_point(n, sim_app_iface)
            yield from sim_scangen_iface.sim_write_vpoint(n)

def raster_pattern_sim():
    pattern = test_raster_pattern_checkerboard(5,5)
    print(pattern)
    yield scan_mode.eq(ScanMode.RasterPattern)
    for n in pattern:
        yield from sim_scangen_iface.sim_write_2bytes(n)
    
    for n in range(1500):
        yield


def sim_iobus():
    scan_mode = Signal(2)
    x_full_resolution_b1 = Signal(8)
    x_full_resolution_b2 = Signal(8)
    y_full_resolution_b1 = Signal(8)
    y_full_resolution_b2 = Signal(8)
    x_upper_limit_b1 = Signal(8)
    x_upper_limit_b2 = Signal(8)
    x_lower_limit_b1 = Signal(8)
    x_lower_limit_b2 = Signal(8)
    y_upper_limit_b1 = Signal(8)
    y_upper_limit_b2 = Signal(8)
    y_lower_limit_b1 = Signal(8)
    y_lower_limit_b2 = Signal(8)
    eight_bit_output = Signal()
    do_frame_sync = Signal()
    do_line_sync = Signal()
    const_dwell_time = Signal()

    dut = IOBus(sim_iface.in_fifo, sim_iface.out_fifo, scan_mode, 
    x_full_resolution_b1, x_full_resolution_b2,
    y_full_resolution_b1, x_full_resolution_b2, 
    x_upper_limit_b1, x_upper_limit_b2,
    x_lower_limit_b1, x_lower_limit_b2,
    y_upper_limit_b1, y_upper_limit_b2,
    y_lower_limit_b1, y_lower_limit_b2,
    eight_bit_output, do_frame_sync, do_line_sync,
    const_dwell_time,
    is_simulation = True,
    test_mode = "data loopback"
    )
    def bench():

        # for n in range(1000):
        #     yield
        b1, b2 = get_two_bytes(4)
        b1 = int(bits(b1))
        b2 = int(bits(b2))

        
        
        yield x_full_resolution_b1.eq(b1)
        yield x_full_resolution_b2.eq(b2)
        yield y_full_resolution_b1.eq(b1)
        yield y_full_resolution_b2.eq(b2)

        yield scan_mode.eq(ScanMode.Vector)
        yield from vector_sim(10)
        for n in range(100):
            yield

        # # yield x_lower_limit_b1.eq(0)
        # # yield x_lower_limit_b2.eq(1)
        # # yield y_lower_limit_b1.eq(0)
        # # yield y_lower_limit_b2.eq(1)

        # # b1, b2 = get_two_bytes(6)
        # # b1 = int(bits(b1))
        # # b2 = int(bits(b2))

        # # yield x_upper_limit_b1.eq(b1)
        # # yield x_upper_limit_b2.eq(b2)
        # # yield y_upper_limit_b1.eq(b1)
        # # yield y_upper_limit_b2.eq(b2)

        # yield eight_bit_output.eq(0)
        # yield

        # for n in range(2000):
        #     yield
        # yield from raster_sim(1024, True)
        # for n in range(1000):
        #     yield
        #yield from raster_sim(500)

        # yield from raster_sim(500)
        # # yield scan_mode.eq(2) ## not defined, so just do nothing/pause
        # # for n in range(10):
        # #     yield
        #yield scan_mode.eq(3)
        #yield
        # try:
        #     yield from vector_sim(512)
        #     output = yield from sim_app_iface.read(512)
        #     print(sim_scangen_iface.decode_vpoint_packet(output))
        # except AssertionError:
        #     yield
        
    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("applet_sim.vcd"):
        sim.run()

if __name__ == "__main__":
    sim_iobus()
    #run_gui(sim_scangen_iface)