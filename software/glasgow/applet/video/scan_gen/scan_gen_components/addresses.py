import amaranth
from amaranth import *
from amaranth.lib import data, enum

# Addresses

class Raster_Data(enum.Enum, shape = 3):
    X = 1
    Y = 2
    DX = 3
    DY = 4
    D = 7

class IOType(enum.Enum, shape = 1):
    Scanalog = 0 ## commands for the actual scan generator
    DigitalIO = 1 ## external relays/switches/etc
class ScanMode(enum.Enum, shape = 1):
    Raster = 0
    Vector = 1
class DwellMode(enum.Enum, shape = 1):
    Constant = 0
    Variable = 1
class Vector_Data(enum.Enum, shape = 3):
    X = 1
    Y = 2
    D = 7

class Vector_Address(enum.Enum, shape = 8):
    X = Value.cast(Cat(Const(0,shape=2),IOType.Scanalog, ScanMode.Vector, DwellMode.Variable, Vector_Data.X))
    Y = Value.cast(Cat(Const(0,shape=2),IOType.Scanalog, ScanMode.Vector, DwellMode.Variable, Vector_Data.Y))
    D = Value.cast(Cat(Const(0,shape=2),IOType.Scanalog, ScanMode.Vector, DwellMode.Variable, Vector_Data.D))


class Constant_Raster_Address(enum.Enum, shape = 8):
    X = Value.cast(Cat(Const(0,shape=2),IOType.Scanalog, ScanMode.Raster, DwellMode.Constant, Raster_Data.X))
    Y = Value.cast(Cat(Const(0,shape=2),IOType.Scanalog, ScanMode.Raster, DwellMode.Constant, Raster_Data.Y))
    D = Value.cast(Cat(Const(0,shape=2),IOType.Scanalog, ScanMode.Raster, DwellMode.Constant, Raster_Data.D))
