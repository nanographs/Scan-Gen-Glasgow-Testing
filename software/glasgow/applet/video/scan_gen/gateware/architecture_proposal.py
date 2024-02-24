from amaranth import *
from amaranth.lib import enum, data, wiring
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
# 9. Configuration synchronizer (in: image frames, out: image pixels or synchronization frames)
# 10. Frame serializer (in: frames, out: bytes)
# 11. Glasgow software/framework (in: bytes, out: same bytes; vendor-provided)
# 12. PC software (in: bytes, out: displayed image)


def StreamSignature(data_layout):
    return wiring.Signature({
        "data":  Out(data_layout),
        "valid": Out(1),
        "ready": In(1),
    })


BusSignature = wiring.Signature({
    "adc_clk":  Out(1),
    "adc_oe":   Out(1),

    "dac_clk":  Out(1),
    "dac_x_le": Out(1),
    "dac_y_le": Out(1),

    "data_i":   In(15),
    "data_o":   Out(15),
    "data_oe":  Out(1),
})


class BusController(wiring.Component):
    # FPGA-side interface
    dac_stream: In(StreamSignature(data.StructLayout({
        "dac_x_code": 14,
        "dac_y_code": 14,
        "last":       1,
    })))

    adc_stream: Out(StreamSignature(data.StructLayout({
        "adc_code": 14,
        "adc_ovf":  1,
        "last":     1,
    })))

    # IO-side interface
    bus: Out(BusSignature)

    def __init__(self, *, adc_half_period: int, adc_latency: int):
        assert (adc_half_period * 2) >= 4, "ADC period must be large enough for FSM latency"
        self.adc_half_period = adc_half_period
        self.adc_latency     = adc_latency

        super().__init__()

    def elaborate(self, platform):
        m = Module()

        adc_cycles = Signal(range(self.adc_half_period))
        with m.If(adc_cycles == self.adc_half_period - 1):
            m.d.sync += adc_cycles.eq(0)
            m.d.sync += self.bus.adc_clk.eq(~self.bus.adc_clk)
        with m.Else():
            m.d.sync += adc_cycles.eq(adc_cycles + 1)
        # ADC and DAC share the bus and have to work in tandem. The ADC conversion starts simultaneously
        # with the DAC update, so the entire ADC period is available for DAC-scope-ADC propagation.
        m.d.comb += self.bus.dac_clk.eq(self.bus.adc_clk)

        # Queue; MSB = most recent sample, LSB = least recent sample
        accept_sample = Signal(self.adc_latency)
        # Queue; as above
        last_sample = Signal(self.adc_latency)

        m.submodules.o_stream_fifo = o_stream_fifo = \
            SyncFIFOBuffered(depth=self.adc_latency, width=len(self.o_stream.data.as_value()))
        m.d.comb += [
            self.o_stream.data.eq(o_stream_fifo.r_data),
            self.o_stream.valid.eq(o_stream_fifo.r_rdy),
            o_stream_fifo.r_en.eq(self.o_stream.ready),
        ]

        o_stream_data = Signal.like(self.o_stream.data) # FIXME: will not be needed after FIFOs have shapes
        m.d.comb += [
            Cat(o_stream_data.adc_code,
                o_stream_data.adc_ovf).eq(self.io_bus.i),
            o_stream_data.last.eq(last_sample[0]),
            o_stream_fifo.w_data.eq(o_stream_data),
        ]

        i_stream_data = Signal.like(self.i_stream.data)
        with m.FSM():
            with m.State("ADC Wait"):
                with m.If(self.bus.adc_clk & (adc_cycles == 0)):
                    m.d.comb += self.bus.adc_oe.eq(1)
                    m.next = "ADC Read"

            with m.State("ADC Read"):
                m.d.comb += o_stream_fifo.w_en.eq(accept_sample[0]) # does nothing if ~o_stream_fifo.w_rdy
                with m.If(self.i_stream.valid & o_stream_data.w_rdy):
                    # Latch DAC codes from input stream.
                    m.d.comb += self.i_stream.ready.eq(1)
                    m.d.sync += i_stream_data.eq(self.i_stream.data)
                    # Schedule ADC sample for these DAC codes to be output.
                    m.d.sync += accept_sample.eq(Cat(accept_sample, 1))
                    # Carry over the flag for last sample [of averaging window] to the output.
                    m.d.sync += accept_sample.eq(Cat(last_sample, self.i_stream.data.last))
                with m.Else():
                    # Leave DAC codes as they are.
                    # Schedule ADC sample for these DAC codes to be discarded.
                    m.d.sync += accept_sample.eq(Cat(accept_sample, 0))
                    # The value of this flag is discarded, so it doesn't matter what it is.
                    m.d.sync += accept_sample.eq(Cat(last_sample, 0))
                m.next = "X DAC Write"

            with m.State("X DAC Write"):
                m.d.comb += [
                    self.bus.data_o.eq(i_stream_data.dac_x_code),
                    self.bus.data_oe.eq(1),
                    self.bus.dac_x_le.eq(1),
                ]
                m.next = "Y DAC Write"

            with m.State("Y DAC Write"):
                m.d.comb += [
                    self.bus.data_o.eq(i_stream_data.dac_y_code),
                    self.bus.data_oe.eq(1),
                    self.bus.dac_y_le.eq(1),
                ]
                m.next = "ADC Read"

        return m


class Supersampler(wiring.Component):
    dac_stream: In(StreamSignature(data.StructLayout({
        "dac_x_code": 14,
        "dac_y_code": 14,
        "dwell_time": 16,
    })))

    adc_stream: Out(StreamSignature(data.StructLayout({
        "adc_code":   14,
    })))

    super_dac_stream: Out(StreamSignature(data.StructLayout({
        "dac_x_code": 14,
        "dac_y_code": 14,
        "last":       1,
    })))

    super_adc_stream: In(StreamSignature(data.StructLayout({
        "adc_code":   14,
        "adc_ovf":    1,  # ignored
        "last":       1,
    })))

    def elaborate(self, platform):
        m = Module()

        dac_stream_data = Signal.like(self.dac_stream.data)
        m.d.comb += [
            self.super_dac_stream.data.dac_x_code.eq(dac_stream.dac_x_code),
            self.super_dac_stream.data.dac_y_code.eq(dac_stream.dac_y_code),
        ]

        dwell_counter = Signal.like(dac_stream_data.dwell_time)
        with m.FSM():
            with m.State("Wait"):
                m.d.comb += self.dac_stream.ready.eq(1)
                with m.If(self.dac_stream.valid):
                    m.d.sync += dac_stream_data.eq(self.dac_stream)
                    m.d.sync += dwell_counter.eq(0)
                    m.d.comb += n_average_fifo.w_en.eq(1) # overflow shouldn't be possible
                    m.next = "Generate"

            with m.State("Generate"):
                m.d.comb += self.super_dac_stream.valid.eq(1)
                with m.If(self.super_dac_stream.ready):
                    with m.If(dwell_counter == dac_stream_data.dwell_time):
                        m.next = "Wait"
                    with m.Else():
                        m.d.sync += dwell_counter.eq(dwell_counter + 1)

        running_average = Signal.like(self.super_adc_stream.data.adc_code)
        m.d.comb += self.adc_stream.data.adc_code.eq(running_average)
        with m.FSM():
            with m.State("Start"):
                m.d.comb += self.super_adc_stream.ready.eq(1)
                with m.If(self.super_adc_stream.valid):
                    m.d.sync += running_average.eq(self.super_adc_stream.data.adc_code)
                    with m.If(self.super_adc_stream.data.last):
                        m.next = "Wait"

            with m.State("Average"):
                m.d.comb += self.super_adc_stream.ready.eq(1)
                with m.If(self.super_adc_stream.valid):
                    m.d.sync += running_average.eq((running_average + self.super_adc_stream.data.adc_code) >> 1)
                    with m.If(self.super_adc_stream.data.last):
                        m.next = "Wait"

            with m.State("Wait"):
                m.d.sync += self.adc_stream.valid.eq(1)
                with m.If(self.adc_stream.ready):
                    m.next = "Start"

        return m


class RasterRegion(data.Struct):
    x_start: 14, # UQ(14,0)
    x_count: 14, # UQ(14,0)
    x_step:  16, # UQ(8,8)
    y_start: 14, # UQ(14,0)
    y_count: 14, # UQ(14,0)
    y_stop:  16, # UQ(8,8)


DwellTime = unsigned(16)


class RasterScanner(wiring.Component):
    FRAC_BITS = 8

    roi_stream: In(StreamSignature(RasterRegion))

    dwell_stream: In(StreamSignature(DwellTime))

    abort: In(1)
    #: Interrupt the scan in progress and fetch the next ROI from `roi_stream`.

    dac_stream: Out(StreamSignature(data.StructLayout({
        "dac_x_code": 14,
        "dac_y_code": 14,
        "dwell_time": DwellTime,
    })))

    def elaborate(self, platform):
        m = Module()

        region  = Signal.like(self.roi_stream.data)

        x_accum = Signal.like(region.x_start)
        x_count = Signal.like(region.x_count)
        y_accum = Signal.like(region.y_start)
        y_count = Signal.like(region.y_count)
        m.d.comb += [
            self.dac_stream.data.dac_x_code.eq(x_accum[self.FRAC_BITS:]),
            self.dac_stream.data.dac_y_code.eq(y_accum[self.FRAC_BITS:]),
            self.dac_stream.data.dwell_time.eq(self.dwell_stream.data),
        ]

        with m.FSM():
            with m.State("Get ROI"):
                m.d.comb += self.roi_stream.ready.eq(1)
                with m.If(self.roi_stream.valid):
                    m.d.sync += [
                        region.eq(self.roi_stream.data),
                        x_accum.eq(Cat(C(0, self.FRAC_BITS), self.roi_stream.data.x_start)),
                        x_count.eq(0),
                        y_accum.eq(Cat(C(0, self.FRAC_BITS), self.roi_stream.data.y_start)),
                        y_count.eq(0),
                    ]
                    m.next = "Scan"

            with m.State("Scan"):
                m.d.comb += self.dwell_stream.ready.eq(1)
                m.d.comb += self.dac_stream.valid.eq(self.dwell_stream.valid)
                with m.If(self.dwell_stream.valid & self.dac_stream.ready):
                    # AXI4-Stream §2.2.1
                    # > Once TVALID is asserted it must remain asserted until the handshake occurs.
                    with m.If(self.abort):
                        m.next = "Get ROI"

                    with m.If(x_count == region.x_count):
                        with m.If(y_count == region.y_count):
                            m.next = "Get ROI"
                        with m.Else():
                            m.d.sync += y_accum.eq(y_accum + region.y_step)
                            m.d.sync += y_count.eq(y_count + 1)

                        m.d.sync += x_accum.eq(Cat(C(0, self.FRAC_BITS), self.roi_stream.data.x_start))
                        m.d.sync += x_count.eq(0)
                    with m.Else():
                        m.d.sync += x_accum.eq(x_accum + region.x_step)
                        m.d.sync += x_count.eq(x_accum + 1)

        return m


Cookie = unsigned(16)
#: Arbitrary value for synchronization. When received, returned as-is in an USB IN frame.


class Command(data.Struct):
    class Type(enum.Enum, shape=8):
        Synchronize     = 0
        RasterRegion    = 1
        RasterPixel     = 2
        RasterPixelRun  = 3
        VectorPixel     = 4

    type: Type
    payload: data.UnionLayout({
        "synchronize":      data.StructLayout({
            "cookie":           Cookie,
            "raster_mode":      1,
        }),
        "raster_region":    RasterRegion,
        "raster_pixel":     DwellTime,
        "raster_pixel_run": data.StructLayout({
            "length":           16,
            "dwell_time":       DwellTime,
        }),
        "vector_pixel":     data.StructLayout({
            "x_coord":          14,
            "y_coord":          14,
            "dwell_time":       DwellTime,
        }),
    })


class CommandParser(wiring.Signature):
    usb_stream: In(StreamSignature(8))
    cmd_stream: Out(StreamSignature(Command))

    def elaborate(self, platform):
        m = Module()

        command = Signal(Command.Type)

        with m.FSM():
            with m.State("Type"):
                m.d.comb += self.usb_stream.ready.eq(1)
                m.d.sync += command.type.eq(self.usb_stream.data)
                with m.If(self.usb_stream.valid):
                    with m.Switch(self.usb_stream.data):
                        with m.Case(Command.Type.Synchronize):
                            m.next = "Payload Synchronize 1"

                        with m.Case(Command.Type.RasterRegion):
                            m.next = "Payload Raster Region 1"

                        with m.Case(Command.Type.RasterPixel):
                            m.next = "Payload Raster Pixel Count"

                        with m.Case(Command.Type.RasterPixelRun):
                            m.next = "Payload Raster Pixel Run 1"

                        with m.Case(Command.Type.VectorPixel):
                            m.next = "Payload Vector Pixel 1"

            def Deserialize(target, state, next_state):
                with m.State(state):
                    m.d.comb += self.usb_stream.ready.eq(1)
                    with m.If(self.usb_stream.valid):
                        m.d.sync += target.eq(self.usb_stream.data)
                        m.next = next_state

            def DeserializeWord(target, state_prefix, next_state):
                Deserialize(target[0:8],
                    f"{state_prefix} High", f"{state_prefix} Low")
                Deserialize(target[0:8],
                    f"{state_prefix} Low",  next_state)

            DeserializeWord(command.payload.synchronize.cookie,
                "Payload Synchronize 1", "Payload Synchronize 2")
            Deserialize(command.payload.synchronize.raster_mode,
                "Payload Synchronize 2", "Submit")

            DeserializeWord(command.payload.raster_region.x_start,
                "Payload Raster Region 1", "Payload Raster Region 2")
            DeserializeWord(command.payload.raster_region.x_count,
                "Payload Raster Region 2", "Payload Raster Region 3")
            DeserializeWord(command.payload.raster_region.x_step,
                "Payload Raster Region 3", "Payload Raster Region 4")
            DeserializeWord(command.payload.raster_region.y_start,
                "Payload Raster Region 4", "Payload Raster Region 5")
            DeserializeWord(command.payload.raster_region.y_count,
                "Payload Raster Region 5", "Payload Raster Region 6")
            DeserializeWord(command.payload.raster_region.y_step,
                "Payload Raster Region 6", "Submit")

            raster_pixel_count = Signal(16)
            DeserializeWord(raster_pixel_count,
                "Payload Raster Pixel Count", "Payload Raster Pixel Array Low")

            DeserializeWord(command.payload.raster_pixel,
                "Payload Raster Pixel Array", "Payload Raster Pixel Array Submit")

            with m.State("Payload Raster Pixel Submit"):
                m.d.comb += self.cmd_stream.valid.eq(1)
                with m.If(self.cmd_stream.ready):
                    with m.If(raster_pixel_count == 0):
                        m.next = "Type"
                    with m.Else():
                        m.d.sync += raster_pixel_count.eq(raster_pixel_count - 1)
                        m.next = "Payload Raster Pixel Array Low"

            DeserializeWord(command.payload.raster_pixel_run.length,
                "Payload Raster Pixel Run 1", "Payload Raster Pixel Run 2")
            DeserializeWord(command.payload.raster_pixel_run.dwell_time,
                "Payload Raster Pixel Run 2", "Submit")

            DeserializeWord(command.payload.vector_pixel.x_coord,
                "Payload Vector Pixel 1", "Payload Vector Pixel 2")
            DeserializeWord(command.payload.vector_pixel.y_coord,
                "Payload Vector Pixel 2", "Payload Vector Pixel 3")
            DeserializeWord(command.payload.vector_pixel.dwell_time,
                "Payload Vector Pixel 3", "Submit")

            with m.State("Submit"):
                m.d.comb += self.cmd_stream.valid.eq(1)
                with m.If(self.cmd_stream.ready):
                    m.next = "Type"

        return m


class CommandExecutor(wiring.Signature):
    cmd_stream: In(StreamSignature(Command))
    img_stream: Out(StreamSignature(unsigned(16)))

    bus: Out(BusSignature)

    def elaborate(self, platform):
        m = Module()

        m.submodules.bus_controller = bus_controller = BusController()
        m.submodules.supersampler   = supersampler   = Supersampler()
        m.submodules.raster_scanner = raster_scanner = RasterScanner()

        wiring.connect(m, flipped(self.bus), bus_controller.bus)

        wiring.connect(m, supersampler.super_dac_stream, bus_controller.dac_stream)
        wiring.connect(m, supersampler.super_adc_stream, bus_controller.adc_stream)

        vector_stream = StreamSignature(data.StructLayout({
            "dac_x_code": 14,
            "dac_y_code": 14,
            "dwell_time": DwellTime,
        })).create()

        raster_mode = Signal()
        with m.If(raster_mode):
            wiring.connect(m, raster_scanner.dac_stream, supersampler.dac_stream)
        with m.Else():
            wiring.connect(m, vector_stream, supersampler.dac_stream)

        in_flight_pixels = Signal(4) # should never overflow
        submit_pixel = Signal()
        retire_pixel = Signal()
        m.d.sync += in_flight_pixels.eq(in_flight_pixels + submit_pixel - retire_pixel)

        command = Signal.like(self.cmd_stream.data)
        run_length = Signal.like(command.payload.raster_pixel_run)
        m.d.comb += [
            raster_scanner.roi_stream.data.eq(command.payload.raster_region),
            vector_stream.dac_x_code.eq(command.payload.vector_pixel.x_coord),
            vector_stream.dac_x_code.eq(command.payload.vector_pixel.y_coord),
            vector_stream.dwell_time.eq(command.payload.vector_pixel.dwell_time),
        ]

        sync_req = Signal()
        sync_ack = Signal()

        with m.FSM():
            with m.State("Fetch"):
                m.d.comb += self.cmd_stream.ready.eq(1)
                with m.If(self.cmd_stream.valid):
                    m.d.sync += command.eq(self.cmd_stream.data)
                    m.next = "Execute"

            with m.State("Execute"):
                with m.Switch(command.type):
                    with m.Case(Command.Type.Synchronize):
                        m.d.comb += sync_req.eq(1)
                        with m.If(sync_ack):
                            m.d.sync += raster_mode.eq(command.payload.synchronize.raster_mode)
                            m.next = "Fetch"

                    with m.Case(Command.Type.RasterRegion):
                        m.d.comb += raster_scanner.roi_stream.valid.eq(1)
                        with m.If(raster_scanner.roi_stream.ready):
                            m.next = "Fetch"

                    with m.Case(Command.Type.RasterPixel):
                        m.d.comb += [
                            raster_scanner.dwell_stream.valid.eq(1),
                            raster_scanner.dwell_stream.data.eq(command.payload.raster_pixel),
                        ]
                        with m.If(raster_scanner.dwell_stream.ready):
                            m.d.comb += submit_pixel.eq(1)
                            m.next = "Fetch"

                    with m.Case(Command.Type.RasterPixelRun):
                        m.d.comb += [
                            raster_scanner.dwell_stream.valid.eq(1),
                            raster_scanner.dwell_stream.data.eq(command.payload.raster_pixel_run.dwell_time)
                        ]
                        with m.If(raster_scanner.dwell_stream.ready):
                            m.d.comb += submit_pixel.eq(1)
                            with m.If(run_length == command.payload.raster_pixel_run.length):
                                m.d.sync += run_length.eq(0)
                                m.next = "Fetch"
                            with m.Else():
                                m.d.sync += run_length.eq(run_length + 1)

                    with m.Case(Command.Type.VectorPixel):
                        m.d.comb += vector_stream.valid.eq(1)
                        with m.If(vector_stream.ready):
                            m.d.comb += submit_pixel.eq(1)
                            m.next = "Fetch"

        with m.FSM():
            with m.State("Imaging"):
                m.d.comb += [
                    self.img_stream.data.eq(supersampler.adc_stream.data.adc_code),
                    self.img_stream.valid.eq(supersampler.adc_stream.valid),
                    supersampler.adc_stream.ready.eq(self.img_stream.ready),
                    retire_pixel.eq(supersampler.adc_stream.valid & self.img_stream.ready),
                ]
                with m.If((in_flight_pixels == 0) & sync_req):
                    m.next = "Write FFFF"

            with m.State("Write FFFF"):
                m.d.comb += [
                    self.img_stream.data.eq(0xffff),
                    self.img_stream.valid.eq(1),
                ]
                with m.If(self.img_stream.ready):
                    m.next = "Write cookie"

            with m.State("Write cookie"):
                m.d.comb += [
                    self.img_stream.data.eq(command.payload.synchronize.cookie),
                    self.img_stream.valid.eq(1),
                ]
                with m.If(self.img_stream.ready):
                    m.d.comb += sync_ack.eq(1)
                    m.next = "Imaging"

        return m


class ImageSerializer(wiring.Component):
    img_stream: In(StreamSignature(unsigned(16)))
    usb_stream: Out(StreamSignature(8))

    def elaborate(self, platform):
        m = Module()

        high = Signal(8)
        with m.FSM():
            with m.State("Low"):
                m.d.comb += self.usb_stream.data.eq(self.img_stream.data[0:8])
                m.d.comb += self.usb_stream.valid.eq(self.img_stream.valid)
                m.d.sync += high.eq(self.img_stream.data[8:16])
                with m.If(self.usb_stream.ready & self.img_stream.valid):
                    m.next = "High"

            with m.State("High"):
                m.d.comb += self.usb_stream.data.eq(high)
                m.d.comb += self.usb_stream.valid.eq(high)
                with m.If(self.usb_stream.ready):
                    m.next = "Low"

        return m


class OBISubtarget(wiring.Component):
    def __init__(self, *, out_fifo, in_fifo):
        self.out_fifo = out_fifo
        self.in_fifo  = in_fifo

    def elaborate(self, platform):
        m = Module()

        m.submodules.parser     = parser     = CommandParser()
        m.submodules.executor   = executor   = CommandExecutor()
        m.submodules.serializer = serializer = ImageSerializer()

        wiring.connect(m, parser.cmd_stream, executor.cmd_stream)
        wiring.connect(m, executor.img_stream, serializer.img_stream)

        m.d.comb += [
            parser.usb_stream.data.eq(self.out_fifo.r_data),
            parser.usb_stream.valid.eq(self.out_fifo.r_rdy),
            self.out_fifo.r_en.eq(parser.usb_stream.ready),
            self.in_fifo.w_data.eq(serializer.usb_stream.data),
            self.in_fifo.w_en.eq(serializer.usb_stream.valid),
            serializer.usb_stream.ready.eq(self.in_fifo.w_rdy),
        ]

        m.d.comb += [
            # platform.request("blah").eq(executor.bus.data_o) ...
        ]
