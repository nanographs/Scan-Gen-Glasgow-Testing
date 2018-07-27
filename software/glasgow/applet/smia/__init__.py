import logging
import time
from migen import *

from .. import *
from ..i2c_master import I2CMasterApplet
from .smia_cci import SMIACCIInterface, SMIACamera


logger = logging.getLogger(__name__)


class SMIASubtarget(Module):
    def __init__(self, pads, reset):
        self.comb += [
            pads.xshutdown_t.oe.eq(1),
            pads.extclk_t.oe.eq(1),
        ]

        reset_cyc  = 1 << 16
        extclk_cyc = 2

        reset_timer = Signal(max=reset_cyc, reset=reset_cyc - 1)
        self.sync += [
            If(reset,
                reset_timer.eq(reset_timer.reset)
            ).Elif(reset_timer != 0,
                reset_timer.eq(reset_timer - 1)
            )
        ]
        self.comb += pads.xshutdown_t.o.eq(reset_timer == 0)

        extclk_timer = Signal(max=extclk_cyc, reset=extclk_cyc - 1)
        self.sync += [
            If(extclk_timer == 0,
                pads.extclk_t.o.eq(~pads.extclk_t.o),
                extclk_timer.eq(extclk_timer.reset)
            ).Else(
                extclk_timer.eq(extclk_timer - 1)
            )
        ]


class CCP2Subtarget(Module):
    def __init__(self, pin_clk, pin_data, arbiter, errors):
        clk   = Signal()
        data0 = Signal()
        data1 = Signal()
        self.specials += [
            Instance("SB_IO",
                p_PIN_TYPE=C(0b000001, 6), # PIN_INPUT
                io_PACKAGE_PIN=pin_clk,
                o_D_IN_0=clk,
            ),
            Instance("SB_IO",
                p_PIN_TYPE=C(0b000000, 6), # PIN_INPUT_DDR
                io_PACKAGE_PIN=pin_data,
                i_INPUT_CLK=clk,
                o_D_IN_0=data0,
                o_D_IN_1=data1,
            ),
        ]

        self.clock_domains.cd_pix = ClockDomain()
        self.comb += self.cd_pix.clk.eq(clk)

        shreg = Signal(33)
        bitno = Signal(3)
        self.sync.pix += [
            shreg.eq(Cat(shreg[2:], data0, data1)),
            If(shreg[2:26] == C(0x0000ff, 24),
                bitno.eq(0)
            ).Elif(shreg[3:27] == C(0x0000ff, 24),
                bitno.eq(1)
            ).Else(
                bitno.eq(bitno + 2)
            )
        ]

        in_fifo = arbiter.get_in_fifo(1, clock_domain=self.cd_pix)
        self.sync.pix += [
            If(bitno[0],
                in_fifo.din.eq(shreg[1:9])
            ).Else(
                in_fifo.din.eq(shreg[0:8])
            ),
            in_fifo.we.eq((bitno & ~1) == 0),
        ]


class SMIAApplet(I2CMasterApplet, name="smia"):
    logger = logger
    help = "capture image data from SMIA cameras"
    description = """
    Configure SMIA cameras via the CCI interface and capture image data via the CCP2 interface.
    """

    @classmethod
    def add_build_arguments(cls, parser, access):
        super().add_build_arguments(parser, access)

        access.add_pin_argument(parser, "xshutdown", required=True)
        access.add_pin_argument(parser, "extclk", required=True)

        access.add_pin_argument(parser, "clk", required=True)
        access.add_pin_argument(parser, "data", required=True)

    def build(self, target, args):
        super().build(target, args)

        iface = self.mux_interface
        reset, self.__addr_reset = target.registers.add_rw(1, reset=1)
        target.submodules += SMIASubtarget(
            pads=iface.get_pads(args, pins=("xshutdown", "extclk")),
            reset=reset,
        )

        errors, self.__addr_errors = target.registers.add_ro()
        target.submodules += CCP2Subtarget(
            pin_clk=iface._pins[args.pin_clk],
            pin_data=iface._pins[args.pin_data],
            arbiter=iface._fx2_arbiter,
            errors=errors,
        )

    @classmethod
    def add_run_arguments(cls, parser, access):
        super().add_run_arguments(parser, access)

        parser.add_argument("-i", "--show-info", action="store_true", default=False,
            help="print camera information (model, manufacturer, etc)")
        parser.add_argument("-l", "--show-limits", action="store_true", default=False,
            help="print camera limits and capabilities (frequencies, gains, sizes, etc)")
        parser.add_argument("-c", "--show-clocking", action="store_true", default=False,
            help="print camera clocking configuration")

    def run(self, device, args):
        i2c_iface = super().run(device, args, interactive=False)
        cci_iface = SMIACCIInterface(i2c_iface, self.logger)
        camera = SMIACamera(cci_iface, self.logger, 15e6)

        device.set_voltage("A", 1.8)
        device.set_voltage("B", 2.7)

        device.write_register(self.__addr_reset, 1)
        i2c_iface.reset()
        time.sleep(0.050)
        device.write_register(self.__addr_reset, 0)
        time.sleep(0.050)

        if args.show_info:
            camera.show_info()

        if camera.get_smia_version() not in ((0, 9), (1, 0)):
            self.logger.error("unsupported SMIA version %d.%d", *camera.get_smia_version())
            if camera.get_smia_version() == (0, 0):
                self.logger.error("camera responded with SMIA version 0.0; is the power on?")
                self.logger.error("some cameras pull SDA/SCL lines to ground until both power "
                                  "supplies are on, in violation of the SMIA specification")
            return

        if args.show_limits:
            camera.show_limits()

        camera.set_ccp_data_format("RAW8")

        self.logger.info("autoconfiguring clocking")
        def clocking_constraints(config):
            return (config["op_sys_clk_freq_mhz"] <= 50.0 and
                    config["vt_sys_clk_freq_mhz"] == config["op_sys_clk_freq_mhz"])
        if not camera.autoconfigure_clocking(clocking_constraints):
            self.logger.error("cannot automatically configure clocking")

        if args.show_clocking:
            camera.show_clocking_configuration()

        camera.set("test_pattern_mode", "ColourBars")
        camera.set("test_data_red",    0b10101010)
        camera.set("test_data_greenR", 0x00)
        camera.set("test_data_blue",   0x00)
        camera.set("test_data_greenB", 0x00)
        camera.start_streaming()

        print(device.bulk_read(8, 16384).hex())
