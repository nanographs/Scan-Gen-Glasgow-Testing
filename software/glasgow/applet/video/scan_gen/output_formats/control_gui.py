import sys
import asyncio

from PyQt6.QtWidgets import (QWidget, QGridLayout, QHBoxLayout, 
                            QLabel, QPushButton, QSpinBox)

from qasync import QEventLoop, QApplication, asyncSlot, asyncClose


class RegisterUpdateBox(QGridLayout):
    def __init__(self, label, lower_limit, upper_limit, fn=None):
        super().__init__()
        self.name = label
        self.fn = fn
        self.label = QLabel(label)
        self.addWidget(self.label,0,1)

        self.spinbox = QSpinBox()
        self.spinbox.setRange(lower_limit, upper_limit)
        self.spinbox.setSingleStep(1)
        self.addWidget(self.spinbox,1,1)


    @asyncSlot()
    async def do_fn(self):
        val = int(self.spinbox.cleanText())
        print("set", self.name, ":", val)
        if not self.fn == None: ## allow previewing the button without any function
            await self.fn(val)

class FrameSettings(QHBoxLayout):
    def __init__(self, img_display, scan_iface=None):
        super().__init__()
        self.scan_iface = scan_iface
        self.img_display = img_display
        if not self.scan_iface == None:
            self.x_resolution = RegisterUpdateBox("X Resolution", 1, 16384, self.scan_iface.set_x_resolution)
            self.y_resolution = RegisterUpdateBox("Y Resolution", 1, 16384, self.scan_iface.set_y_resolution)
        else:
            self.x_resolution = RegisterUpdateBox("X Resolution", 1, 16384)
            self.y_resolution = RegisterUpdateBox("Y Resolution", 1, 16384)
        
        self.x_resolution.spinbox.setValue(2048)
        self.y_resolution.spinbox.setValue(2048)

        self.registers = [self.x_resolution, self.y_resolution]

        self.addLayout(self.x_resolution)
        self.addLayout(self.y_resolution)

        self.btn = QPushButton("->")
        self.addWidget(self.btn) 
        self.btn.clicked.connect(self.do_fns)

    @asyncSlot()
    def do_fns(self):
        height = int(self.y_resolution.spinbox.cleanText())
        width = int(self.x_resolution.spinbox.cleanText())
        self.img_display.setRange(height, width)
        for register in self.registers:
            register.do_fn()



class MainWindow(QWidget):


    def __init__(self, scan_iface = None):
        super().__init__()
        self.scan_iface = scan_iface

        self.setWindowTitle("Scan Control")
        self.layout = QGridLayout()
        self.setLayout(self.layout)

        self.frame_settings = FrameSettings(self.scan_iface)
        self.layout.addLayout(self.frame_settings, 2, 0)


        self.start_btn = QPushButton('▶️')
        self.layout.addWidget(self.start_btn)
        self.start_btn.clicked.connect(self.do_stuff)
        
    @asyncSlot()
    async def do_stuff(self):
        print("Hello")



def run_gui(scan_iface=None):

    app = QApplication(sys.argv)

    event_loop = QEventLoop(app)
    asyncio.set_event_loop(event_loop)

    main_window = MainWindow(scan_iface)
    main_window.show()
    
    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)

    with event_loop:
        event_loop.run_until_complete(app_close_event.wait())


if __name__ == "__main__":
    run_gui()


