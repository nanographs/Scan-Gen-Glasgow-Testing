from amaranth.build import *

obi_resources  = [
    Resource("control", 0,
        Subsignal("D17", Pins("K1", dir="o")),
        Subsignal("D18", Pins("J1", dir="o")),
        Subsignal("D19", Pins("H3", dir="o")),
        Subsignal("D20", Pins("H1", dir="o")),
        Subsignal("D21", Pins("G3", dir="o")),
        Subsignal("D22", Pins("H2", dir="o")),
        Subsignal("D23", Pins("F3", dir="o")),
        Subsignal("D24", Pins("G1", dir="o")),
        Attrs(IO_STANDARD="SB_LVCMOS33")
    ),

    Resource("data", 0,
        Subsignal("D1", Pins("B2", dir="io")),
        Subsignal("D2", Pins("B1", dir="io")),
        Subsignal("D3", Pins("C4", dir="io")),
        Subsignal("D4", Pins("C3", dir="io")),
        Subsignal("D5", Pins("C2", dir="io")),
        Subsignal("D6", Pins("C1", dir="io")),
        Subsignal("D7", Pins("D1", dir="io")),
        Subsignal("D8", Pins("D3", dir="io")),
        Subsignal("D9", Pins("F4", dir="io")),
        Subsignal("D10", Pins("G2", dir="io")),
        Subsignal("D11", Pins("E3", dir="io")),
        Subsignal("D12", Pins("F1", dir="io")),
        Subsignal("D13", Pins("E2", dir="io")),
        Subsignal("D14", Pins("F2", dir="io")),
        # Subsignal("D15", Pins("E1", dir="io")),
        # Subsignal("D16", Pins("D2", dir="io")),
        Attrs(IO_STANDARD="SB_LVCMOS33")
    ),

    Resource("power_ok", 0, Pins("D2", dir = "i"), Attrs(IO_STANDARD="SB_LVCMOS33"))
]
