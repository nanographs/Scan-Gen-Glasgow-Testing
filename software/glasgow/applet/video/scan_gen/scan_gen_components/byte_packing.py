import amaranth
from amaranth import *

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
    def __init__(self, input):
        self.input = input 
        self.value = Signal(16) 
        self.parsing = Signal() ## External "enable" for the state machine
        self.flag = Signal()
        self.last_byte = Signal()
    def elaborate(self, platform):
        m = Module()
        

        with m.If(self.parsing):
            #m.d.sync += self.flag.eq(0)
            with m.FSM() as fsm:
                with m.State("First Byte"):
                    m.d.sync += self.flag.eq(0)
                    m.d.sync += self.value[0:7].eq(self.input)
                    m.next = "Second Byte"
                with m.State("Second Byte"):
                    m.d.sync += self.value[7:15].eq(self.input)
                    m.d.sync += self.parsing.eq(0)
                    m.d.sync += self.flag.eq(1)
                    m.d.comb += self.last_byte.eq(1)
                    m.next = "First Byte"

        return m
    def ports(self):
        return [self.flag, self.parsing, self.value]
    


class TwoByteOutbox(Elaboratable):
    '''
    Parameters:
        Input: A 16 bit value, provided by a data stream

    '''
    def __init__(self, input):
        self.input = input 
        self.value = Signal(8) 
        self.parsing = Signal() ## External "enable" for the state machine
        self.flag = Signal()
    def elaborate(self, platform):
        m = Module()

        with m.If(self.parsing):
            m.d.sync += self.flag.eq(0)
            with m.FSM() as fsm:
                with m.State("First Byte"):
                    m.d.comb += self.value.eq(self.input[0:7])
                    m.next = "Second Byte"
                with m.State("Second Byte"):
                    m.d.comb += self.value.eq(self.input[7:15])
                    m.d.sync += self.flag.eq(1)
                    m.d.sync += self.parsing.eq(0)
                    m.next = "First Byte"

        return m


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