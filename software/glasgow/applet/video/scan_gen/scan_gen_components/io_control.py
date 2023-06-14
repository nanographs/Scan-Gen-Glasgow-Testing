import amaranth
from amaranth import *
from amaranth.sim import Simulator
from bus_state_machine import ScanIOBus


BUS_WRITE_X = 0x01
BUS_WRITE_Y = 0x02
BUS_READ = 0x03
BUS_FIFO = 0x04

class IO_Control(Elaboratable):
    def __init__(self, resolution_bits):
        self.resolution_bits = resolution_bits

        self.a = Signal()
        self.b = Signal()
        self.c = Signal()
        self.d = Signal()
        self.e = Signal()
        self.f = Signal()
        self.g = Signal()
        self.h = Signal()
        self.i = Signal()
        self.j = Signal()
        self.k = Signal()
        self.l = Signal()
        self.m = Signal()
        self.n = Signal()

        self.datain = Signal(14)
        self.x_data = Signal(14)
        self.y_data = Signal(14)
    def elaborate(self, platform):
        m = Module()
        m.submodules.scan_bus = scan_bus = ScanIOBus(self.resolution_bits)

        m.d.sync += [
            self.datain.eq(255),    
            self.x_data.eq(scan_bus.x_data),
            self.y_data.eq(scan_bus.y_data),
        ]

        with m.If(scan_bus.bus_state == BUS_WRITE_X):
            m.d.comb += [
                self.a.eq(self.x_data[13]),
                self.b.eq(self.x_data[12]),
                self.c.eq(self.x_data[11]),
                self.d.eq(self.x_data[10]),
                self.e.eq(self.x_data[9]),
                self.f.eq(self.x_data[8]),
                self.g.eq(self.x_data[7]),
                self.h.eq(self.x_data[6]),
                self.i.eq(self.x_data[5]),
                self.j.eq(self.x_data[4]),
                self.k.eq(self.x_data[3]),
                self.l.eq(self.x_data[2]),
                self.m.eq(self.x_data[1]),
                self.n.eq(self.x_data[0])
            ]
        
        with m.If(scan_bus.bus_state == BUS_WRITE_Y):
            m.d.comb += [
                self.a.eq(self.y_data[13]),
                self.b.eq(self.y_data[12]),
                self.c.eq(self.y_data[11]),
                self.d.eq(self.y_data[10]),
                self.e.eq(self.y_data[9]),
                self.f.eq(self.y_data[8]),
                self.g.eq(self.y_data[7]),
                self.h.eq(self.y_data[6]),
                self.i.eq(self.y_data[5]),
                self.j.eq(self.y_data[4]),
                self.k.eq(self.y_data[3]),
                self.l.eq(self.y_data[2]),
                self.m.eq(self.y_data[1]),
                self.n.eq(self.y_data[0])
            ]
        
        with m.If(scan_bus.bus_state == BUS_READ):
            m.d.comb += [
                self.a.eq(self.datain[0]),
                self.b.eq(self.datain[1]),
                self.c.eq(self.datain[2]),
                self.d.eq(self.datain[3]),
                self.e.eq(self.datain[4]),
                self.f.eq(self.datain[5]),
                self.g.eq(self.datain[6]),
                self.h.eq(self.datain[7]),
            ]
            

        return m
    def ports(self):
        return [self.a, self.b, self.c, self.d, self.e, self.f, self.g,
        self.h, self.i, self,j, self.k, self.l, self.m, self.n]

if __name__ == "__main__":
    dut = IO_Control(4) # 16 x 16
    def bench():
        for _ in range(1024):
            yield
        yield


    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("scan_sim_IO.vcd"):
        sim.run()