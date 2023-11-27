if "glasgow" in __name__: ## running as applet
    from ..scan_gen_components.addresses import *
else:
    from addresses import *


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