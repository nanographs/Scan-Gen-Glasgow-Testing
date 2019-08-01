# Ref: IEEE Std 1149.1-2001
# Accession: G00018

import struct
import logging
import asyncio
from bitarray import bitarray
from migen import *
from migen.genlib.cdc import MultiReg

from ....support.pyrepl import *
from ....gateware.pads import *
from ....database.jedec import *
from ....arch.jtag import *
from ... import *


class JTAGProbeBus(Module):
    def __init__(self, pads):
        self.tck = Signal(reset=1)
        self.tms = Signal(reset=1)
        self.tdo = Signal(reset=1)
        self.tdi = Signal(reset=1)
        self.trst_z = Signal(reset=0)
        self.trst_o = Signal(reset=1)

        ###

        self.comb += [
            pads.tck_t.oe.eq(1),
            pads.tck_t.o.eq(self.tck),
            pads.tms_t.oe.eq(1),
            pads.tms_t.o.eq(self.tms),
            pads.tdi_t.oe.eq(1),
            pads.tdi_t.o.eq(self.tdi),
        ]
        self.specials += [
            MultiReg(pads.tdo_t.i, self.tdo),
        ]
        if hasattr(pads, "trst_t"):
            self.sync += [
                pads.trst_t.oe.eq(~self.trst_z),
                pads.trst_t.o.eq(~self.trst)
            ]


# Other kinds of adapters are possible, e.g. cJTAG or Spy-Bi-Wire. Applets providing other adapters
# would reuse the interface of JTAGProbeAdapter.
class JTAGProbeAdapter(Module):
    def __init__(self, bus, period_cyc):
        self.stb = Signal()
        self.rdy = Signal()

        self.tms = Signal()
        self.tdo = Signal()
        self.tdi = Signal()
        self.trst_z = bus.trst_z
        self.trst_o = bus.trst_o

        ###

        half_cyc = int(period_cyc // 2)
        timer    = Signal(max=half_cyc)

        self.submodules.fsm = FSM()
        self.fsm.act("TCK-H",
            bus.tck.eq(1),
            If(timer != 0,
                NextValue(timer, timer - 1)
            ).Else(
                If(self.stb,
                    NextValue(timer, half_cyc - 1),
                    NextValue(bus.tms, self.tms),
                    NextValue(bus.tdi, self.tdi),
                    NextState("TCK-L")
                ).Else(
                    self.rdy.eq(1)
                )
            )
        )
        self.fsm.act("TCK-L",
            bus.tck.eq(0),
            If(timer != 0,
                NextValue(timer, timer - 1)
            ).Else(
                NextValue(timer, half_cyc - 1),
                NextValue(self.tdo, bus.tdo),
                NextState("TCK-H")
            )
        )


CMD_MASK       = 0b11110000
CMD_SET_TRST   = 0b00000000
CMD_SHIFT_TMS  = 0b00010000
CMD_SHIFT_TDIO = 0b00100000
# CMD_SET_TRST
BIT_TRST_Z     =       0b01
BIT_TRST_O     =       0b10
# CMD_SHIFT_{TMS,TDIO}
BIT_DATA_OUT   =     0b0001
BIT_DATA_IN    =     0b0010
BIT_LAST       =     0b0100


class JTAGProbeDriver(Module):
    def __init__(self, adapter, out_fifo, in_fifo):
        cmd     = Signal(8)
        count   = Signal(16)
        bitno   = Signal(3)
        align   = Signal(3)
        shreg_o = Signal(8)
        shreg_i = Signal(8)

        self.submodules.fsm = FSM()
        self.fsm.act("RECV-COMMAND",
            If(out_fifo.readable,
                out_fifo.re.eq(1),
                NextValue(cmd, out_fifo.dout),
                NextState("COMMAND")
            )
        )
        self.fsm.act("COMMAND",
            If((cmd & CMD_MASK) == CMD_SET_TRST,
                NextValue(adapter.trst_z, (cmd & BIT_TRST_Z) != 0),
                NextValue(adapter.trst_o, (cmd & BIT_TRST_O) != 0),
                NextState("RECV-COMMAND")
            ).Elif(((cmd & CMD_MASK) == CMD_SHIFT_TMS) |
                   ((cmd & CMD_MASK) == CMD_SHIFT_TDIO),
                NextState("RECV-COUNT-1")
            )
        )
        self.fsm.act("RECV-COUNT-1",
            If(out_fifo.readable,
                out_fifo.re.eq(1),
                NextValue(count[0:8], out_fifo.dout),
                NextState("RECV-COUNT-2")
            )
        )
        self.fsm.act("RECV-COUNT-2",
            If(out_fifo.readable,
                out_fifo.re.eq(1),
                NextValue(count[8:16], out_fifo.dout),
                NextState("RECV-BITS")
            )
        )
        self.fsm.act("RECV-BITS",
            If(count == 0,
                NextState("RECV-COMMAND")
            ).Else(
                If(count > 8,
                    NextValue(bitno, 0)
                ).Else(
                    NextValue(align, 8 - count[:3]),
                    NextValue(bitno, 8 - count[:3])
                ),
                If(cmd & BIT_DATA_OUT,
                    If(out_fifo.readable,
                        out_fifo.re.eq(1),
                        NextValue(shreg_o, out_fifo.dout),
                        NextState("SHIFT-SETUP")
                    )
                ).Else(
                    NextValue(shreg_o, 0b11111111),
                    NextState("SHIFT-SETUP")
                )
            )
        )
        self.fsm.act("SHIFT-SETUP",
            NextValue(adapter.stb, 1),
            If((cmd & CMD_MASK) == CMD_SHIFT_TMS,
                NextValue(adapter.tms, shreg_o[0]),
                NextValue(adapter.tdi, 0),
            ).Else(
                NextValue(adapter.tms, 0),
                If(cmd & BIT_LAST,
                    NextValue(adapter.tms, count == 1)
                ),
                NextValue(adapter.tdi, shreg_o[0]),
            ),
            NextValue(shreg_o, Cat(shreg_o[1:], 1)),
            NextValue(count, count - 1),
            NextValue(bitno, bitno + 1),
            NextState("SHIFT-CAPTURE")
        )
        self.fsm.act("SHIFT-CAPTURE",
            NextValue(adapter.stb, 0),
            If(adapter.rdy,
                NextValue(shreg_i, Cat(shreg_i[1:], adapter.tdo)),
                If(bitno == 0,
                    NextState("SEND-BITS")
                ).Else(
                    NextState("SHIFT-SETUP")
                )
            )
        )
        self.fsm.act("SEND-BITS",
            If(cmd & BIT_DATA_IN,
                If(in_fifo.writable,
                    in_fifo.we.eq(1),
                    If(count == 0,
                        in_fifo.din.eq(shreg_i >> align)
                    ).Else(
                        in_fifo.din.eq(shreg_i)
                    ),
                    NextState("RECV-BITS")
                )
            ).Else(
                NextState("RECV-BITS")
            )
        )


class JTAGProbeSubtarget(Module):
    def __init__(self, pads, out_fifo, in_fifo, period_cyc):
        self.submodules.bus     = JTAGProbeBus(pads)
        self.submodules.adapter = JTAGProbeAdapter(self.bus, period_cyc)
        self.submodules.driver  = JTAGProbeDriver(self.adapter, out_fifo, in_fifo)


class JTAGInterface:
    def __init__(self, interface, logger):
        self.lower   = interface
        self._logger = logger
        self._level  = logging.DEBUG if self._logger.name == __name__ else logging.TRACE

        self._state      = "Unknown"
        self._current_ir = None

    def _log_l(self, message, *args):
        self._logger.log(self._level, "JTAG-L: " + message, *args)

    def _log_h(self, message, *args):
        self._logger.log(self._level, "JTAG-H: " + message, *args)

    # Low-level operations

    async def set_trst(self, active):
        if active is None:
            self._log_l("set trst=z")
            await self.lower.write(struct.pack("<B",
                CMD_SET_TRST|BIT_TRST_Z))
        else:
            self._log_l("set trst=%d", active)
            await self.lower.write(struct.pack("<B",
                CMD_SET_TRST|(BIT_TRST_O if active else 0)))

    async def shift_tms(self, tms_bits):
        tms_bits = bitarray(tms_bits, endian="little")
        self._log_l("shift tms=<%s>", tms_bits.to01())
        await self.lower.write(struct.pack("<BH",
            CMD_SHIFT_TMS|BIT_DATA_OUT, len(tms_bits)))
        await self.lower.write(tms_bits.tobytes())

    def _shift_last(self, last):
        if last:
            if self._state == "Shift-IR":
                self._log_l("state Shift-IR → Exit1-IR")
                self._state = "Exit1-IR"
            elif self._state == "Shift-DR":
                self._log_l("state Shift-DR → Exit1-DR")
                self._state = "Exit1-DR"

    async def shift_tdio(self, tdi_bits, last=True):
        assert self._state in ("Shift-IR", "Shift-DR")
        tdi_bits = bitarray(tdi_bits, endian="little")
        tdo_bits = bitarray(endian="little")
        self._log_l("shift tdio-i=<%s>", tdi_bits.to01())
        await self.lower.write(struct.pack("<BH",
            CMD_SHIFT_TDIO|BIT_DATA_IN|BIT_DATA_OUT|(BIT_LAST if last else 0),
            len(tdi_bits)))
        tdi_bytes = tdi_bits.tobytes()
        await self.lower.write(tdi_bytes)
        tdo_bytes = await self.lower.read(len(tdi_bytes))
        tdo_bits.frombytes(bytes(tdo_bytes))
        while len(tdo_bits) > len(tdi_bits): tdo_bits.pop()
        self._log_l("shift tdio-o=<%s>", tdo_bits.to01())
        self._shift_last(last)
        return tdo_bits

    async def shift_tdi(self, tdi_bits, last=True):
        assert self._state in ("Shift-IR", "Shift-DR")
        tdi_bits = bitarray(tdi_bits, endian="little")
        self._log_l("shift tdi=<%s>", tdi_bits.to01())
        await self.lower.write(struct.pack("<BH",
            CMD_SHIFT_TDIO|BIT_DATA_OUT|(BIT_LAST if last else 0),
            len(tdi_bits)))
        tdi_bytes = tdi_bits.tobytes()
        await self.lower.write(tdi_bytes)
        self._shift_last(last)

    async def shift_tdo(self, count, last=True):
        assert self._state in ("Shift-IR", "Shift-DR")
        tdo_bits = bitarray(endian="little")
        await self.lower.write(struct.pack("<BH",
            CMD_SHIFT_TDIO|BIT_DATA_IN|(BIT_LAST if last else 0),
            count))
        tdo_bytes = await self.lower.read((count + 7) // 8)
        tdo_bits.frombytes(bytes(tdo_bytes))
        while len(tdo_bits) > count: tdo_bits.pop()
        self._log_l("shift tdo=<%s>", tdo_bits.to01())
        self._shift_last(last)
        return tdo_bits

    async def pulse_tck(self, count):
        assert self._state in ("Run-Test/Idle", "Shift-IR", "Shift-DR", "Pause-IR", "Pause-DR")
        self._log_l("pulse tck count=%d", count)
        while count > 0xffff:
            await self.lower.write(struct.pack("<BH",
                CMD_SHIFT_TDIO, 0xffff))
            count -= 0xffff
        await self.lower.write(struct.pack("<BH",
            CMD_SHIFT_TDIO, count))

    # State machine transitions

    async def enter_test_logic_reset(self, force=True):
        if force:
            self._log_l("state * → Test-Logic-Reset")
        elif self._state != "Test-Logic-Reset":
            self._log_l("state %s → Test-Logic-Reset", self._state)
        else:
            return

        await self.shift_tms("11111")
        self._state = "Test-Logic-Reset"

    async def enter_run_test_idle(self):
        if self._state == "Run-Test/Idle": return

        self._log_l("state %s → Run-Test/Idle", self._state)
        if self._state == "Test-Logic-Reset":
            await self.shift_tms("0")
        elif self._state in ("Exit1-IR", "Exit1-DR"):
            await self.shift_tms("10")
        elif self._state in ("Pause-IR", "Pause-DR"):
            await self.shift_tms("110")
        elif self._state in ("Update-IR", "Update-DR"):
            await self.shift_tms("0")
        else:
            assert False
        self._state = "Run-Test/Idle"

    async def enter_shift_ir(self):
        if self._state == "Shift-IR": return

        self._log_l("state %s → Shift-IR", self._state)
        if self._state == "Test-Logic-Reset":
            await self.shift_tms("01100")
        elif self._state in ("Run-Test/Idle", "Update-IR", "Update-DR"):
            await self.shift_tms("1100")
        elif self._state in ("Pause-DR"):
            await self.shift_tms("111100")
        elif self._state in ("Pause-IR"):
            await self.shift_tms("10")
        else:
            assert False
        self._state = "Shift-IR"

    async def enter_pause_ir(self):
        if self._state == "Pause-IR": return

        self._log_l("state %s → Pause-IR", self._state)
        if self._state == "Exit1-IR":
            await self.shift_tms("0")
        else:
            assert False
        self._state = "Pause-IR"

    async def enter_update_ir(self):
        if self._state == "Update-IR": return

        self._log_l("state %s → Update-IR", self._state)
        if self._state == "Shift-IR":
            await self.shift_tms("11")
        elif self._state == "Exit1-IR":
            await self.shift_tms("1")
        else:
            assert False
        self._state = "Update-IR"

    async def enter_shift_dr(self):
        if self._state == "Shift-DR": return

        self._log_l("state %s → Shift-DR", self._state)
        if self._state == "Test-Logic-Reset":
            await self.shift_tms("0100")
        elif self._state in ("Run-Test/Idle", "Update-IR", "Update-DR"):
            await self.shift_tms("100")
        elif self._state in ("Pause-IR"):
            await self.shift_tms("11100")
        elif self._state in ("Pause-DR"):
            await self.shift_tms("10")
        else:
            assert False
        self._state = "Shift-DR"

    async def enter_pause_dr(self):
        if self._state == "Pause-DR": return

        self._log_l("state %s → Pause-DR", self._state)
        if self._state == "Exit1-DR":
            await self.shift_tms("0")
        else:
            assert False
        self._state = "Pause-DR"

    async def enter_update_dr(self):
        if self._state == "Update-DR": return

        self._log_l("state %s → Update-DR", self._state)
        if self._state == "Shift-DR":
            await self.shift_tms("11")
        elif self._state == "Exit1-DR":
            await self.shift_tms("1")
        else:
            assert False
        self._state = "Update-DR"

    # High-level register manipulation

    async def pulse_trst(self):
        self._log_h("pulse trst")
        await self.set_trst(True)
        # IEEE 1149.1 3.6.1 (d): "To ensure deterministic operation of the test logic, TMS should
        # be held at 1 while the signal applied at TRST* changes from [active] to [inactive]."
        await self.shift_tms("1")
        await self.set_trst(False)
        self._current_ir = None

    async def test_reset(self):
        self._log_h("test reset")
        await self.enter_test_logic_reset()
        await self.enter_run_test_idle()
        self._current_ir = None

    async def run_test_idle(self, count):
        self._log_h("run-test/idle count=%d", count)
        await self.enter_run_test_idle()
        await self.pulse_tck(count)

    async def exchange_ir(self, data):
        self._current_ir = data = bitarray(data, endian="little")
        self._log_h("exchange ir")
        await self.enter_shift_ir()
        data = await self.shift_tdio(data)
        await self.enter_update_ir()
        return data

    async def read_ir(self, count):
        self._current_ir = bitarray("1", endian="little") * count
        await self.enter_shift_ir()
        data = await self.shift_tdo(count)
        await self.enter_update_ir()
        self._log_h("read ir=<%s>", data.to01())
        return data

    async def write_ir(self, data, elide=True):
        if data == self._current_ir:
            self._log_h("write ir (elided)")
            return
        self._current_ir = data = bitarray(data, endian="little")
        self._log_h("write ir=<%s>", data.to01())
        await self.enter_shift_ir()
        await self.shift_tdi(data)
        await self.enter_update_ir()

    async def exchange_dr(self, data):
        self._log_h("exchange dr")
        await self.enter_shift_dr()
        data = await self.shift_tdio(data)
        await self.enter_update_dr()
        return data

    async def read_dr(self, count, idempotent=False):
        await self.enter_shift_dr()
        data = await self.shift_tdo(count, last=not idempotent)
        if idempotent:
            # Shift what we just read back in. This is useful to avoid disturbing any bits
            # in R/W DRs when we go through Update-DR.
            await self.shift_tdi(data)
        await self.enter_update_dr()
        if idempotent:
            self._log_h("read idempotent dr=<%s>", data.to01())
        else:
            self._log_h("read dr=<%s>", data.to01())
        return data

    async def write_dr(self, data):
        data = bitarray(data, endian="little")
        self._log_h("write dr=<%s>", data.to01())
        await self.enter_shift_dr()
        await self.shift_tdi(data)
        await self.enter_update_dr()

    # Specialized operations

    async def _scan_xr(self, xr, max_length, zero_ok=False):
        assert xr in ("ir", "dr")
        self._log_h("scan %s length", xr)

        if xr ==  "ir":
            await self.enter_shift_ir()
        if xr ==  "dr":
            await self.enter_shift_dr()

        try:
            # Fill the entire register chain with ones.
            data = await self.shift_tdio(bitarray("1") * max_length, last=False)

            length = 0
            while length < max_length:
                out = await self.shift_tdio(bitarray("0"), last=False)
                if out[0] == 0:
                    break
                length += 1
            else:
                self._log_h("overlong %s", xr)
                return

            self._log_h("scan %s length=%d data=<%s>", xr, length, data[:length].to01())
            return data[:length]

        finally:
            if xr == "ir":
                # Fill the register with BYPASS instructions.
                await self.shift_tdi(bitarray("1") * length, last=True)
            if xr == "dr":
                # Restore the old contents, just in case this matters.
                await self.shift_tdi(data[:length], last=True)

            await self.enter_run_test_idle()

    async def scan_ir(self, max_length):
        return await self._scan_xr("ir", max_length)

    async def scan_dr(self, max_length):
        return await self._scan_xr("dr", max_length)

    async def scan_ir_length(self, max_length):
        data = await self.scan_ir(max_length)
        if data is None: return
        return len(data)

    async def scan_dr_length(self, max_length, zero_ok=False):
        data = await self.scan_dr(max_length)
        if data is None: return
        length = len(data)
        assert zero_ok or length > 0
        return length

    def segment_idcodes(self, dr_value):
        idcodes = []
        index = 0
        while index < len(dr_value):
            if dr_value[index]:
                if len(dr_value) - index >= 32:
                    idcode_bits = dr_value[index:index + 32]
                    idcode, = struct.unpack("<L", idcode_bits.tobytes())
                    self._log_h("found idcode=<%08x>", idcode)
                    idcodes.append(idcode)
                    index += 32
                else:
                    self._log_h("found truncated idcode=<%s>", dr_value[index:].to01())
                    return
            else:
                self._log_h("found bypass")
                idcodes.append(None)
                index += 1

        return idcodes

    def segment_irs(self, ir_value, count=None):
        if ir_value[0:2] != bitarray("10"):
            self._log_h("ir does not start with 10")

        irs = []
        ir_offset = 0
        if count == 1:
            # 1 TAP case; the entire IR belongs to the only TAP we have.
            ir_length = len(ir_value)
            self._log_h("found ir[%d] (1-tap)", ir_length)
            irs.append((ir_offset, ir_length))
        else:
            # >1 TAP case; there is no way to segment IR without knowledge of specific devices
            # involved, but an IR always starts with 10, and we can use this to try and guess
            # the IR segmentation. Our segmentation is pessimistic, i.e. it always detects either
            # as many IRs as TAPs, or more IRs than TAPs.
            ir_starts = ir_value.search(bitarray("10"))
            for ir_start0, ir_start1 in zip(ir_starts, ir_starts[1:] + [len(ir_value)]):
                ir_length = ir_start1 - ir_start0
                self._log_h("found ir[%d] (n-tap)", ir_length)
                irs.append((ir_offset, ir_length))
                ir_offset += ir_length

        if count is not None and len(irs) != count:
            self._log_h("ir count does not match idcode count")
            return

        return irs

    async def select_tap(self, tap, max_ir_length=128, max_dr_length=1024):
        await self.test_reset()

        dr_value = await self.scan_dr(max_dr_length)
        if dr_value is None:
            return

        idcodes = self.segment_idcodes(dr_value)
        if idcodes is None:
            return

        ir_value = await self.scan_ir(max_ir_length)
        if ir_value is None:
            return

        irs = self.segment_irs(ir_value, count=len(idcodes))
        if not irs:
            return

        if tap >= len(irs):
            self._log_h("tap %d not present on chain")
            return

        ir_offset, ir_length = irs[tap]
        total_ir_length = sum(length for offset, length in irs)

        dr_offset, dr_length = tap, 1
        total_dr_length = len(idcodes)

        bypass = bitarray("1", endian="little")
        def affix(offset, length, total_length):
            prefix = bypass * offset
            suffix = bypass * (total_length - offset - length)
            return prefix, suffix

        return TAPInterface(self, ir_length,
            *affix(ir_offset, ir_length, total_ir_length),
            *affix(dr_offset, dr_length, total_dr_length))


class TAPInterface:
    def __init__(self, lower, ir_length, ir_prefix, ir_suffix, dr_prefix, dr_suffix):
        self.lower = lower
        self.ir_length    = ir_length
        self._ir_prefix   = ir_prefix
        self._ir_suffix   = ir_suffix
        self._ir_overhead = len(ir_prefix) + len(ir_suffix)
        self._dr_prefix   = dr_prefix
        self._dr_suffix   = dr_suffix
        self._dr_overhead = len(dr_prefix) + len(dr_suffix)

    async def test_reset(self):
        await self.lower.test_reset()

    async def run_test_idle(self, count):
        await self.lower.run_test_idle(count)

    async def exchange_ir(self, data):
        data = bitarray(data, endian="little")
        assert len(data) == self.ir_length
        data = await self.lower.exchange_ir(self._ir_prefix + data + self._ir_suffix)
        if self._ir_suffix:
            return data[len(self._ir_prefix):-len(self._ir_suffix)]
        else:
            return data[len(self._ir_prefix):]

    async def read_ir(self):
        data = await self.lower.read_ir(self._ir_overhead + self.ir_length)
        if self._ir_suffix:
            return data[len(self._ir_prefix):-len(self._ir_suffix)]
        else:
            return data[len(self._ir_prefix):]

    async def write_ir(self, data):
        data = bitarray(data, endian="little")
        assert len(data) == self.ir_length
        await self.lower.write_ir(self._ir_prefix + data + self._ir_suffix)

    async def exchange_dr(self, data):
        data = bitarray(data, endian="little")
        data = await self.lower.exchange_dr(self._dr_prefix + data + self._dr_suffix)
        if self._dr_suffix:
            return data[len(self._dr_prefix):-len(self._dr_suffix)]
        else:
            return data[len(self._dr_prefix):]

    async def read_dr(self, count, idempotent=False):
        data = await self.lower.read_dr(self._dr_overhead + count, idempotent=idempotent)
        if self._dr_suffix:
            return data[len(self._dr_prefix):-len(self._dr_suffix)]
        else:
            return data[len(self._dr_prefix):]

    async def write_dr(self, data):
        data = bitarray(data, endian="little")
        await self.lower.write_dr(self._dr_prefix + data + self._dr_suffix)

    async def scan_dr_length(self, max_length, zero_ok=False):
        length = await self.lower.scan_dr_length(max_length=self._dr_overhead + max_length,
                                                 zero_ok=zero_ok)
        if length is None or length == 0:
            return
        assert length >= self._dr_overhead
        assert zero_ok or length - self._dr_overhead > 0
        return length - self._dr_overhead


class JTAGProbeApplet(GlasgowApplet, name="jtag-probe"):
    logger = logging.getLogger(__name__)
    help = "test integrated circuits via IEEE 1149.1 JTAG"
    description = """
    Identify, test and debug integrated circuits and board assemblies via IEEE 1149.1 JTAG.
    """
    has_custom_repl = True

    __pins = ("tck", "tms", "tdi", "tdo", "trst")

    @classmethod
    def add_build_arguments(cls, parser, access):
        super().add_build_arguments(parser, access)

        for pin in ("tck", "tms", "tdi", "tdo"):
            access.add_pin_argument(parser, pin, default=True)
        access.add_pin_argument(parser, "trst")

        parser.add_argument(
            "-f", "--frequency", metavar="FREQ", type=int, default=100,
            help="set clock period to FREQ kHz (default: %(default)s)")

    def build(self, target, args):
        self.mux_interface = iface = target.multiplexer.claim_interface(self, args)
        iface.add_subtarget(JTAGProbeSubtarget(
            pads=iface.get_pads(args, pins=self.__pins),
            out_fifo=iface.get_out_fifo(),
            in_fifo=iface.get_in_fifo(),
            period_cyc=target.sys_clk_freq // (args.frequency * 1000),
        ))

    async def run(self, device, args, reset=True):
        iface = await device.demultiplexer.claim_interface(self, self.mux_interface, args)
        jtag_iface = JTAGInterface(iface, self.logger)
        if reset:
            # If we have a defined TRST#, enable the driver and reset the TAPs to a good state.
            await jtag_iface.pulse_trst()
        return jtag_iface

    @classmethod
    def add_interact_arguments(cls, parser):
        parser.add_argument(
            "--max-ir-length", metavar="LENGTH", type=int, default=128,
            help="give up scanning IR after LENGTH bits")
        parser.add_argument(
            "--max-dr-length", metavar="LENGTH", type=int, default=1024,
            help="give up scanning DR after LENGTH bits")

        # TODO(py3.7): add required=True
        p_operation = parser.add_subparsers(dest="operation", metavar="OPERATION")

        p_scan = p_operation.add_parser(
            "scan", help="scan JTAG chain and attempt to identify devices",
            description="""
            Reset the JTAG TAPs and shift IDCODE or BYPASS register values out to determine
            the count and (hopefully) identity of the devices in the scan chain.
            """)

        p_enumerate_ir = p_operation.add_parser(
            "enumerate-ir", help="use heuristics to enumerate JTAG IR values (DANGEROUS)",
            description="""
            THIS COMMAND CAN HAVE POTENTIALLY DESTRUCTIVE CONSEQUENCES.

            IEEE 1149.1 requires that any unimplemented IR value select the BYPASS DR.
            By exploiting this, and measuring DR lengths for every possible IR value,
            we can discover DR lengths for every IR value.

            Note that discovering DR length requires going through Capture-DR and Update-DR
            states. While we strive to be as unobtrustive as possible by shifting the original
            DR value back after we discover DR length, there is no guarantee that updating DR
            with the captured DR value is side effect free. As such, this command can potentially
            have UNPREDICTABLE side effects that, due to the nature of JTAG, can permanently
            damage your target. Use with care.

            Note that while unimplemented IR values are required to select the BYPASS DR,
            in practice, many apparently (from the documentation) unimplemented IR values
            would actually select reserved DRs instead, which can lead to confusion. In some
            cases they even select a constant 0 level on TDO!
            """)
        p_enumerate_ir.add_argument(
            "tap_indexes", metavar="INDEX", type=int, nargs="+",
            help="enumerate IR values for TAP #INDEX")

        # This one is identical to run-repl, and is just for consistency when using the subcommands
        # tap-repl and jtag-repl alternately.
        p_jtag_repl = p_operation.add_parser(
            "jtag-repl", help="drop into Python REPL")

        p_tap_repl = p_operation.add_parser(
            "tap-repl", help="select a TAP and drop into Python REPL")
        p_tap_repl.add_argument(
            "tap_index", metavar="INDEX", type=int, default=0, nargs="?",
            help="select TAP #INDEX for communication (default: %(default)s)")

    async def interact(self, device, args, jtag_iface):
        if args.operation in ("scan", "enumerate-ir"):
            await jtag_iface.test_reset()

            dr_value = await jtag_iface.scan_dr(max_length=args.max_dr_length)
            if dr_value is None:
                self.logger.warning("DR length scan did not terminate")
                return
            self.logger.info("shifted %d-bit DR=<%s>", len(dr_value), dr_value.to01())

            ir_value = await jtag_iface.scan_ir(max_length=args.max_ir_length)
            if ir_value is None:
                self.logger.warning("IR length scan did not terminate")
                return
            self.logger.info("shifted %d-bit IR=<%s>", len(ir_value), ir_value.to01())

            idcodes = jtag_iface.segment_idcodes(dr_value)
            if not idcodes:
                self.logger.warning("DR segmentation discovered no devices")
                return
            self.logger.info("DR segmentation discovered %d devices", len(idcodes))

            irs = jtag_iface.segment_irs(ir_value, count=len(idcodes))

        if args.operation == "scan":
            if not irs:
                self.logger.warning("automatic IR segmentation failed")
                irs = [(None, "?") for _ in idcodes]

            for tap_index, (idcode_value, (ir_offset, ir_length)) in enumerate(zip(idcodes, irs)):
                if idcode_value is None:
                    self.logger.info("TAP #%d: IR[%s] BYPASS",
                                     tap_index, ir_length)
                else:
                    idcode   = DR_IDCODE.from_int(idcode_value)
                    mfg_name = jedec_mfg_name_from_bank_num(idcode.mfg_id >> 7,
                                                            idcode.mfg_id & 0x7f) or \
                                    "unknown"
                    self.logger.info("TAP #%d: IR[%s] IDCODE=%#010x",
                                     tap_index, ir_length, idcode_value)
                    self.logger.info("manufacturer=%#05x (%s) part=%#06x version=%#03x",
                                     idcode.mfg_id, mfg_name, idcode.part_id, idcode.version)

        if args.operation == "enumerate-ir":
            if not irs:
                self.logger.error("automatic IR segmentation failed")
                return

            for tap_index in args.tap_indexes or range(len(irs)):
                ir_offset, ir_length = irs[tap_index]
                self.logger.info("TAP #%d: IR[%d]", tap_index, ir_length)

                tap_iface = await jtag_iface.select_tap(tap_index,
                                                        args.max_ir_length, args.max_dr_length)
                if not tap_iface:
                    raise GlasgowAppletError("cannot select TAP #%d" % tap_index)

                for ir_value in range(0, (1 << ir_length)):
                    ir_value = bitarray([ir_value & (1 << bit) for bit in range(ir_length)],
                                        endian="little")
                    await tap_iface.test_reset()
                    await tap_iface.write_ir(ir_value)
                    dr_length = await tap_iface.scan_dr_length(max_length=args.max_dr_length,
                                                               zero_ok=True)
                    if dr_length is None:
                        level = logging.ERROR
                        dr_length = "?"
                    elif dr_length == 0:
                        level = logging.WARN
                    elif dr_length == 1:
                        level = logging.DEBUG
                    else:
                        level = logging.INFO
                    self.logger.log(level, "  IR=%s DR[%s]", ir_value.to01(), dr_length)

        if args.operation == "jtag-repl":
            await AsyncInteractiveConsole(locals={"iface":jtag_iface}).interact()

        if args.operation == "tap-repl":
            tap_iface = await jtag_iface.select_tap(args.tap_index,
                                                    args.max_ir_length, args.max_dr_length)
            if not tap_iface:
                self.logger.error("cannot select TAP #%d" % args.tap_index)
                return

            await AsyncInteractiveConsole(locals={"iface":tap_iface}).interact()

# -------------------------------------------------------------------------------------------------

class JTAGProbeAppletTestCase(GlasgowAppletTestCase, applet=JTAGProbeApplet):
    @synthesis_test
    def test_build(self):
        self.assertBuilds()
