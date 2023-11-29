import amaranth
from amaranth import *
from amaranth.sim import Simulator

class LineDrawer(Elaboratable):
    def __init__(self):
        self.x0 = Signal(8)
        self.y0 = Signal(8)

        self.dx = Signal(8)
        self.dy = Signal(8)

        self.sx = Signal()
        self.sy = Signal()

        #print(self.sx.shape())

        self.x1 = Signal(8)
        self.y1 = Signal(8)

        self.err = Signal(8)
        self.e2 = Signal(8)

    def elaborate(self, platform):
        m = Module()

        m.d.comb += self.dx.eq(abs(self.x1 - self.x0))
        m.d.comb += self.dy.eq(abs(self.y1 - self.y0))

        with m.If(self.x0 < self.x1):
            m.d.comb += self.sx.eq(1)


        with m.If(self.y0 < self.y1):
            m.d.comb += self.sy.eq(1)

        m.d.sync += self.err.eq(self.dx + self.dy)
        m.d.sync += self.e2.eq(2*self.err)

        with m.If(~(self.x0 == self.x1) & ~(self.y0 == self.y1)):
            with m.If(self.e2 >= self.dy):
                m.d.sync += self.err.eq(self.err + self.dy)
                with m.If(self.sx):
                    m.d.sync += self.x0.eq(self.x0 + 1)
                with m.Else():
                    m.d.sync += self.x0.eq(self.x0 - 1)

            with m.If(self.e2 <= self.dx):
                m.d.sync += self.err.eq(self.err + self.dy)
                with m.If(self.sy):
                    m.d.sync += self.y0.eq(self.y0 + 1)
                with m.Else():
                    m.d.sync += self.y0.eq(self.y0 - 1)

        return m


def test_drawline():
    dut = LineDrawer()
    def bench():
        yield dut.x0.eq(2)
        yield dut.y0.eq(3)
        yield dut.x1.eq(10)
        yield dut.y1.eq(11)
        for n in range(20):
            yield

    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("drawline_sim.vcd"):
        sim.run()

test_drawline()