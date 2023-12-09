if "glasgow" in __name__: ## running as applet
    from ..scan_gen_components.addresses import *
else:
    from addresses import *

short_test_vector_points = [
    [2000,1000,2],
    [1000,1000,2],
    [2500,1500,3],
    [2000,1000,2],
    [1000,1000,4],
    [2500,1500,3],
    [2000,1000,2],
    [1000,1000,5],
    [2500,1500,3],
]

test_vector_points = [
    [2000, 1000, 30], ## X, Y, D
    [1000, 2000, 40],
    [3000, 2500, 50],
    [4000, 1000, 3], ## X, Y, D
    [10000, 2000, 4],
    [10300, 2500, 5],
    [2000, 10300, 30], ## X, Y, D
    [10010, 2000, 10],
    [12000, 2500, 5],
    [10300, 2500, 5],
    [2000, 10300, 30], ## X, Y, D
    [8010, 2000, 10],
    [12000, 2500, 50],
    [2000, 1000, 30], ## X, Y, D
    [1000, 2000, 40],
    [300, 2500, 50],
    [12000, 1000, 15], ## X, Y, D
    [10000, 2000, 20],
]

#  ◼︎◻︎◼︎◻︎◼︎
#  ◻︎◼︎◻︎◼︎◻︎
#  ◼︎◻︎◼︎◻︎◼︎
#  ◻︎◼︎◻︎◼︎◻︎
#  ◼︎◻︎◼︎◻︎◼︎

def test_raster_pattern_checkerboard(x_width, y_height):
    points = []
    for y in range(y_height):
        for x in range(x_width):
            if y%2 == 0:
                if x%2 == 0:
                    points.append(5)
                else:
                    points.append(0)
            else:
                if x%2 == 0:
                    points.append(0)
                else:
                    points.append(5)
    return points




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


def hilbert():
    stream = open("hilbert.txt")
    nstream = []
    for n in stream:
        data = eval(n.strip(",\n"))
        #print(data)
        nstream.append(data)

    print(nstream)


if __name__ == "__main__":
    test_raster_pattern_checkerboard(6, 7)



