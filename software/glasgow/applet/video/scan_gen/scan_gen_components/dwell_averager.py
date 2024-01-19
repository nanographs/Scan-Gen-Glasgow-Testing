import amaranth
from amaranth import *
from amaranth.sim import Simulator


class DwellTimeAverager(Elaboratable):
    '''
    Inputs:
        pixel_in: Next value read from ADC
        start_new_average: If high, running_average is set to pixel_in, and
        prev_pixel is not used.

    Outputs:
        running_average: The current running average. Average of pixel_in and prev_pixel
        prev_pixel: Running average or pixel value from the previous cycle
    '''
    def __init__(self):
        self.pixel_in = Signal(14)
        self.running_average = Signal(14)
        self.prev_pixel = Signal(14)
        self.start_new_average = Signal()
        self.averaging = Signal()
        self.strobe = Signal()
    def elaborate(self, platform):
        m = Module()
        


        with m.FSM() as fsm:
            with m.State("Waiting"):
                with m.If(self.start_new_average):
                    m.next = "Start New Average"

            with m.State("Start New Average"):
                with m.If(self.strobe):
                    m.d.sync += self.prev_pixel.eq(self.pixel_in)
                    m.next = "Averaging"
                
            with m.State("Averaging"):
                m.d.sync += self.prev_pixel.eq(self.running_average)
                with m.If(self.strobe):
                    m.d.comb += self.running_average.eq((self.pixel_in+self.prev_pixel)//2)
                with m.Else():
                    m.d.comb += self.running_average.eq((self.prev_pixel))
                with m.If((self.start_new_average) & (~self.strobe)):
                    m.next = "Start New Average"
                with m.If((self.start_new_average) & (self.strobe)):
                    m.d.sync += self.prev_pixel.eq(self.pixel_in)
                    m.next = "Averaging"

        return m

if __name__ == "__main__":
    def average(val1, val2):
        return int((val1 + val2)/2)


    test_pixel_stream = [
        1000,
        2000,
        3000,
        2000,
        1000,
        1250,
        1240,
        500,
        1600
    ]
    
    def test_dwelltimeaverager():
        dut = DwellTimeAverager()
        def bench():
            yield dut.start_new_average.eq(1)
            yield dut.averaging.eq(1)
            yield dut.strobe.eq(1)
            yield dut.pixel_in.eq(Const(test_pixel_stream[0],shape=14))
            print("Pixel in:", test_pixel_stream[0])
            yield
            print("-")
            assert(yield dut.running_average == Const(test_pixel_stream[0],shape=14))
            print("Running average:", test_pixel_stream[0])
            running_average = test_pixel_stream[0]
            
            yield dut.start_new_average.eq(0)


            for n in range(1, 5):
                yield dut.pixel_in.eq(test_pixel_stream[n])
                print("Pixel in:", test_pixel_stream[n])
                yield
                print("-")
                print("Averaging", test_pixel_stream[n], "and", running_average)
                running_average = average(test_pixel_stream[n], running_average)
                print("Running average:", running_average)
                assert(yield dut.running_average == Const(running_average,shape=14))

            yield dut.start_new_average.eq(1)
            print("Starting new running average.")
            yield dut.pixel_in.eq(test_pixel_stream[5])
            print("Pixel in:", test_pixel_stream[5])
            running_average = test_pixel_stream[5]
            yield
            print("-")
            assert(yield dut.running_average == Const(test_pixel_stream[5],shape=14))
            print("Running average:", running_average)
            yield dut.start_new_average.eq(0)

            for n in range(6, len(test_pixel_stream)):
                yield dut.pixel_in.eq(test_pixel_stream[n])
                print("Pixel in:", test_pixel_stream[n])
                yield
                print("-")
                running_average = average(test_pixel_stream[n], running_average)
                print("Running average:", running_average)
                assert(yield dut.running_average == Const(running_average,shape=14))
                
                
                
                
        sim = Simulator(dut)
        sim.add_clock(1e-6) # 1 MHz
        sim.add_sync_process(bench)
        with sim.write_vcd("running_avg_sim.vcd"):
            sim.run()

    test_dwelltimeaverager()