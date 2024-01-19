from abc import ABCMeta, abstractmethod

class MicroscopeInterface(metaclass=ABCMeta):
    @abstractmethod
    def set_x_resolution(self,xval):
        pass

    @abstractmethod
    def set_y_resolution(self,yval):
        pass

    @abstractmethod
    def set_ROI(self,x_upper, x_lower, y_upper, y_lower):
        pass

    @abstractmethod
    def pause(self):
        pass

    @abstractmethod
    def unpause(self):
        pass