import amaranth
from amaranth import *
from amaranth.lib import data, enum

# Addresses, data types,  and other utilities

class ScanMode(enum.Enum, shape = 2):
    Raster = 1
    RasterPattern = 2
    Vector = 3

vector_point = data.StructLayout({
    "X1": 8,
    "X2": 8,
    "Y1": 8,
    "Y2": 8,
    "D1": 8,
    "D2": 8,
})

vector_position = data.StructLayout({
    "X1": 8,
    "X2": 8,
    "Y1": 8,
    "Y2": 8,
})

vector_dwell = data.StructLayout({
    "D1": 8,
    "D2": 8,
})


def get_two_bytes(n: int):
    bits = "{0:016b}".format(n)
    return bits[0:8], bits[8:16]


#print(get_two_bytes(1000))




