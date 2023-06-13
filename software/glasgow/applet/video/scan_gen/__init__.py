import logging
import asyncio
from amaranth import *
from amaranth.sim import Simulator

from ... import *









########################################
######       Scan Generator       ######
########################################
###### Increment on min dwell = 0 ######
########################################
######   set x_ramp and y_ramp    ######
########################################

class ScanGenSubtarget(Elaboratable):




    def __init__(self, x_width, y_height):
        self.x_width = x_width
        self.y_width = y_height


        
    def elaborate(self, platform):
        m = Module()




        return m




##############################
###### Min Dwel Counter ######
##############################









######################
###### DATA BUS ######
######################

class DataBusAndFIFOSubtarget(Elaboratable):
    def __init__(self, pads, in_fifo, out_fifo):
        self.pads     = pads
        self.in_fifo  = in_fifo
        self.out_fifo = out_fifo
        self.datain = Signal(14)

    def elaborate(self, platform):
        m = Module()

        x_latch = platform.request("X_LATCH")
        x_enable = platform.request("X_ENABLE")
        y_latch = platform.request("Y_LATCH")
        y_enable = platform.request("Y_ENABLE")
        a_latch = platform.request("A_LATCH")
        a_enable = platform.request("A_ENABLE")

        m.submodules.ramp = ramp = RampGenerator(65535)




        ####################################################################################
        ######                        DAC & ADC Clock Drivers                         ######
        ####################################################################################
        ###### Devide number of cycles in min dwel in half, toggle DAC and ADC busses ######
        ####################################################################################








        ######################################################################################################################################################
        ######                                                   State Machine                                                                          ######
        ###### If clock = 1 --> X Write --> X Latch --> Y Write --> Y Latch --> A Latch and Enable --> A Read --> Frame & Line Flags --> Wait for clock ######
        ######################################################################################################################################################

        m.d.comb += x_enable.eq(1)
        m.d.comb += y_enable.eq(1)



        with m.FSM() as fsm:
            with m.State("Wait_Start"):

                with m.If(MinDwelCounter == 1):
                    m.d.comb += MihDwelCounter.eq(MinDwelCounter + 1)
                    m.next = "X_Write"


            with m.State("X_Write"):
                m.d.comb += [
                    self.pads.a_t.oe.eq(),
                    self.pads.a_t.o.eq(x_ramp.count[0]),
                    self.pads.b_t.oe.eq(),
                    self.pads.b_t.o.eq(x_ramp.count[1]),
                    self.pads.c_t.oe.eq(),
                    self.pads.c_t.o.eq(x_ramp.count[2]),
                    self.pads.d_t.oe.eq(),
                    self.pads.d_t.o.eq(x_ramp.count[3]),
                    self.pads.e_t.oe.eq(),
                    self.pads.e_t.o.eq(x_ramp.count[4]),
                    self.pads.f_t.oe.eq(),
                    self.pads.f_t.o.eq(x_ramp.count[5]),
                    self.pads.g_t.oe.eq(),
                    self.pads.g_t.o.eq(x_ramp.count[6]),
                    self.pads.h_t.oe.eq(),
                    self.pads.h_t.o.eq(x_ramp.count[7]),
                    self.pads.i_t.oe.eq(),
                    self.pads.i_t.o.eq(x_ramp.count[8]),
                    self.pads.j_t.oe.eq(),
                    self.pads.j_t.o.eq(x_ramp.count[9]),
                    self.pads.k_t.oe.eq(),
                    self.pads.k_t.o.eq(x_ramp.count[10]),
                    self.pads.l_t.oe.eq(),
                    self.pads.l_t.o.eq(x_ramp.count[11]),
                    self.pads.m_t.oe.eq(),
                    self.pads.m_t.o.eq(x_ramp.count[12]),
                    self.pads.n_t.oe.eq(),
                    self.pads.n_t.o.eq(x_ramp.count[13]),
                    ]
                m.next = "X_Latch"


                with m.State("X_Latch"):
                m.d.comb += [
                    
                    x_latch.eq(1),  

                    self.pads.a_t.oe.eq(),
                    self.pads.a_t.o.eq(x_ramp.count[0]),
                    self.pads.b_t.oe.eq(1),
                    self.pads.b_t.o.eq(x_ramp.count[1]),
                    self.pads.c_t.oe.eq(1),
                    self.pads.c_t.o.eq(x_ramp.count[2]),
                    self.pads.d_t.oe.eq(1),
                    self.pads.d_t.o.eq(x_ramp.count[3]),
                    self.pads.e_t.oe.eq(1),
                    self.pads.e_t.o.eq(x_ramp.count[4]),
                    self.pads.f_t.oe.eq(1),
                    self.pads.f_t.o.eq(x_ramp.count[5]),
                    self.pads.g_t.oe.eq(1),
                    self.pads.g_t.o.eq(x_ramp.count[6]),
                    self.pads.h_t.oe.eq(1),
                    self.pads.h_t.o.eq(x_ramp.count[7]),
                    self.pads.i_t.oe.eq(1),
                    self.pads.i_t.o.eq(x_ramp.count[8]),
                    self.pads.j_t.oe.eq(1),
                    self.pads.j_t.o.eq(x_ramp.count[9]),
                    self.pads.k_t.oe.eq(1),
                    self.pads.k_t.o.eq(x_ramp.count[10]),
                    self.pads.l_t.oe.eq(1),
                    self.pads.l_t.o.eq(x_ramp.count[11]),
                    self.pads.m_t.oe.eq(1),
                    self.pads.m_t.o.eq(x_ramp.count[12]),
                    self.pads.n_t.oe.eq(1),
                    self.pads.n_t.o.eq(x_ramp.count[13]),
                    ]
                m.next = "Y_Write"

            with m.State("Y_WRITE"):
                ## output pins
                m.d.comb += [
                    self.pads.a_t.oe.eq(1),
                    self.pads.a_t.o.eq(y_ramp.count[0]),
                    self.pads.b_t.oe.eq(1),
                    self.pads.b_t.o.eq(y_ramp.count[1]),
                    self.pads.c_t.oe.eq(1),
                    self.pads.c_t.o.eq(y_ramp.count[2]),
                    self.pads.d_t.oe.eq(1),
                    self.pads.d_t.o.eq(y_ramp.count[3]),
                    self.pads.e_t.oe.eq(1),
                    self.pads.e_t.o.eq(y_ramp.count[4]),
                    self.pads.f_t.oe.eq(1),
                    self.pads.f_t.o.eq(y_ramp.count[5]),
                    self.pads.g_t.oe.eq(1),
                    self.pads.g_t.o.eq(y_ramp.count[6]),
                    self.pads.h_t.oe.eq(1),
                    self.pads.h_t.o.eq(y_ramp.count[7]),
                    self.pads.i_t.oe.eq(1),
                    self.pads.i_t.o.eq(y_ramp.count[8]),
                    self.pads.j_t.oe.eq(1),
                    self.pads.j_t.o.eq(y_ramp.count[9]),
                    self.pads.k_t.oe.eq(1),
                    self.pads.k_t.o.eq(y_ramp.count[10]),
                    self.pads.l_t.oe.eq(1),
                    self.pads.l_t.o.eq(y_ramp.count[11]),
                    self.pads.m_t.oe.eq(1),
                    self.pads.m_t.o.eq(y_ramp.count[12]),
                    self.pads.n_t.oe.eq(1),
                    self.pads.n_t.o.eq(y_ramp.count[13]),
                    ]
                m.next = "Y_LATCH"

            with m.State("Y_LATCH"):
                m.d.comb += [
                    ## enable ramp
                    
                    y_latch.eq(1),
                    
                    self.pads.a_t.oe.eq(1),
                    self.pads.a_t.o.eq(y_ramp.count[0]),
                    self.pads.b_t.oe.eq(1),
                    self.pads.b_t.o.eq(y_ramp.count[1]),
                    self.pads.c_t.oe.eq(1),
                    self.pads.c_t.o.eq(y_ramp.count[2]),
                    self.pads.d_t.oe.eq(1),
                    self.pads.d_t.o.eq(y_ramp.count[3]),
                    self.pads.e_t.oe.eq(1),
                    self.pads.e_t.o.eq(y_ramp.count[4]),
                    self.pads.f_t.oe.eq(1),
                    self.pads.f_t.o.eq(y_ramp.count[5]),
                    self.pads.g_t.oe.eq(1),
                    self.pads.g_t.o.eq(y_ramp.count[6]),
                    self.pads.h_t.oe.eq(1),
                    self.pads.h_t.o.eq(y_ramp.count[7]),
                    self.pads.i_t.oe.eq(1),
                    self.pads.i_t.o.eq(y_ramp.count[8]),
                    self.pads.j_t.oe.eq(1),
                    self.pads.j_t.o.eq(y_ramp.count[9]),
                    self.pads.k_t.oe.eq(1),
                    self.pads.k_t.o.eq(y_ramp.count[10]),
                    self.pads.l_t.oe.eq(1),
                    self.pads.l_t.o.eq(y_ramp.count[11]),
                    self.pads.m_t.oe.eq(1),
                    self.pads.m_t.o.eq(y_ramp.count[12]),
                    self.pads.n_t.oe.eq(1),
                    self.pads.n_t.o.eq(y_ramp.count[13]),
                ]   
                m.next = "A_Latch_&_Enable"

            with m.State("A_Latch_&_Enable"):
                m.d.comb += [                  
                    a_latch.eq(1),
                    a_enable.eq(1),
                ]
                m.next = "A_READ"


            with m.State("A_READ"):
                ## input pins
                m.d.comb += [
                    a_enable.eq(1),

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
                ]
                m.next = "FIFO_Write_1"

            with m.State("FIFO_Write_1"):
                with m.If(self.in_fifo.w_rdy):
                    m.d.comb += [
                        self.in_fifo.din.eq(self.datain[0:7]),
                        self.in_fifo.w_en.eq(1),
                    ]
                m.next = "FIFO_Write_2"

            with m.State("FIFO_Write_2"):
                with m.If(self.in_fifo.w_rdy):
                    m.d.comb += [
                        self.in_fifo.din.eq(self.datain[8:]),
                        self.in_fifo.w_en.eq(1),
                        
                    ]
                    m.next = "Line_&_Frame_Flags"


            ###### Send 00 to signal new frame, send 01 to signal new line


            with m.State("Line_&_Frame_Flags"):
                with m.If(new_frame):
                    with m.If(self.in_fifo.w_rdy):
                        m.d.comb += [
                            self.in_fifo.din.eq(0),
                            self.in_fifo.w_en.eq(1),
                        ]

                with m.If(new_line):
                    with m.If(self.in_fifo.w_rdy):
                        m.d.comb += [
                            self.in_fifo.din.eq(1),
                            self.in_fifo.w_en.eq(1),
                        ]


                m.next = "Wait_Start"



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
    __pins = ("a", "b", "c", "d", "e","f","g","h")

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

class ScanGenAppletTestCase(GlasgowAppletTestCase, applet=ScanGenApplet):
    @synthesis_test
    def test_build(self):
        self.assertBuilds()