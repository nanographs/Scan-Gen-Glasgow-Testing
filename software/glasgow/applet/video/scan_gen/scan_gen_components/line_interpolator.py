import amaranth
from amaranth import *
from amaranth.sim import Simulator

class LineDrawer(Elaboratable):
    '''
    Reference: https://projectf.io/posts/lines-and-triangles/

    x0: Signal, in
    y0: Signal, in
        Starting point of the line: (x0, y0)

    x1: Signal, in
    y1: Signal, in
        End point of the line: (x1, y1)

    x: Signal, out
    y: Signal, out
        Current point: (x, y)

    dx: Signal, internal, signed
        Total x span of the line: |(x1-x0)|
    dy: Signal, internal, signed
        Total y span of the line, inverted: -|(y1-y0)|

    err: Signal, internal, signed
        Combined error in x and y - how far off are
        x and y from x1 and y1?
    
    movx: Signal, internal, 1
        Asserted if 2*self.err >= self.dy
        Asserts that the x value needs to be incremented this cycle
    movy: Signal, internal, 1
        Asserted if 2*self.err <= self.dx
        Asserts that the y value needs to be incremented this cycle

    right: Signal, internal, 1
        True if line goes from left to right, so x value needs to be incremented +1
        True if line goes from right to left, so x value needs to be incremented -1

    up: Signal, internal, 1
        True if line goes from top to bottom, so y value needs to be incremented +1
        True if line goes from bottom to top, so y value needs to be incremented -1
              | +y
              |
    -x -------|------- +x
              |
              | -y

    ## TODO: Implement something that takes a stream of points, and draws a series of lines
    from (x0, y0) to (x1, y1) to (x2,y2), etc
    '''
    def __init__(self):
        self.x0 = Signal(8)
        self.y0 = Signal(8)

        self.x1 = Signal(8)
        self.y1 = Signal(8)

        self.x = Signal(8)
        self.y = Signal(8)

        self.dx = Signal(range(-255,255))
        self.dy = Signal(range(-255,255))

        self.err = Signal(range(-255,255))

        self.movx = Signal()
        self.movy = Signal()

        self.right = Signal()
        self.up = Signal()

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
                with m.If((self.movx) & (self.movy)): ### Increment in x and y
                    m.d.sync += self.err.eq(self.err + self.dx + self.dy)
                    with m.If(self.right):
                        m.d.sync += self.x.eq(self.x + 1)
                    with m.Else():
                        m.d.sync += self.x.eq(self.x - 1)
                    with m.If(self.up):
                        m.d.sync += self.y.eq(self.y + 1)
                    with m.Else():
                        m.d.sync += self.y.eq(self.y - 1)
                with m.If((self.movx) & ~(self.movy)): #### Increment in X only
                    m.d.sync += self.err.eq(self.err + self.dy)
                    with m.If(self.right):
                        m.d.sync += self.x.eq(self.x0 + 1)
                    with m.Else():
                        m.d.sync += self.x.eq(self.x0 - 1)
                with m.If(~(self.movx) & (self.movy)): #### Increment in Y only
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