if "glasgow" in __name__: ## running as applet
    from ..scan_gen_components.addresses import *
else:
    from addresses import *

test_vector_points = [
    [2000, 1000, 30],
    [1000, 2000, 40],
    [3000, 2500, 50],
]

basic_vector_stream = [
    [Vector_Address.X, 1000], #X, 1000
    [Vector_Address.Y, 2000], #Y, 2000
    [Vector_Address.D, 10],  #D, 50
    [Vector_Address.X, 1250], #X, 1000
    [Vector_Address.Y, 1700], #Y, 2000
    [Vector_Address.D, 11],  #D, 50
    [Vector_Address.X, 1000], #X, 1000
    [Vector_Address.Y, 2000], #Y, 2000
    [Vector_Address.D, 13],  #D, 50
    [Vector_Address.X, 1250], #X, 1000
    [Vector_Address.Y, 1700], #Y, 2000
    [Vector_Address.D, 14],  #D, 50
    [Vector_Address.X, 1100], #X, 1000
    [Vector_Address.Y, 2100], #Y, 2000
    [Vector_Address.D, 10],  #D, 50
    [Vector_Address.X, 1350], #X, 1000
    [Vector_Address.Y, 1700], #Y, 2000
    [Vector_Address.D, 11],  #D, 50
    [Vector_Address.X, 1000], #X, 1000
    [Vector_Address.Y, 2000], #Y, 2000
    [Vector_Address.D, 10],  #D, 50
    [Vector_Address.X, 1250], #X, 1000
    [Vector_Address.Y, 1700], #Y, 2000
    [Vector_Address.D, 11],  #D, 50
    [Vector_Address.X, 1000], #X, 1000
    [Vector_Address.Y, 2000], #Y, 2000
    [Vector_Address.D, 13],  #D, 50
    [Vector_Address.X, 1250], #X, 1000
    [Vector_Address.Y, 1700], #Y, 2000
    [Vector_Address.D, 14],  #D, 50
    [Vector_Address.X, 1100], #X, 1000
    [Vector_Address.Y, 2100], #Y, 2000
    [Vector_Address.D, 10],  #D, 50
    [Vector_Address.X, 1350], #X, 1000
    [Vector_Address.Y, 1700], #Y, 2000
    [Vector_Address.D, 11],  #D, 50
    # [Constant_Raster_Address.X, 15], #X, 1250
    # [Constant_Raster_Address.Y, 25], #Y, 2500
    # [Constant_Raster_Address.D, 12],  #D, 75
    
]


roi_stream = [
    [Constant_Raster_Address.X, 10], #X, 1250
    [Constant_Raster_Address.Y, 12], #Y, 2500
    [Constant_Raster_Address.D, 4],  #D, 75
    [Constant_Raster_Address.LX, 3], #Y, 2500
    [Constant_Raster_Address.LY, 4],  #D, 75
    [Constant_Raster_Address.UX, 8], #Y, 2500
    [Constant_Raster_Address.UY, 9],  #D, 75
    [Constant_Raster_Address.D, 5],  #D, 75
    [Constant_Raster_Address.D, 6],  #D, 75
    [Constant_Raster_Address.D, 7],  #D, 75
    [Constant_Raster_Address.D, 8],  #D, 75
    [Constant_Raster_Address.D, 9],  #D, 75
    [Constant_Raster_Address.D, 10],  #D, 75
    [Constant_Raster_Address.D, 5],  #D, 75
]

vector_then_raster_pattern_stream = [
    [Vector_Address.X, 1000], #X, 1000
    [Vector_Address.Y, 2000], #Y, 2000
    [Vector_Address.D, 13],  #D, 50
    [Vector_Address.X, 1250], #X, 1000
    [Vector_Address.Y, 1700], #Y, 2000
    [Vector_Address.D, 14],  #D, 50
    [Variable_Raster_Address.X, 3], #X, 1250
    [Variable_Raster_Address.Y, 4], #Y, 2500
    [Variable_Raster_Address.D, 10],  #D, 75
    [Variable_Raster_Address.D, 12],  #D, 75
    [Variable_Raster_Address.D, 15],  #D, 75
    [Variable_Raster_Address.D, 17],  #D, 75
]


#  ◼︎◻︎◼︎◻︎◼︎
#  ◻︎◼︎◻︎◼︎◻︎
#  ◼︎◻︎◼︎◻︎◼︎
#  ◻︎◼︎◻︎◼︎◻︎
#  ◼︎◻︎◼︎◻︎◼︎

test_image_as_raster_pattern = [
    [Variable_Raster_Address.X, 4], #X,5
    [Variable_Raster_Address.Y, 4], #Y, 5

    [Variable_Raster_Address.D, 20],  #D, 75
    [Variable_Raster_Address.D, 10],  #D, 75
    [Variable_Raster_Address.D, 20],  #D, 75
    [Variable_Raster_Address.D, 10],  #D, 75
    [Variable_Raster_Address.D, 20],  #D, 75

    [Variable_Raster_Address.D, 10],  #D, 75
    [Variable_Raster_Address.D, 20],  #D, 75
    [Variable_Raster_Address.D, 10],  #D, 75
    [Variable_Raster_Address.D, 20],  #D, 75
    [Variable_Raster_Address.D, 10],  #D, 75

    [Variable_Raster_Address.D, 20],  #D, 75
    [Variable_Raster_Address.D, 10],  #D, 75
    [Variable_Raster_Address.D, 20],  #D, 75
    [Variable_Raster_Address.D, 10],  #D, 75
    [Variable_Raster_Address.D, 20],  #D, 75

    [Variable_Raster_Address.D, 10],  #D, 75
    [Variable_Raster_Address.D, 20],  #D, 75
    [Variable_Raster_Address.D, 10],  #D, 75
    [Variable_Raster_Address.D, 20],  #D, 75
    [Variable_Raster_Address.D, 10],  #D, 75

    [Variable_Raster_Address.D, 20],  #D, 75
    [Variable_Raster_Address.D, 10],  #D, 75
    [Variable_Raster_Address.D, 20],  #D, 75
    [Variable_Raster_Address.D, 10],  #D, 75
    [Variable_Raster_Address.D, 20],  #D, 75
]


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

