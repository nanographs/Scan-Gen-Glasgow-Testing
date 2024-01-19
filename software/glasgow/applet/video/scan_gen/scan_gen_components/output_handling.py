import amaranth
from amaranth import *
from amaranth.sim import Simulator
from amaranth.lib import data, enum
from amaranth.lib.fifo import SyncFIFO


import unittest

class VideoSink(Elaboratable):
    def __init__(self):
        self.pixel_in = Signal(14)
        self.pixel_out = Signal(14)
        self.pipeline_offsetter = PipelineOffsetter()
        self.dwell_time_averager = DwellTimeAverager()
        #self.pipeline_full = Signal()
        self.sinking = Signal()
        self.dwelling = Signal()
    def elaborate(self, platform):
        m = Module()


        m.submodules["PipelineOffsetter"] = self.pipeline_offsetter
        m.submodules["DwellTimeAverager"] = self.dwell_time_averager

        m.d.comb += self.dwell_time_averager.pixel_in.eq(self.pixel_in)
        m.d.comb += self.pipeline_offsetter.pixel_in.eq(self.dwell_time_averager.running_average)
        m.d.comb += self.pixel_out.eq(self.pipeline_offsetter.pixel_out)
        #m.d.comb += self.dwell_time_averager.strobe.eq(self.strobe)

        
        with m.If(self.sinking):
            m.d.comb += self.pipeline_offsetter.reading.eq(self.pipeline_offsetter.pipeline_full)
            m.d.comb += self.dwell_time_averager.averaging.eq(1)
            m.d.comb += self.pipeline_offsetter.writing.eq(1)
            ## only copy the data into the delay pipeline if it's actually a new point
                
        with m.FSM() as fsm:
            with m.State("Start New Collection"):
                m.d.comb += self.dwell_time_averager.start_new_average.eq(1)
                m.next = "Collecting and Averaging"

            with m.State("Collecting and Averaging"):
                with m.If(self.dwelling):
                    m.next = "Start New Collection"
                with m.Else():
                    m.next = "Collecting and Averaging"
        
        
        return m
    def ports(self):
        return [self.pixel_in, self.pixel_out, self.dwelling]

class PipelineOffsetter(Elaboratable):
    '''
    By setting pixel_in to a value, that value is written into a memory
    6 cycles later, the same value appears at pixel_out by reading from the memory
    Parameters:
        offset: Number of cycles of delay = 6

    Inputs:
        pixel_in: Value to be copied into the first stage of the pipeline
        writing: If writing = high:
            - Current pixel_in value will be written into memory on the next cycle
            - Read and write addresses will be incremented on the next cycle

            writing:   -_
            write_addr: n
            write_data: x
            memory(n): -x

        reading: If reading = high, the value at read_addr will be written to
            pixel_out on the next cycle

            reading:   -_
            read_addr: n
            memory(n): x
            read_data: x
            pixel_out: -x

        start_delay: A counter that is incremented whenever writing is high
            When the counter reaches offset(6), pipeline_full is true.
            read_addr only starts incrementing once start_delay reaches offset(6).
        pipeline_full: A signal that is low when the module is first initialized,
            then goes high when start_delay reaches 6.
            At this point, all memory registers have been written to.

            start_delay:  0 1 2 3 4 5 6 
            pipeline_full:____________-
        
    
    Outputs:
        pixel_out: Value read from the last stage of the pipeline

    Internal signals:
        read_addr: Address of memory register to be written into next cycle
        write_addr: Address of memory register to be read from next cycle
        read_ovf: High when read_addr = offset, read_addr will be reset next cycle
        write_ovf: High when write_addr = offset, write_addr will be reset next cycle
    '''
    def __init__(self, offset = 6, sync = False):
        self.pixel_in = Signal(14)
        self.pixel_out = Signal(14)
        self.offset = offset ## Number of pipelining cycles to offset
        self.reading = Signal() ## Control input
        self.writing = Signal() ## Control input
        self.pipeline_full = Signal() ## High on the 6th cycle of reading data in
        self.start_delay = Signal(self.offset.bit_length())

        self.sync = sync


    def elaborate(self, platform):
        m = Module()
        
        mem = Memory(width=14, depth=self.offset)
        m.submodules["read_port"] = read_port = mem.read_port(transparent=False)
        m.submodules["write_port"] = write_port = mem.write_port()
        
        write_addr = Signal(self.offset.bit_length()) ## Memory address to be written to next cycle
        read_addr = Signal(self.offset.bit_length()) ## Memory address to be read from next cycle
        m.d.comb += read_port.addr.eq(read_addr)
        m.d.comb += write_port.addr.eq(write_addr)


        write_ovf = Signal() ## High when write_addr = offset
        read_ovf = Signal() ## High when read_addr = offset
        m.d.comb += write_ovf.eq(write_addr == self.offset)
        m.d.comb += read_ovf.eq(read_addr == self.offset)

        m.d.comb += self.pipeline_full.eq(self.start_delay == self.offset)

        ## Writing data
        m.d.comb += write_port.data.eq(self.pixel_in)
        m.d.comb += write_port.addr.eq(write_addr)

        with m.If(self.writing):
            m.d.comb += write_port.en.eq(1)
            
            with m.If(self.pipeline_full):
                with m.If(read_ovf):
                    m.d.sync += read_addr.eq(0)
                with m.Else():
                    m.d.sync += read_addr.eq(read_addr + 1)
                
            ## Let the queue fill up before you start drawing from it
            with m.Else():
                m.d.sync += self.start_delay.eq(self.start_delay + 1)
                m.d.sync += read_addr.eq(0)

            with m.If(write_ovf):
                m.d.sync += write_addr.eq(0)
            with m.Else():
                m.d.sync += write_addr.eq(write_addr + 1)

        m.d.comb += self.pixel_out.eq(read_port.data)
        m.d.comb += read_port.en.eq(self.reading)
        
        if self.sync:
            with m.If((self.start_delay == self.offset - 1) & (self.writing)):
                m.d.comb += read_port.en.eq(1)
        
        return m
    def ports(self):
        return [self.pixel_out, self.pixel_in, self.read_addr, self.write_addr,
        self.reading, self.writing, self.pipeline_full]





if __name__ == "__main__":


    def test_pipelineoffsetter():
        dut = PipelineOffsetter()
        def bench():
            for n in range(0,6):
                next_pixel = test_pixel_stream[n]
                yield dut.writing.eq(1)
                yield dut.pixel_in.eq(next_pixel)
                yield
                print("-")
                print("cycle", n, "pixel in = ", next_pixel)
                assert(yield dut.start_delay == n)
            yield dut.reading.eq(1)
            yield
            print("-")
            assert(yield dut.pipeline_full)
            print("pipeline full")
            print("pixel out =", test_pixel_stream[0])
            for n in range(0,6):
                yield
                print("-")
                assert(yield dut.pixel_out == test_pixel_stream[n])
                print("pixel out =", test_pixel_stream[n])
            

        sim = Simulator(dut)
        sim.add_clock(1e-6) # 1 MHz
        sim.add_sync_process(bench)
        with sim.write_vcd("pipelining_sim.vcd"):
            sim.run()






    def test_videosink():
        dut = VideoSink()
        def bench():
            yield dut.dwelling.eq(1)
            for n in range(0, len(test_pixel_stream)):
                next_pixel = test_pixel_stream[n]
                print("pixel", n, "=", next_pixel)
                yield dut.pixel_in.eq(next_pixel)
                yield dut.sinking.eq(1)
                yield
                yield dut.sinking.eq(0)
                yield
            yield dut.dwelling.eq(0)
            yield
        
        sim = Simulator(dut)
        sim.add_clock(1e-6) # 1 MHz
        sim.add_sync_process(bench)
        with sim.write_vcd("videosink_sim.vcd"):
            sim.run()


    #test_dwelltimeaverager()
    #test_pipelineoffsetter()
    #test_videosink()