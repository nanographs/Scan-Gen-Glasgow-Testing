import logging
import asyncio
from amaranth import *

from ... import *


class RampGenerator(Elaboratable):
    """
    A n-bit up counter with a fixed limit.

    Parameters
    ----------
    limit : int
        The value at which the counter overflows.

    Attributes
    ----------
    en : Signal, in
        The counter is incremented if ``en`` is asserted, and retains
        its value otherwise.
    ovf : Signal, out
        ``ovf`` is asserted when the counter reaches its limit.
    """
    def __init__(self, limit: int):
        ## Number of unique steps to count up to
        self.limit = limit

        # Ports
        self.en  = Signal()
        self.ovf = Signal()

        # State
        self.count = Signal(limit.bit_length())

    def elaborate(self, platform):
        m = Module()
        ## evaluate whether counter is at its limit
        m.d.comb += self.ovf.eq(self.count == self.limit)

        ## incrementing the counter
        with m.If(self.en):
            with m.If(self.ovf):
                ## if the counter is at overflow, set it to 0
                m.d.sync += self.count.eq(0)
            with m.Else():
                ## else, increment the counter by 1
                m.d.sync += self.count.eq(self.count + 1)

        return m
    def ports(self):
        return[self.module.en, self.module.ovf, self.module.count]



class FIFOTestSubtarget(Elaboratable):
    def __init__(self, pads, in_fifo, out_fifo):
        self.pads     = pads
        self.in_fifo  = in_fifo
        self.out_fifo = out_fifo
        self.datain = Signal(8)

    def elaborate(self, platform):
        m = Module()
        m.submodules.ramp = ramp = RampGenerator(255)
        ## enable ramp
        m.d.comb += ramp.en.eq(1)

        ## output pins
        m.d.comb += [
            self.pads.a_t.oe.eq(1),
            self.pads.a_t.o.eq(ramp.count[0]),
            self.pads.b_t.oe.eq(1),
            self.pads.b_t.o.eq(ramp.count[1]),
            self.pads.c_t.oe.eq(1),
            self.pads.c_t.o.eq(ramp.count[2]),
            self.pads.d_t.oe.eq(1),
            self.pads.d_t.o.eq(ramp.count[3]),
            self.pads.e_t.oe.eq(1),
            self.pads.e_t.o.eq(ramp.count[4]),
            self.pads.f_t.oe.eq(1),
            self.pads.f_t.o.eq(ramp.count[5]),
            self.pads.g_t.oe.eq(1),
            self.pads.g_t.o.eq(ramp.count[6]),
            self.pads.h_t.oe.eq(1),
            self.pads.h_t.o.eq(ramp.count[7]),
                ]

        ## input pins
        m.d.comb += [
            self.datain[0].eq(self.pads.i_t.i),
            self.datain[1].eq(self.pads.j_t.i),
            self.datain[2].eq(self.pads.k_t.i),
            self.datain[3].eq(self.pads.l_t.i),
            self.datain[4].eq(self.pads.m_t.i),
            self.datain[5].eq(self.pads.n_t.i),
            self.datain[6].eq(self.pads.o_t.i),
            self.datain[7].eq(self.pads.p_t.i),
        ]

        with m.If(self.in_fifo.w_rdy):
            m.d.comb += [
                self.in_fifo.din.eq(self.datain),
                self.in_fifo.w_en.eq(1)
            ]
        return m


class FIFOTestApplet(GlasgowApplet, name="fifo-test"):
    logger = logging.getLogger(__name__)
    help = "boilerplate applet"
    preview = True
    description = """
    An example of the boilerplate code required to implement a minimal Glasgow applet.

    The only things necessary for an applet are:
        * a subtarget class,
        * an applet class,
        * the `build` and `run` methods of the applet class.

    Everything else can be omitted and would be replaced by a placeholder implementation that does
    nothing. Similarly, there is no requirement to use IN or OUT FIFOs, or any pins at all.
    """

    __pins = ("a", "b", "c", "d", "e","f","g","h","i","j","k","l","m","n","o","p")

    @classmethod
    def add_build_arguments(cls, parser, access):
        super().add_build_arguments(parser, access)

        for pin in cls.__pins:
            access.add_pin_argument(parser, pin, default=True)

    def build(self, target, args):
        self.mux_interface = iface = target.multiplexer.claim_interface(self, args)
        iface.add_subtarget(FIFOTestSubtarget(
            pads=iface.get_pads(args, pins=self.__pins),
            in_fifo=iface.get_in_fifo(),
            out_fifo=iface.get_out_fifo(),
        ))

    @classmethod
    def add_run_arguments(cls, parser, access):
        super().add_run_arguments(parser, access)

    async def run(self, device, args):
        iface = await device.demultiplexer.claim_interface(self, self.mux_interface, args)
        data = await iface.read()
        print(data.tolist())

    @classmethod
    def add_interact_arguments(cls, parser):
        pass

    async def interact(self, device, args, iface):
        pass

# -------------------------------------------------------------------------------------------------

class BoilerplateAppletTestCase(GlasgowAppletTestCase, applet=FIFOTestApplet()):
    @synthesis_test
    def test_build(self):
        self.assertBuilds()
