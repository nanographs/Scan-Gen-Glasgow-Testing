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
#from glasgow.applet.video.scan_gen.output_formats.even_newer_gui import run_gui
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
                    2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, is_simulation = True)


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


def vector_pattern_sim(dut):
    yield dut.scan_mode.eq(ScanMode.Vector)
    yield from vector_sim(10)
    for n in range(200):
        yield

def raster_pattern_sim(dut):
    pattern = test_raster_pattern_checkerboard(5,5)
    print(pattern)
    yield dut.scan_mode.eq(ScanMode.RasterPattern)
    for n in pattern:
        yield from sim_scangen_iface.sim_write_2bytes(n)
    
    for n in range(1500):
        yield

def set_raster_params(dut, x_res=8, y_res = 8, x_lower = 0, y_lower = 0, x_upper = 0, y_upper = 0):
    b1, b2 = get_two_bytes(x_res)
    print("set x resolution:", x_res)
    b1 = int(bits(b1))
    b2 = int(bits(b2))

    yield dut.x_full_resolution_b1.eq(b1)
    yield dut.x_full_resolution_b2.eq(b2)

    b1, b2 = get_two_bytes(y_res)
    b1 = int(bits(b1))
    b2 = int(bits(b2))

    yield dut.y_full_resolution_b1.eq(b1)
    yield dut.y_full_resolution_b2.eq(b2)

    b1, b2 = get_two_bytes(x_lower)
    b1 = int(bits(b1))
    b2 = int(bits(b2))

    yield dut.x_lower_limit_b1.eq(b1)
    yield dut.x_lower_limit_b2.eq(b2)

    b1, b2 = get_two_bytes(y_lower)
    b1 = int(bits(b1))
    b2 = int(bits(b2))

    yield dut.y_lower_limit_b1.eq(b1)
    yield dut.y_lower_limit_b2.eq(b2)

    b1, b2 = get_two_bytes(x_upper)
    b1 = int(bits(b1))
    b2 = int(bits(b2))

    yield dut.x_upper_limit_b1.eq(b1)
    yield dut.x_upper_limit_b2.eq(b2)

    b1, b2 = get_two_bytes(y_upper)
    b1 = int(bits(b1))
    b2 = int(bits(b2))

    yield dut.y_upper_limit_b1.eq(b1)
    yield dut.y_upper_limit_b2.eq(b2)


    yield dut.scan_mode.eq(ScanMode.Raster)



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
    configuration = Signal()

    dut = IOBus(sim_iface.in_fifo, sim_iface.out_fifo, scan_mode, 
    x_full_resolution_b1, x_full_resolution_b2,
    y_full_resolution_b1, x_full_resolution_b2, 
    x_upper_limit_b1, x_upper_limit_b2,
    x_lower_limit_b1, x_lower_limit_b2,
    y_upper_limit_b1, y_upper_limit_b2,
    y_lower_limit_b1, y_lower_limit_b2,
    eight_bit_output, do_frame_sync, do_line_sync,
    const_dwell_time, configuration,
    is_simulation = True,
    test_mode = "data loopback", use_config_handler = True
    )
    def bench():
        # yield do_frame_sync.eq(1)
        # yield do_line_sync.eq(0)
        # yield eight_bit_output.eq(1)
        yield
        yield from set_raster_params(dut, x_res=512, y_res=512)
        yield scan_mode.eq(1)
        yield
        yield configuration.eq(1)
        yield
        for n in range(10):
            yield
        yield configuration.eq(0)
        yield
        yield from raster_sim(100, eight_bit_output = True)
        yield scan_mode.eq(0)
        for n in range(100):
            yield
        #yield from raster_sim(100, eight_bit_output = True)
        
        # yield dut.scan_mode.eq(ScanMode.Vector)
        # yield from vector_sim(16384)
        # yield from vector_pattern_sim(dut)
        # for n in range(6):
        #     data = yield from sim_app_iface.read(6)
        #     print(sim_scangen_iface.decode_vpoint_packet(data))

    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("applet_sim.vcd"):
        sim.run()

if __name__ == "__main__":
    sim_iobus()
    #run_gui(sim_scangen_iface)