import amaranth
from amaranth import *
from amaranth.sim import Simulator

class LineDrawer(Elaboratable):
    def __init__(self):
        self.x0 = Signal(8)
        self.y0 = Signal(8)

        self.x1 = Signal(8)
        self.y1 = Signal(8)

        self.x = Signal(8)
        self.y = Signal(8)

        self.dx = Signal(range(-255,255))
        print(self.dx.shape())
        self.dy = Signal(range(-255,255))
        print(self.dy.shape())

        self.err = Signal(range(-255,255))

        self.movx = Signal()
        self.movy = Signal()

        self.right = Signal()
        self.down = Signal()

    def elaborate(self, platform):
        m = Module()

        m.d.comb += self.movx.eq(2*self.err >= self.dy)
        m.d.comb += self.movy.eq(2*self.err <= self.dx)
        
        m.d.comb += self.right.eq(self.x0 < self.x1)
        m.d.comb += self.down.eq(self.y0 < self.y1)

        m.d.comb += self.dx.eq(abs(self.x1 - self.x0))
        m.d.comb += self.dy.eq(-abs(self.y1 - self.y0))

        with m.FSM() as fsm: 
            with m.State("Start"):
                m.d.sync += self.x.eq(self.x0)
                m.d.sync += self.y.eq(self.y0)
                m.next = "Draw"
            with m.State("Draw"):
                with m.If((self.movx) & (self.movy)):
                    m.d.sync += self.err.eq(self.err + self.dx + self.dy)
                    with m.If(self.right):
                        m.d.sync += self.x.eq(self.x + 1)
                    with m.Else():
                        m.d.sync += self.x.eq(self.x - 1)
                    with m.If(self.down):
                        m.d.sync += self.y.eq(self.y + 1)
                    with m.Else():
                        m.d.sync += self.y.eq(self.y - 1)
                with m.If((self.movx) & ~(self.movy)):
                    m.d.sync += self.err.eq(self.err + self.dy)
                    with m.If(self.right):
                        m.d.sync += self.x.eq(self.x0 + 1)
                    with m.Else():
                        m.d.sync += self.x.eq(self.x0 - 1)
                with m.If(~(self.movx) & (self.movy)):
                    m.d.sync += self.err.eq(self.err + self.dx)
                    with m.If(self.down):
                        m.d.sync += self.y.eq(self.y + 1)
                    with m.Else():
                        m.d.sync += self.y.eq(self.y - 1)    
        return m


def test_drawline():
    dut = LineDrawer()
    def bench():
        yield dut.x0.eq(1)
        yield dut.y0.eq(1)
        yield dut.x1.eq(10)
        yield dut.y1.eq(50)
        for n in range(20):
            yield

    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("lineinterp_sim.vcd"):
        sim.run()

test_drawline()