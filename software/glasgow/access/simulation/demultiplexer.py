import types
from amaranth import *

from ...support.logging import *
from .. import AccessDemultiplexer, AccessDemultiplexerInterface


class SimulationDemultiplexer(AccessDemultiplexer):
    async def claim_interface(self, applet, mux_interface, args, pull_low=set(), pull_high=set()):
        return SimulationDemultiplexerInterface(self.device, applet, mux_interface)

@types.coroutine
def _fifo_read(fifo):
    assert (yield fifo.r_rdy)
    value = (yield fifo.r_data)
    yield fifo.r_en.eq(1)
    yield
    yield fifo.r_en.eq(0)
    yield
    return value

@types.coroutine
def _fifo_write(fifo, data):
    assert (yield fifo.w_rdy)
    yield fifo.w_data.eq(data)
    yield fifo.w_en.eq(1)
    yield
    yield fifo.w_en.eq(0)
    yield


class SimulationDemultiplexerInterface(AccessDemultiplexerInterface):
    def __init__(self, device, applet, mux_interface):
        super().__init__(device, applet)

        self._in_fifo  = mux_interface.in_fifo
        self._out_fifo = mux_interface.out_fifo

    async def cancel(self):
        pass

    async def reset(self):
        pass

    @types.coroutine
    def read(self, length=None):
        data = []
        if length is None:
            while (yield self._in_fifo.r_rdy):
                data.append((yield from _fifo_read(self._in_fifo)))
        else:
            while len(data) < length:
                self.logger.trace("FIFO: need %d bytes", length - len(data))
                print("FIFO: need %d bytes" %(length - len(data)))
                n = 0
                while not (yield self._in_fifo.r_rdy):
                    print("not in fifo r rdy", n)
                    n += 1
                    yield
                    if n >= 70:
                        break
                if n < 29:    
                    data.append((yield from _fifo_read(self._in_fifo)))
                else:
                    break

        data = bytes(data)
        self.logger.trace("FIFO: read <%s>", dump_hex(data))
        print("FIFO: read <%s>" %dump_hex(data))
        return data

    @types.coroutine
    def write(self, data):
        data = bytes(data)
        self.logger.trace("FIFO: write <%s>", dump_hex(data))
        print("FIFO: write <%s>" %dump_hex(data))

        for byte in data:
            n = 0
            while not (yield self._out_fifo.w_rdy):
                #print("not out fifo w_rdy", n)
                n += 1
                yield
                if n >= 30:
                   break
            #if n <= 29:
            yield from _fifo_write(self._out_fifo, byte)
            # else:
            #     break

    async def flush(self):
        pass
