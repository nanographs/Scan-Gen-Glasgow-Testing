from abc import ABC, ABCMeta, abstractmethod
from bmp_utils import bmp_to_bitstream
from patterngen_utils import in2_out1_byte_stream, packet_from_generator

class Pattern(ABC):
    def __init__(self):
        pass

class BitmapPattern(Pattern):
    def __init__(self, x_width, y_height, file_path):
        super().__init__()
        self.x_width = x_width
        self.y_height = y_height
        self.bitstream = bmp_to_bitstream(self.file_path, self.x_width, self.y_height)
        
