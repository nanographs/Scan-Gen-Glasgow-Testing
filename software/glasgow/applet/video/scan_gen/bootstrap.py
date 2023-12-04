import sys
import argparse
from argparse import Namespace
import asyncio

from PyQt6.QtWidgets import (QWidget, QGridLayout, QHBoxLayout, 
                            QLabel, QPushButton, QSpinBox)

import pyqtgraph as pg
from pyqtgraph.exporters import Exporter
from pyqtgraph.Qt import QtCore


import qasync
from qasync import QEventLoop, QApplication, asyncSlot, asyncClose

from output_formats.even_newer_gui import MainWindow

sys.path.append("/Users/isabelburgos/Scan-Gen-Glasgow-Testing/software")
from glasgow import *
from glasgow.cli import main, get_argparser, _applet, _main
from glasgow.device.hardware import GlasgowHardwareDevice
from glasgow.access.direct import DirectDemultiplexer

async def get_applet():
    args = Namespace(verbose=0, quiet=0, log_file=None, filter_log=None, show_statistics=False, serial=None, 
                    action='run', override_required_revision=False, reload=False, prebuilt=False, bitstream=None, 
                    trace=None, applet='scan-gen', port_spec='AB', pin_set_data=range(0, 14), pin_power_ok=15, voltage=3.3, 
                    mirror_voltage=False, keep_voltage=False, gui=True)
    device = GlasgowHardwareDevice(args.serial)
    target, applet = _applet("C3", args)
    print(target)
    print(applet)
    print(vars(applet))
    device.demultiplexer = DirectDemultiplexer(device, target.multiplexer.pipe_count)
    iface = await applet.run(device, args)
    return iface


async def main(event_loop, app, iface):
    print(event_loop)
    # args = get_argparser().parse_args()
    # print(args)

    print(iface)
    # print(target)
    # print(applet)
    # event_loop = asyncio.get_event_loop()
    # a = asyncio.run(_main(args))
    # print(a)
    # print(type(args.voltage))
    # asyncio.run(device.set_voltage(args.ports, args.voltage))



if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        event_loop = QEventLoop(app)
        asyncio.set_event_loop(event_loop)

        scan_iface = event_loop.run_until_complete(get_applet())

        main_window = MainWindow(scan_iface)
        main_window.show()

        app_close_event = asyncio.Event()
        app.aboutToQuit.connect(app_close_event.set)

        with event_loop:
            event_loop.run_until_complete(app_close_event.wait())
        #qasync.run(main(event_loop, app))
        
    except Exception as err:
        print("error:", err)
        event_loop.close()
        sys.exit(0)




