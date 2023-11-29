import amaranth
from amaranth import *
from amaranth.sim import Simulator


### with inspiration from https://github.com/maia-sdr/maia-sdr/blob/main/maia-hdl/maia_hdl/packer.py

class TwoByteInbox(Elaboratable):
    '''
    Parameters:
        Input: An 8 bit value, provided by a data stream
    
    Attributes:
        Value: A 16 bit value, to be synthesized from two subsequent 8 bit values
        Parsing: When True, the two-byte-parsing state machine is enabled
        Flag: When True, a complete 16 bit value has been recieved

    States:
        First byte: Flag is False, data is incomplete
        Second byte: Flag is True, data is complete

    Flag:    ___-_-
    Parsing: __----
    '''
    def __init__(self):
        self.input = Signal(8)
        self.first_byte = Signal(8)
        self.value = Signal(16) 
        self.parsing = Signal()  ## asserted when input is valid
        self.flag = Signal() ## asserted when value is valid
        self.last_byte = Signal()
    def elaborate(self, platform):
        m = Module()

        with m.FSM() as fsm:
            with m.State("First Byte"):
                m.d.comb += self.flag.eq(0)
                m.d.sync += self.first_byte.eq(self.input)
                with m.If(self.parsing):
                    m.next = "Second Byte"
            with m.State("Second Byte"):
                m.d.comb += self.value.eq(Cat(self.first_byte, self.input))
                #m.d.sync += self.parsing.eq(0)
                m.d.comb += self.flag.eq(1)
                m.d.comb += self.last_byte.eq(1)
                
                with m.If(self.parsing):
                    m.next = "First Byte"

        return m
    def ports(self):
        return [self.flag, self.parsing, self.value]
    


class TwoByteOutbox(Elaboratable):
    '''
    Parameters:
        Input: A 16 bit value, provided by a data stream
        Value: An 8 bit value, to be written into an in-fifo

    Parsing: __--
    Flag:    ___-

    '''
    def __init__(self):
        self.input = Signal(16)
        self.value = Signal(8) 
        self.parsing = Signal() ## asserted when input is valid
        self.flag = Signal() ## asserted when both bytes of value have been parsed
    def elaborate(self, platform):
        m = Module()

        with m.FSM() as fsm:
            with m.State("First Byte"):
                m.d.comb += self.value.eq(self.input[0:7])
                with m.If(self.parsing):
                    m.next = "Second Byte"
            with m.State("Second Byte"):
                m.d.comb += self.value.eq(self.input[7:15])
                m.d.comb += self.flag.eq(1)
                #m.d.sync += self.parsing.eq(0)
                with m.If(self.parsing):
                    m.next = "First Byte"

        return m



class Box(Elaboratable):
    '''
    A place to put data while passing it from one module to the next
    Inputs:
        Flag_In: Asserted when value will be set to new data next cycle
        Flag_Out: Asserted when value has been read, and can be overwritten next cycle

    Flag_In:  _-_____
    Flag:     __----_
    Flag_Out: _____-_
    '''
    def __init__(self):
        self.value = Signal(16)
        self.flag = Signal()
        self.flag_out = Signal()
        self.flag_in = Signal()
    def elaborate(self, platform):
        m = Module()

        with m.If(self.flag_in):
            m.d.sync += self.flag.eq(1)
        with m.If(self.flag_out):
            m.d.sync += self.flag.eq(0)

        return m


def test_twobyteinbox():
    dut = TwoByteInbox()

    def bench():
        data = Const(2500, unsigned(16))
        yield dut.input.eq(data[0:8])
        yield dut.parsing.eq(1)
        yield
        yield dut.input.eq(data[8:15])
        yield dut.parsing.eq(1)
        yield

    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("2bytein_sim.vcd"):
        sim.run()

def test_twobyteoutbox():
    input = Signal(16)
    dut = TwoByteOutbox(input)

    def bench():
        for n in range(len(test_pixel_stream)):
            print(test_pixel_stream[n])
            yield dut.parsing.eq(1)
            yield dut.input.eq(Const(test_pixel_stream[n],shape=16))
            yield
            yield

    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("2byteout_sim.vcd"):
        sim.run()

if __name__ == "__main__":
    test_twobyteinbox()