import amaranth
from amaranth import *
from amaranth.sim import Simulator
import unittest

from bus_state_machine import ScanIOBus

class FIFO_sim(Elaboratable):
    def __init__(self):
        self.din = Signal(8)
        self.w_en = Signal()
        self.w_rdy = Signal()
        self.flush = Signal()

class FIFO_State(Elaboratable):
    def __init__(self, in_fifo, resolution_bits):
        self.in_fifo  = in_fifo

        self.resolution_bits = resolution_bits ## 9x9 = 512, etc.

        self.datain = Signal(14)

    def elaborate(self, platform):
        m = Module()
        m.submodules.scan_bus = scan_bus = ScanIOBus(self.resolution_bits)

        with m.FSM() as fsm:
            with m.State("BUS_READ"):
                m.d.sync += [
                    self.datain.eq(scan_bus.x_data)
                ]
                m.next = "BUS_FIFO_IMG"

            with m.State("BUS_FIFO_IMG"):
                with m.If(self.in_fifo.w_rdy):
                    with m.If(self.datain <= 1): #restrict image data to 2-255, save 0-1 for frame/line sync
                        m.d.comb += [
                            self.in_fifo.din.eq(2),
                            self.in_fifo.w_en.eq(1),
                        ]
                    with m.Else():
                        m.d.comb += [
                            self.in_fifo.din.eq(self.datain[0:8]),
                            self.in_fifo.w_en.eq(1),
                        ]
                m.next = "BUS_FIFO_SYNC"

            with m.State("BUS_FIFO_SYNC"):
                with m.If(self.in_fifo.w_rdy):
                    with m.If(scan_bus.line_sync & scan_bus.frame_sync):
                        m.d.comb += [
                            self.in_fifo.din.eq(0),
                            self.in_fifo.w_en.eq(1),
                        ]
                    with m.Elif(scan_bus.line_sync):
                        m.d.comb += [
                            self.in_fifo.din.eq(1),
                            self.in_fifo.w_en.eq(1),
                        ]
                m.next = "FIFO_WAIT"

            with m.State("FIFO_WAIT"):
                with m.If(self.in_fifo.w_rdy):
                    m.d.comb += [
                                scan_bus.fifo_ready.eq(1)
                            ]
                with m.Else():
                    m.d.comb += [
                                self.in_fifo.flush.eq(1)
                            ]
                m.next = "BUS_READ"
        
        return m

if __name__ == "__main__":
    sim_fifo = FIFO_sim()
    dut = FIFO_State(sim_fifo,9)# 512x512
    def bench():
        for _ in range(1024):
            yield
        yield


    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("scan_sim_fifo.vcd"):
        sim.run()