if "glasgow" in __name__: ## running as applet
    from ..scan_gen_components.addresses import *
else:
    from addresses import *


test_vector_points = [
    [2000, 1000, 13], ## X, Y, D
    [1000, 2000, 13],
    [3000, 2500, 13],
]

#  ◼︎◻︎◼︎◻︎◼︎
#  ◻︎◼︎◻︎◼︎◻︎
#  ◼︎◻︎◼︎◻︎◼︎
#  ◻︎◼︎◻︎◼︎◻︎
#  ◼︎◻︎◼︎◻︎◼︎


# see access.simulation.demultiplexer -> SimulationDemultiplexer
def _fifo_write(fifo, data):
    assert (yield fifo.w_rdy)
    yield fifo.w_data.eq(data)
    yield fifo.w_en.eq(1)
    yield
    yield fifo.w_en.eq(0)
    yield

def _fifo_read(fifo):
    assert (yield fifo.r_rdy)
    value = (yield fifo.r_data)
    yield fifo.r_en.eq(1)
    yield
    yield fifo.r_en.eq(0)
    yield
    return value

def _fifo_write_data_address(fifo, address, data):
    bytes_data = Const(data, unsigned(16))
    print("address:", address)
    yield from _fifo_write(fifo, address)
    print("data 1:", bytes_data[0:8])
    yield from _fifo_write(fifo, bytes_data[0:8])
    print("data 2:", bytes_data[8:15])
    yield from _fifo_write(fifo, bytes_data[8:15])

def _fifo_write_vector_point(n, fifo):
    x, y, d = n
    x = Const(int(x), unsigned(16))
    y = Const(int(y), unsigned(16))
    d = Const(int(d), unsigned(16))
    yield from _fifo_write(fifo, x[0:8])
    yield from _fifo_write(fifo, x[8:16])
    yield from _fifo_write(fifo, y[0:8])
    yield from _fifo_write(fifo, y[8:16])
    yield from _fifo_write(fifo, d[0:8])
    yield from _fifo_write(fifo, d[8:16])




