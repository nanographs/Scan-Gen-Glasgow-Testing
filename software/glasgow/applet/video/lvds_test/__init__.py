import logging
import asyncio
from amaranth import *
from amaranth.sim import Simulator

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
    def __init__(self,pads):
        self.pads = pads

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

    def elaborate(self, platform):
        m = Module()

        ## C0-7
        x_latch = platform.request("X_LATCH")
        #x_enable = platform.request("X_ENABLE")
        # y_latch = platform.request("Y_LATCH")
        #y_enable = platform.request("Y_ENABLE")
        # a_latch = platform.request("A_LATCH")
        # a_enable = platform.request("A_ENABLE")
        #d_clock = platform.request("D_CLOCK")
        #a_clock = platform.request("A_CLOCK")
        # v_ok = platform.request("port_b",7)
        #data = platform.request("port_a",0)

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





        self.dataout = Signal(14)

        self.UpCount_limit = 16383
        self.DownCount_limit = 16383

        # Ports
        self.UpCount_ovf = Signal()
        self.DownCount_ovf = Signal()

        # State
        self.UpCount = Signal(14)
        self.DownCount = Signal(14)

## Countes
    # Ovf Monitors
        m.d.comb += self.UpCount_ovf.eq(self.UpCount == self.UpCount_limit)
        m.d.comb += self.DownCount_ovf.eq(self.DownCount == self.DownCount_limit)
    

        dac_increment = Signal()

        # Up Count
        with m.If(dac_increment):
            with m.If(self.UpCount_ovf):
                ## if the counter is at overflow, set it to 0
                m.d.sync += self.UpCount.eq(0)
            with m.Else():
                ## else, increment the counter by 1
                m.d.sync += self.UpCount.eq(self.UpCount + 1)

        # Down Count
        with m.If(1):
            with m.If(self.DownCount_ovf):
                ## if the counter is at overflow, set it to 0
                m.d.sync += self.DownCount.eq(0)
            with m.Else():
                ## else, increment the counter by 1
                m.d.sync += self.DownCount.eq(self.DownCount + 1)



## Pins Doing Things

        

        # X Data
        # with m.If((self.MinDwelCounter >= 1)|(self.MinDwelCounter <= 3)):
            m.d.sync += self.dataout.eq(self.UpCount)


        # X Data Latch Permant
        m.d.comb += x_latch.eq(1)
        



    

        dac_freqency = int(24)
        dac_timer = Signal(range(dac_freqency + 1))

        with m.If(dac_timer == dac_freqency):
            #m.d.sync += d_clock.eq(~d_clock)
            m.d.sync += dac_timer.eq(0)
            m.d.sync += dac_increment.eq(1)
        
        with m.Else():
            m.d.sync += dac_timer.eq(dac_timer + 1)
            m.d.sync += dac_increment.eq(0)




            m.d.sync += [
            self.pads.a_t.oe.eq(self.pads.p_t.i),
            self.pads.a_t.o.eq(self.dataout[0]),
            self.pads.b_t.oe.eq(self.pads.p_t.i),
            self.pads.b_t.o.eq(self.dataout[1]),
            self.pads.c_t.oe.eq(self.pads.p_t.i),
            self.pads.c_t.o.eq(self.dataout[2]),
            self.pads.d_t.oe.eq(self.pads.p_t.i),
            self.pads.d_t.o.eq(self.dataout[3]),
            self.pads.e_t.oe.eq(self.pads.p_t.i),
            self.pads.e_t.o.eq(self.dataout[4]),
            self.pads.f_t.oe.eq(self.pads.p_t.i),
            self.pads.f_t.o.eq(self.dataout[5]),
            self.pads.g_t.oe.eq(self.pads.p_t.i),
            self.pads.g_t.o.eq(self.dataout[6]),
            self.pads.h_t.oe.eq(self.pads.p_t.i),
            self.pads.h_t.o.eq(self.dataout[7]),
            self.pads.i_t.oe.eq(self.pads.p_t.i),
            self.pads.i_t.o.eq(self.dataout[8]),
            self.pads.j_t.oe.eq(self.pads.p_t.i),
            self.pads.j_t.o.eq(self.dataout[9]),
            self.pads.k_t.oe.eq(self.pads.p_t.i),
            self.pads.k_t.o.eq(self.dataout[10]),
            self.pads.l_t.oe.eq(self.pads.p_t.i),
            self.pads.l_t.o.eq(self.dataout[11]),
            self.pads.m_t.oe.eq(self.pads.p_t.i),
            self.pads.m_t.o.eq(self.dataout[12]),
            self.pads.n_t.oe.eq(self.pads.p_t.i),
            self.pads.n_t.o.eq(self.dataout[13]),


            self.pads.i_t.oe.eq(1),
            self.pads.i_t.o.eq(dac_increment),


            ]

            m.d.sync += [  
            led2.eq(self.pads.p_t.i)
            ]
            



        return m

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
        iface.add_subtarget(ScanGenSubtarget(
            pads=iface.get_pads(args, pins=self.__pins)
        ))
    
    @classmethod
    def add_run_arguments(cls, parser, access):
        super().add_run_arguments(parser, access)

    async def run(self, device, args):
        return await device.demultiplexer.claim_interface(self, self.mux_interface, args)

    @classmethod
    def add_interact_arguments(cls, parser):
        pass

    async def interact(self, device, args, iface):
        pass

# -------------------------------------------------------------------------------------------------

class ScanGenAppletTestCase(GlasgowAppletTestCase, applet=LVDSTestApplet):
    @synthesis_test
    def test_build(self):
        self.assertBuilds()