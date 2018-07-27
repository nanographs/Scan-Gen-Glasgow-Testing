import os
import tempfile
from migen import *
from migen.build.generic_platform import *
from migen.build.platforms.ice40_hx8k_b_evn import Platform as HX8KEvaluationPlatform


_ext = [
    ("clk_in",   0, Pins("C2")), # DP02B
    ("clk_out",  0, Pins("D1")),
    ("data_in",  0, Pins("J1")), # DP14B
    ("data_out", 0, Pins("K3")),
]


class SubLVDSBuffer(Module):
    def __init__(self):
        self.platform = HX8KEvaluationPlatform()
        self.platform.add_extension(_ext)

        self.clock_domains.cd_sys = ClockDomain()

        counter  = Signal(22)
        self.sync += counter.eq(counter - 1)

        led      = self.platform.request("user_led")
        self.comb += led.eq(counter[counter.nbits - 1])

        clk      = Signal()
        data     = Signal()
        clk_in   = self.platform.request("clk_in")
        data_in  = self.platform.request("data_in")
        clk_out  = self.platform.request("clk_out")
        data_out = self.platform.request("data_out")

        self.comb += self.cd_sys.clk.eq(~clk)

        clk_2 = Signal()
        self.sync += [
            clk_2.eq(~clk_2)
        ]

        self.specials += [
            Instance("SB_IO",
                p_PIN_TYPE=C(0b000001, 6), # PIN_INPUT
                p_IO_STANDARD="SB_LVDS_INPUT",
                io_PACKAGE_PIN=clk_in,
                o_D_IN_0=clk,
            ),
            Instance("SB_IO",
                p_PIN_TYPE=C(0b011000, 6), # PIN_OUTPUT
                io_PACKAGE_PIN=clk_out,
                i_D_OUT_0=clk_2,
            ),
            Instance("SB_IO",
                p_PIN_TYPE=C(0b000001, 6), # PIN_INPUT
                p_IO_STANDARD="SB_LVDS_INPUT",
                io_PACKAGE_PIN=data_in,
                o_D_IN_0=data,
            ),
            Instance("SB_IO",
                p_PIN_TYPE=C(0b011000, 6), # PIN_OUTPUT
                io_PACKAGE_PIN=data_out,
                i_D_OUT_0=data,
            ),
        ]

    def build_and_load(self, **kwargs):
        build_dir = tempfile.mkdtemp(prefix="sublvds_")
        self.platform.build(self, build_dir=build_dir, **kwargs)

        programmer = self.platform.create_programmer()
        programmer.load_bitstream(os.path.join(build_dir, "top.bin"))


if __name__ == "__main__":
    sub_lvds_buffer = SubLVDSBuffer()
    sub_lvds_buffer.build_and_load()
