from amaranth import *
from amaranth.lib import data, wiring
from amaranth.lib.wiring import In, Out


# Overview of (linear) processing pipeline:
# 1. PC software (in: user input, out: bytes)
# 2. Glasgow software/framework (in: bytes, out: same bytes; vendor-provided)
# 3. Command deserializer (in: bytes; out: structured commands)
# 4. Command parser/executor (in: structured commands, out: DAC state changes and ADC sample strobes)
# 5. DAC (in: DAC words, out: analog voltage; Glasgow plug-in)
# 6. electron microscope
# 7. ADC (in: analog voltage; out: ADC words, Glasgow plug-in)
# 8. Image serializer (in: ADC words, out: image frames)
# 9. Configuration synchronizer (in: image frames, out: image or configuration frames)
# 10. Frame serializer (in: frames, out: bytes)
# 11. Glasgow software/framework (in: bytes, out: same bytes; vendor-provided)
# 12. PC software (in: bytes, out: displayed image)


class ParallelBusController(wiring.Component):
    # FPGA-side interface
    i_stream: In(wiring.Signature({
        "data": Out(data.StructLayout({
            "dac_x": 14,
            "dac_y": 14,
        })),
        "valid": Out(1),
        "ready": In(1),
    }))
    o_stream: Out(wiring.Signature({

    }))

    # IO-side interface
    adc_clk: Out(1)
    dac_clk: Out(1)
