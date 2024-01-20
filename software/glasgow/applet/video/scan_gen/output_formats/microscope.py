from abc import ABCMeta, abstractmethod

class MicroscopeInterface(metaclass=ABCMeta):
    @abstractmethod
    async def set_x_resolution(self,xval):
        pass

    @abstractmethod
    async def set_y_resolution(self,yval):
        pass

    @abstractmethod
    async def set_ROI(self,x_upper, x_lower, y_upper, y_lower):
        pass

    @abstractmethod
    async def pause(self):
        pass

    @abstractmethod
    async def unpause(self):
        pass

    @abstractmethod
    async def set_scan_mode(self, mode):
        pass 