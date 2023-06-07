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
        self.datain = Signal(16)

    def elaborate(self, platform):
        m = Module()



        y_latch = platform.request("Y_LATCH")
        y_enable = platform.request("Y_ENABLE")
        a_latch = platform.request("A_LATCH")
        a_enable = platform.request("A_ENABLE")

        m.submodules.ramp = ramp = RampGenerator(65535)
        m.d.comb += y_enable.eq(0)


       

     



        with m.FSM() as fsm:
            with m.State("Y_WRITE"):
                ## output pins
                m.d.comb += [
                    ## enable ramp
                    ramp.en.eq(1),
                    #Cat(pin.oe for pin in pins).eq(1),
                    #Cat(pin.o  for pin in pins).eq(ramp.count),
                    #]
                    a_enable.eq(1),

                    self.pads.a_t.oe.eq(1),
                    self.pads.b_t.oe.eq(1),
                    self.pads.a_t.o.eq(ramp.count[0]),
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
                    self.pads.i_t.oe.eq(1),
                    self.pads.i_t.o.eq(ramp.count[8]),
                    self.pads.j_t.oe.eq(1),
                    self.pads.j_t.o.eq(ramp.count[9]),
                    self.pads.k_t.oe.eq(1),
                    self.pads.k_t.o.eq(ramp.count[10]),
                    self.pads.l_t.oe.eq(1),
                    self.pads.l_t.o.eq(ramp.count[11]),
                    self.pads.m_t.oe.eq(1),
                    self.pads.m_t.o.eq(ramp.count[12]),
                    self.pads.n_t.oe.eq(1),
                    self.pads.n_t.o.eq(ramp.count[13]),
                    self.pads.o_t.oe.eq(1),
                    self.pads.o_t.o.eq(ramp.count[14]),
                    self.pads.p_t.oe.eq(1),
                    self.pads.p_t.o.eq(ramp.count[15]),
                    ]
                m.next = "Y_LATCH_ON"


            with m.State("Y_LATCH_ON"):
                m.d.comb += [
                    ## enable ramp
                    ramp.en.eq(1),

                    y_latch.eq(1),
                    a_enable.eq(1),
                        
        
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
                    self.pads.i_t.oe.eq(1),
                    self.pads.i_t.o.eq(ramp.count[8]),
                    self.pads.j_t.oe.eq(1),
                    self.pads.j_t.o.eq(ramp.count[9]),
                    self.pads.k_t.oe.eq(1),
                    self.pads.k_t.o.eq(ramp.count[10]),
                    self.pads.l_t.oe.eq(1),
                    self.pads.l_t.o.eq(ramp.count[11]),
                    self.pads.m_t.oe.eq(1),
                    self.pads.m_t.o.eq(ramp.count[12]),
                    self.pads.n_t.oe.eq(1),
                    self.pads.n_t.o.eq(ramp.count[13]),
                    self.pads.o_t.oe.eq(1),
                    self.pads.o_t.o.eq(ramp.count[14]),
                    self.pads.p_t.oe.eq(1),
                    self.pads.p_t.o.eq(ramp.count[15]),
                ]
                m.next = "A_LATCH_ON"

                
            with m.State("A_LATCH_ON"):
                m.d.comb += [                  

                    a_latch.eq(1),
                    a_enable.eq(1),
                ]
                m.next = "A_READ"



            with m.State("A_READ"):
                ## input pins
                m.d.comb += [
                    #self.datain.eq(Cat(pin.i for pin in pins))

                    a_enable.eq(0),


                    self.datain[0].eq(self.pads.a_t.i),
                    self.datain[1].eq(self.pads.b_t.i),
                    self.datain[2].eq(self.pads.c_t.i),
                    self.datain[3].eq(self.pads.d_t.i),
                    self.datain[4].eq(self.pads.e_t.i),
                    self.datain[5].eq(self.pads.f_t.i),
                    self.datain[6].eq(self.pads.g_t.i),
                    self.datain[7].eq(self.pads.h_t.i),
                    self.datain[8].eq(self.pads.i_t.i),
                    self.datain[9].eq(self.pads.j_t.i),
                    self.datain[10].eq(self.pads.k_t.i),
                    self.datain[11].eq(self.pads.l_t.i),
                    self.datain[12].eq(self.pads.m_t.i),
                    self.datain[13].eq(self.pads.n_t.i),
                    self.datain[14].eq(self.pads.o_t.i),
                    self.datain[15].eq(self.pads.p_t.i),
                ]
                m.next = "Y_LATCH_ON"
        

                with m.If(self.in_fifo.w_rdy):
                    m.d.comb += [
                        self.in_fifo.din.eq(self.datain),
                        self.in_fifo.w_en.eq(1)
                    ]
                #with m.Else():
                #    m.d.comb += [
                #        self.in_fifo.flush.eq(1),
                #    ]
                

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
        async def read_data():
            data = await iface.read()
            print(data.tolist())
        await read_data()
        await read_data()
        await read_data()
        await read_data()

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
