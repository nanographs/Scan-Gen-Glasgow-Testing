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