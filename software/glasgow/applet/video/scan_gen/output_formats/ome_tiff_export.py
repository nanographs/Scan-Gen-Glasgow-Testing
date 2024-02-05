import numpy as np
from ome_types import to_xml, OME

from ome_types.model import Instrument, Microscope, InstrumentRef, Image, Pixels


microscope_jeol = Microscope(
             manufacturer='JEOL',
             model='Lab Mk4',
             serial_number='L4-5678',
         )

ome = OME()

instrument = Instrument(
    microscope = microscope_jeol
)
ome.instruments.append(instrument)

pixels = Pixels(
    size_x = 512,
    size_y = 512,
    size_z = 1,
    size_c = 1,
    size_t = 1,
)

image = Image(pixels)
ome.images.append(image)

print(ome.to_xml())

# array = np.random.randint(0, 255,size = (512,512))
# array = array.astype(np.uint8)