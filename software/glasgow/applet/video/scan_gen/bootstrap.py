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

args = Namespace(verbose=0, quiet=0, log_file=None, filter_log=None, show_statistics=False, serial=None, 
                    action='interact', override_required_revision=False, reload=False, prebuilt=False, bitstream=None, 
                    trace=None, applet='scan-gen', port_spec='AB', pin_set_data=range(0, 14), pin_power_ok=15, voltage=3.3, 
                    mirror_voltage=False, keep_voltage=False, gui=True)


async def get_applet():

    device = GlasgowHardwareDevice(args.serial)
    target, applet = _applet("C3", args)
    plan = target.build_plan()
    await device.download_target(plan, reload=args.reload)
    print(target)
    print(applet)
    print(vars(applet))
    device.demultiplexer = DirectDemultiplexer(device, target.multiplexer.pipe_count)
    return applet, device, args

async def get_iface():
    iface = await applet.run(device, args)
    return iface





if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        event_loop = QEventLoop(app)
        asyncio.set_event_loop(event_loop)

        applet, device, args = event_loop.run_until_complete(get_applet())

        main_window = MainWindow([applet, device, args])
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




