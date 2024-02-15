from fibsem.structures import (FibsemImage, FibsemImageMetadata,
                            FibsemMillingSettings, FibsemRectangle,
                            FibsemStagePosition,
                            ImageSettings, SystemSettings, SystemInfo,
                            MicroscopeState, Point, FibsemDetectorSettings,
                            FibsemUser, FibsemExperiment,
                            FibsemPatternSettings, FibsemRectangleSettings, 
                            FibsemCircleSettings, FibsemLineSettings, FibsemBitmapSettings)
from fibsem.microscope import FibsemMicroscope


class OBIMicroscope(FibsemMicroscope):
    def __init__(self):
        pass
    def connect_to_microscope(self, ip_address: str, port: int) -> None:
        pass
    def disconnect(self):
        pass
    def acquire_image(self, image_settings:ImageSettings) -> FibsemImage:
        resolution = image_settings.resolution
        dwell_time = image_settings.dwell_time
        reduced_area = image_settings.reduced_area
    def draw_rectangle(self, pattern_settings:FibsemRectangleSettings):
        pass
    def draw_line(self, pattern_settings:FibsemLineSettings):
        pass
    def draw_bitmap_pattern(self, pattern_settings:FibsemBitmapSettings, path: str):
        pass

settings = ImageSettings()
print(settings)
    