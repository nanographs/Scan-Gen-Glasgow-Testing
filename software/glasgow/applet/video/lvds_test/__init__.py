import logging
import asyncio
from amaranth import *
from amaranth.sim import Simulator
from amaranth.lib.cdc import FFSynchronizer

from ....gateware.pads import *
from ....gateware.analyzer import *


from ... import *

class LEDBlinker(Elaboratable):

    def elaborate(self, platform):
        m = Module()

        led = platform.request("led")
        half_freq = int(platform.default_clk_frequency // 2)
        timer = Signal(range(half_freq + 1))

        with m.If(timer == half_freq):
            m.d.sync += led.eq(~led)
            m.d.sync += timer.eq(0)
        with m.Else():
            m.d.sync += timer.eq(timer + 1) 
        return m


class ScanGenSubtarget(Elaboratable):
    """
    An 8-bit up counter with a fixed limit.

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
    def __init__(self,pads, in_fifo):
        self.pads = pads

        self.in_fifo = in_fifo

        self.analyzer = EventAnalyzer(in_fifo)
        self.event_source = self.analyzer.add_event_source("pin", "change",1)

        self.limit = 255

        # Ports
        self.en  = Signal()
        self.ovf = Signal()

        # State
        self.count = Signal(8)

        self.a = Signal()
        self.b = Signal()
        self.c  = Signal()
        self.d  = Signal()
        self.e  = Signal()
        self.f  = Signal()
        self.g  = Signal()
        self.h  = Signal()
        #self.p = Signal()

        self.datain = Signal()

    def elaborate(self, platform):
        m = Module()

        led = platform.request("led",0)
        led2 = platform.request("led",1)
        half_freq = int(platform.default_clk_frequency // 2)
        timer = Signal(range(half_freq + 1))

        with m.If(timer == half_freq):
            m.d.sync += led.eq(~led)
            #m.d.sync += d_clock.eq(~d_clock)
            m.d.sync += timer.eq(0)
        with m.Else():
            m.d.sync += timer.eq(timer + 1) 

        ## evaluate whether counter is at its limit
        m.d.comb += self.ovf.eq(self.count == self.limit)

        ## incrementing the counter
        with m.If(1):
            with m.If(self.ovf):
                ## if the counter is at overflow, set it to 0
                m.d.sync += self.count.eq(0)
            with m.Else():
                ## else, increment the counter by 1
                m.d.sync += self.count.eq(self.count + 1)

    ## Pins Doing Things
        pins_i = Signal.like(self.pads.p_t.i)
        pins_r = Signal.like(self.pads.p_t.i)
        m.submodules += FFSynchronizer(self.pads.p_t.i, pins_i)

        m.d.sync += [
        self.pads.a_t.oe.eq(1),
        self.pads.a_t.o.eq(led),
        self.datain.eq(self.pads.p_t.i),
        led2.eq(~self.datain)
        ]

        m.d.comb += [
        self.event_source.data.eq(pins_i),
        self.event_source.trigger.eq(pins_i != pins_r)
        ]
            

        return m

class AnalyzerInterface:
    def __init__(self, interface, event_sources):
        self.lower   = interface
        self.decoder = TraceDecoder(event_sources)

    async def read(self):
        self.decoder.process(await self.lower.read())
        return self.decoder.flush()

class LVDSTestApplet(GlasgowApplet, name="lvds-test"):
    logger = logging.getLogger(__name__)
    help = "boilerplate applet"
    preview = True
    description = """
    /|/|/|/|/|/|/|/|
    /|/|/|/|/|/|/|/|
    /|/|/|/|/|/|/|/|
    /|/|/|/|/|/|/|/|
    """

    # An example of the boilerplate code required to implement a minimal Glasgow applet.
    #
    # The only things necessary for an applet are:
    #   * a subtarget class,
    #   * an applet class,
    #   * the `build` and `run` methods of the applet class.
    #
    # Everything else can be omitted and would be replaced by a placeholder implementation that does
    # nothing. Similarly, there is no requirement to use IN or OUT FIFOs, or any pins at all.
#
    __pins = ("a", "b", "c", "d", "e","f","g","h",
    "i","j","k","l","m","n","o","p")

    @classmethod
    def add_build_arguments(cls, parser, access):
        super().add_build_arguments(parser, access)
        for pin in cls.__pins:
            access.add_pin_argument(parser, pin, default=True)


    def build(self, target, args):
        self.mux_interface = iface = target.multiplexer.claim_interface(self, args)
        #iface.add_subtarget(LEDBlinker())
        subtarget = iface.add_subtarget(ScanGenSubtarget(
            pads=iface.get_pads(args, pins=self.__pins),
            in_fifo=iface.get_in_fifo(),
        ))

        self._event_sources = subtarget.analyzer.event_sources
    
    @classmethod
    def add_run_arguments(cls, parser, access):
        super().add_run_arguments(parser, access)

    async def run(self, device, args):
        iface =  await device.demultiplexer.claim_interface(self, self.mux_interface, args)
        return AnalyzerInterface(iface, self._event_sources)

    @classmethod
    def add_interact_arguments(cls, parser):
        pass

    async def interact(self, device, args, iface):
        print(self._event_sources)

# -------------------------------------------------------------------------------------------------

class ScanGenAppletTestCase(GlasgowAppletTestCase, applet=LVDSTestApplet):
    @synthesis_test
    def test_build(self):
        self.assertBuilds()