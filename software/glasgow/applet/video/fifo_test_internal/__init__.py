import logging
import asyncio
from amaranth import *

from ... import *

class FIFOTestSubtarget(Elaboratable):
    def __init__(self, pads, in_fifo, out_fifo):
        self.pads     = pads
        self.in_fifo  = in_fifo
        print(type(in_fifo))
        self.out_fifo = out_fifo
        self.datain = Signal(14)

    def elaborate(self, platform):
        m = Module()

        m.d.sync += self.datain.eq(255)

        with m.FSM():
            with m.State("READ"):
                with m.If(self.out_fifo.r_rdy):
                    m.d.sync += [
                        self.datain.eq(self.out_fifo.r_data),
                        self.out_fifo.r_en.eq(1),
                    ]
                m.next = "WRITE"
            with m.State("WRITE"):
                m.d.comb += [
                self.pads.a_t.oe.eq(1), 
                self.pads.a_t.o.eq(self.datain[0]), ## LSB
                self.pads.b_t.oe.eq(1),
                self.pads.b_t.o.eq(self.datain[1]),
                self.pads.c_t.oe.eq(1),
                self.pads.c_t.o.eq(self.datain[2]),
                self.pads.d_t.oe.eq(1),
                self.pads.d_t.o.eq(self.datain[3]),
                self.pads.e_t.oe.eq(1),
                self.pads.e_t.o.eq(self.datain[4]),
                self.pads.f_t.oe.eq(1),
                self.pads.f_t.o.eq(self.datain[5]),
                self.pads.g_t.oe.eq(1),
                self.pads.g_t.o.eq(self.datain[6]),
                self.pads.h_t.oe.eq(1),
                self.pads.h_t.o.eq(self.datain[7]),
                # self.pads.i_t.oe.eq(1),
                # self.pads.i_t.o.eq(self.datain[8]),
                # self.pads.j_t.oe.eq(1),
                # self.pads.j_t.o.eq(self.datain[9]),
                # self.pads.k_t.oe.eq(1),
                # self.pads.k_t.o.eq(self.datain[10]),
                # self.pads.l_t.oe.eq(1),
                # self.pads.l_t.o.eq(self.datain[11]),
                # self.pads.m_t.oe.eq(1),
                # self.pads.m_t.o.eq(self.datain[12]),
                # self.pads.n_t.oe.eq(1),
                # self.pads.n_t.o.eq(self.datain[13]), ## MSB
            ]

                m.next = "READ"




        return m


class FIFOTestInternalApplet(GlasgowApplet, name="fifo-test-internal"):
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
        # file = open("fifo_output.txt", "w")
        # async def read_data():
        #     print("reading")
        #     ## actually get the data from the fifo
        #     raw_data = await iface.read()
        #     data = raw_data.tolist()
        #     print(data)
        #     print("done")
            
        #     ## write output to txt file
        #     raw_length = len(raw_data)
        #     file.write("<=======================================================================================================================================>\n")
        #     file.write(f'RAW PACKET LENGTH: {raw_length}\n')
        #     file.write(", ".join([str(x) for x in data]))
        
        ## do read_data() four times (get 4 packets)
        async def write_data():
            print("writing")
            await iface.write(bytes([0xAA, 0x55]))
            print("done")

        for n in range(2000):
            await write_data()


    @classmethod
    def add_interact_arguments(cls, parser):
        pass

    async def interact(self, device, args, iface):
        pass

# -------------------------------------------------------------------------------------------------

class BoilerplateAppletTestCase(GlasgowAppletTestCase, applet=FIFOTestInternalApplet()):
    @synthesis_test
    def test_build(self):
        self.assertBuilds()