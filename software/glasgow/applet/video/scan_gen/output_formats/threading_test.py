from threading import Thread, Event
from time import sleep, perf_counter
import asyncio

from data_protocol import ScanInterface

class UI:
    def __init__(self):
        loop = asyncio.get_event_loop()
        close_future = loop.create_future()
        self.con = ScanInterface(close_future)
    
    def start(self):
        t = Thread(target = asyncio.run, args = [self.con.start()])
        t.start()


ui = UI()
ui.start()
