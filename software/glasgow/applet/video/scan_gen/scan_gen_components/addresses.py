import amaranth
from amaranth import *
from amaranth.lib import data, enum

# Addresses

class ResetMode(enum.Enum, shape = 1):
    NoReset = 0
    Immediate = 1
class IOType(enum.Enum, shape = 1):
    DigitalIO = 0 ## external relays/switches/etc
    Scanalog = 1 ## commands for the actual scan generator
class ScanMode(enum.Enum, shape = 1):
    Raster = 0
    Vector = 1
class ScanRepeat(enum.Enum, shape = 1):
    Continous = 0
    Once = 1
class DwellMode(enum.Enum, shape = 1):
    Constant = 0
    Variable = 1
class Vector_Data(enum.Enum, shape = 3):
    X = 1
    Y = 2
    D = 7

class Raster_Data(enum.Enum, shape = 3):
    X = 1
    Y = 2
    UX = 3
    UY = 4
    LX = 5
    LY = 6
    D = 7

class Vector_Address(enum.Enum, shape = 8):
    X = Value.cast(Cat(ResetMode.NoReset,IOType.Scanalog, ScanMode.Vector, ScanRepeat.Once, DwellMode.Variable, Vector_Data.X))
    Y = Value.cast(Cat(ResetMode.NoReset,IOType.Scanalog, ScanMode.Vector, ScanRepeat.Once, DwellMode.Variable, Vector_Data.Y))
    D = Value.cast(Cat(ResetMode.NoReset,IOType.Scanalog, ScanMode.Vector, ScanRepeat.Once, DwellMode.Variable, Vector_Data.D))


class Constant_Raster_Address(enum.Enum, shape = 8):
    X = Value.cast(Cat(ResetMode.NoReset, IOType.Scanalog, ScanMode.Raster, ScanRepeat.Once, DwellMode.Constant, Raster_Data.X))
    Y = Value.cast(Cat(ResetMode.NoReset, IOType.Scanalog, ScanMode.Raster, ScanRepeat.Once, DwellMode.Constant, Raster_Data.Y))
    D = Value.cast(Cat(ResetMode.NoReset,IOType.Scanalog, ScanMode.Raster, ScanRepeat.Once, DwellMode.Constant, Raster_Data.D))
    LX = Value.cast(Cat(ResetMode.NoReset, IOType.Scanalog, ScanMode.Raster, ScanRepeat.Once, DwellMode.Constant, Raster_Data.LX))
    LY = Value.cast(Cat(ResetMode.NoReset,IOType.Scanalog, ScanMode.Raster, ScanRepeat.Once, DwellMode.Constant, Raster_Data.LY))
    UX = Value.cast(Cat(ResetMode.NoReset, IOType.Scanalog, ScanMode.Raster, ScanRepeat.Once, DwellMode.Constant, Raster_Data.UX))
    UY = Value.cast(Cat(ResetMode.NoReset,IOType.Scanalog, ScanMode.Raster, ScanRepeat.Once, DwellMode.Constant, Raster_Data.UY))

class Variable_Raster_Address(enum.Enum, shape = 8):
    X = Value.cast(Cat(ResetMode.NoReset, IOType.Scanalog, ScanMode.Raster, ScanRepeat.Once, DwellMode.Variable, Raster_Data.X))
    Y = Value.cast(Cat(ResetMode.NoReset, IOType.Scanalog, ScanMode.Raster, ScanRepeat.Once, DwellMode.Variable, Raster_Data.Y))
    D = Value.cast(Cat(ResetMode.NoReset,IOType.Scanalog, ScanMode.Raster, ScanRepeat.Once, DwellMode.Variable, Raster_Data.D))


address_layout = data.StructLayout({
    "ResetMode": 1,
    "IOType": 1,
    "ScanMode": 1,
    "ScanRepeat": 1,
    "DwellMode": 1,
    "DataType": 3
})


vector_point = data.StructLayout({
    "X1": 8,
    "X2": 8,
    "Y1": 8,
    "Y2": 8,
    "D1": 8,
    "D2": 8,
})


def get_two_bytes(n: int):
    bits = "{0:016b}".format(n)
    return bits[0:8], bits[8:16]


#print(get_two_bytes(1000))




