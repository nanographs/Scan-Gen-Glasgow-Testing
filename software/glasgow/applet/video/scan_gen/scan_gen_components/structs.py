import amaranth
from amaranth import *
from amaranth.lib import data, enum

# Addresses, data types,  and other utilities

class ScanMode(enum.Enum, shape = 2):
    Raster = 1
    RasterPattern = 2
    Vector = 3

scan_point_8 = data.StructLayout({
    "X1": 8,
    "X2": 8,
    "Y1": 8,
    "Y2": 8,
    "D1": 8,
    "D2": 8,
})

scan_point_16 = data.StructLayout({
    "X": 16,
    "Y": 16,
    "D": 16,
})

scan_position_8 = data.StructLayout({
    "X1": 8,
    "X2": 8,
    "Y1": 8,
    "Y2": 8,
})

scan_dwell_8 = data.StructLayout({
    "D1": 8,
    "D2": 8,
})

scan_dwell_8_onebyte = data.StructLayout({
    "D1": 8,
})

reduced_area_8 = data.StructLayout({
    "LX1": 8,
    "LX2": 8,
    "UX1": 8,
    "UX2": 8,
    "LY1": 8,
    "LY2": 8,
    "UY1": 8,
    "UY2": 8,
})

reduced_area_16 = data.StructLayout({
    "LX": 16,
    "UX": 16,
    "LY": 16,
    "UY": 16
})


def get_two_bytes(n: int):
    bits = "{0:016b}".format(n)
    return bits[0:8], bits[8:16]


#print(get_two_bytes(1000))




