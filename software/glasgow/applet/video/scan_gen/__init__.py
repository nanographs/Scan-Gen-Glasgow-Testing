import logging
import asyncio
from amaranth import *
from amaranth.sim import Simulator

from .scan_gen_components.bus_state_machine import ScanIOBus

from ... import *

BUS_WRITE_X = 0x01
BUS_WRITE_Y = 0x02
BUS_READ = 0x03
BUS_FIFO = 0x04



######################
###### DATA BUS ######
######################

class DataBusAndFIFOSubtarget(Elaboratable):
    def __init__(self, pads, in_fifo, out_fifo):
        self.pads     = pads
        self.in_fifo  = in_fifo
        self.out_fifo = out_fifo

        self.resolution_bits = 14

        self.datain = Signal(14)
        self.x_data = Signal(14)
        self.y_data = Signal(14)

    def elaborate(self, platform):
        m = Module()

        m.submodules.scan_bus = scan_bus = ScanIOBus(self.resolution_bits)

        x_latch = platform.request("X_LATCH")
        x_enable = platform.request("X_ENABLE")
        y_latch = platform.request("Y_LATCH")
        y_enable = platform.request("Y_ENABLE")
        a_latch = platform.request("A_LATCH")
        a_enable = platform.request("A_ENABLE")

        a_clock = platform.request("A_CLOCK")
        d_clock = platform.request("D_CLOCK")

        m.d.sync += [  
            self.x_data.eq(scan_bus.x_data),
            self.y_data.eq(scan_bus.y_data),
        ]


        m.d.comb += [
            x_latch.eq(scan_bus.x_latch),
            x_enable.eq(scan_bus.x_enable),
            y_latch.eq(scan_bus.y_latch),
            y_enable.eq(scan_bus.y_enable),
            a_latch.eq(scan_bus.a_latch),
            a_enable.eq(scan_bus.a_enable),
            a_clock.eq(scan_bus.a_clock),
            d_clock.eq(scan_bus.d_clock),
        ]

        with m.If(scan_bus.bus_state == BUS_WRITE_X):
            m.d.comb += [
                self.pads.a_t.oe.eq(self.pads.p_t.i),
                self.pads.a_t.o.eq(self.x_data[13]),
                self.pads.b_t.oe.eq(self.pads.p_t.i),
                self.pads.b_t.o.eq(self.x_data[12]),
                self.pads.c_t.oe.eq(self.pads.p_t.i),
                self.pads.c_t.o.eq(self.x_data[11]),
                self.pads.d_t.oe.eq(self.pads.p_t.i),
                self.pads.d_t.o.eq(self.x_data[10]),
                self.pads.e_t.oe.eq(self.pads.p_t.i),
                self.pads.e_t.o.eq(self.x_data[9]),
                self.pads.f_t.oe.eq(self.pads.p_t.i),
                self.pads.f_t.o.eq(self.x_data[8]),
                self.pads.g_t.oe.eq(self.pads.p_t.i),
                self.pads.g_t.o.eq(self.x_data[7]),
                self.pads.h_t.oe.eq(self.pads.p_t.i),
                self.pads.h_t.o.eq(self.x_data[6]),
                self.pads.i_t.oe.eq(self.pads.p_t.i),
                self.pads.i_t.o.eq(self.x_data[5]),
                self.pads.j_t.oe.eq(self.pads.p_t.i),
                self.pads.j_t.o.eq(self.x_data[4]),
                self.pads.k_t.oe.eq(self.pads.p_t.i),
                self.pads.k_t.o.eq(self.x_data[3]),
                self.pads.l_t.oe.eq(self.pads.p_t.i),
                self.pads.l_t.o.eq(self.x_data[2]),
                self.pads.m_t.oe.eq(self.pads.p_t.i),
                self.pads.m_t.o.eq(self.x_data[1]),
                self.pads.n_t.oe.eq(self.pads.p_t.i),
                self.pads.n_t.o.eq(self.x_data[0]),
            ]
        
        with m.If(scan_bus.bus_state == BUS_WRITE_Y):
            m.d.comb += [
                self.pads.a_t.oe.eq(self.pads.p_t.i),
                self.pads.a_t.o.eq(self.y_data[13]),
                self.pads.b_t.oe.eq(self.pads.p_t.i),
                self.pads.b_t.o.eq(self.y_data[12]),
                self.pads.c_t.oe.eq(self.pads.p_t.i),
                self.pads.c_t.o.eq(self.y_data[11]),
                self.pads.d_t.oe.eq(self.pads.p_t.i),
                self.pads.d_t.o.eq(self.y_data[10]),
                self.pads.e_t.oe.eq(self.pads.p_t.i),
                self.pads.e_t.o.eq(self.y_data[9]),
                self.pads.f_t.oe.eq(self.pads.p_t.i),
                self.pads.f_t.o.eq(self.y_data[8]),
                self.pads.g_t.oe.eq(self.pads.p_t.i),
                self.pads.g_t.o.eq(self.y_data[7]),
                self.pads.h_t.oe.eq(self.pads.p_t.i),
                self.pads.h_t.o.eq(self.y_data[6]),
                self.pads.i_t.oe.eq(self.pads.p_t.i),
                self.pads.i_t.o.eq(self.y_data[5]),
                self.pads.j_t.oe.eq(self.pads.p_t.i),
                self.pads.j_t.o.eq(self.y_data[4]),
                self.pads.k_t.oe.eq(self.pads.p_t.i),
                self.pads.k_t.o.eq(self.y_data[3]),
                self.pads.l_t.oe.eq(self.pads.p_t.i),
                self.pads.l_t.o.eq(self.y_data[2]),
                self.pads.m_t.oe.eq(self.pads.p_t.i),
                self.pads.m_t.o.eq(self.y_data[1]),
                self.pads.n_t.oe.eq(self.pads.p_t.i),
                self.pads.n_t.o.eq(self.y_data[0]),
            ]
        
        with m.If(scan_bus.bus_state == BUS_READ):
            m.d.sync += [
                ## LOOPBACK
                #self.datain[0].eq(self.x_data[0]),
                #self.datain[1].eq(self.x_data[1]),
                #self.datain[2].eq(self.x_data[2]),
                #self.datain[3].eq(self.x_data[3]),
                #self.datain[4].eq(self.x_data[4]),
                #self.datain[5].eq(self.x_data[5]),
                #self.datain[6].eq(self.x_data[6]),
                #self.datain[7].eq(self.x_data[7]),
                #self.datain[7].eq(self.x_data[8]),

                ## Actual input
                self.datain[0].eq(self.pads.a_t.i),
                self.datain[1].eq(self.pads.b_t.i),
                self.datain[2].eq(self.pads.c_t.i),
                self.datain[3].eq(self.pads.d_t.i),
                self.datain[4].eq(self.pads.e_t.i),
                self.datain[5].eq(self.pads.f_t.i),
                self.datain[6].eq(self.pads.g_t.i),
                self.datain[7].eq(self.pads.h_t.i),
                self.datain[8].eq(self.pads.i_t.i),

                

                ### Only reading 8 bits right now
                ### so just ignore the rest
                self.datain[9].eq(0),
                self.datain[10].eq(0),
                self.datain[11].eq(0),
                self.datain[12].eq(0),
                self.datain[13].eq(0),
                #self.datain[9].eq(self.pads.j_t.i),
                #self.datain[10].eq(self.pads.k_t.i),
                #self.datain[11].eq(self.pads.l_t.i),
                #self.datain[12].eq(self.pads.m_t.i),
                #self.datain[13].eq(self.pads.n_t.i),
            ]

        with m.If(scan_bus.bus_state == BUS_FIFO):
            with m.If(self.in_fifo.w_rdy):
                    m.d.comb += [
                        self.in_fifo.din.eq(self.datain[0:7]),
                        self.in_fifo.w_en.eq(1),
                    ]
            
        return m


class ScanGenApplet(GlasgowApplet, name="scan-gen"):
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
    "i","j","k","l","m","n", "o","p")

    @classmethod
    def add_build_arguments(cls, parser, access):
        super().add_build_arguments(parser, access)
        for pin in cls.__pins:
            access.add_pin_argument(parser, pin, default=True)


    def build(self, target, args):
        self.mux_interface = iface = target.multiplexer.claim_interface(self, args)
        #iface.add_subtarget(LEDBlinker())
        iface.add_subtarget(DataBusAndFIFOSubtarget(
            pads=iface.get_pads(args, pins=self.__pins),
            in_fifo = iface.get_in_fifo(),
            out_fifo = iface.get_out_fifo()
        ))
    
    @classmethod
    def add_run_arguments(cls, parser, access):
        super().add_run_arguments(parser, access)

    async def run(self, device, args):
        iface = await device.demultiplexer.claim_interface(self, self.mux_interface, args)
        async def read_data():
            ## actually get the data from the fifo
            raw_data = await iface.read()
            print(raw_data.tolist())
        await read_data()
        await read_data()

    @classmethod
    def add_interact_arguments(cls, parser):
        pass

    async def interact(self, device, args, iface):
        pass

# -------------------------------------------------------------------------------------------------

class ScanGenAppletTestCase(GlasgowAppletTestCase, applet=ScanGenApplet):
    @synthesis_test
    def test_build(self):
        self.assertBuilds()