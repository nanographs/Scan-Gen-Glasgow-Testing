import amaranth
from amaranth import *
from amaranth.sim import Simulator

## dealing with relative imports
if "glasgow" in __name__: ## running as applet
    from ..scan_gen_components.ramps import RampGenerator
else: ## running as script (simulation)
    from ramps import RampGenerator
    


class ScanGenerator(Elaboratable):
    def __init__(self, resolution_bits):
        assert resolution_bits <= 14
        self.bits = resolution_bits
        self.width = pow(2,self.bits)

        ## state
        self.en = Signal()
        self.line_sync = Signal()
        self.frame_sync = Signal()

        ## frame counter
        self.frame_size = self.width*self.width
        
        ## x and y position values
        self.x_data = Signal(14)
        self.y_data = Signal(14)

        
    def elaborate(self,platform):
        m = Module()

        m.submodules.x_ramp = x_ramp = RampGenerator(self.width)
        m.submodules.y_ramp = y_ramp = RampGenerator(self.width)
        m.d.comb += [x_ramp.en.eq(0),y_ramp.en.eq(0)]

        m.d.comb += [            
        self.x_data.eq(x_ramp.count*pow(2,14-self.bits)), 
        self.y_data.eq(y_ramp.count*pow(2,14-self.bits)), 
        self.line_sync.eq(x_ramp.ovf),
        self.frame_sync.eq(y_ramp.ovf),
        x_ramp.limit.eq(self.width.bit_length()),
        y_ramp.limit.eq(self.width.bit_length())
        ]

        with m.If(self.en):
            ## start counting when enabled
            m.d.comb += x_ramp.en.eq(1)
            with m.If(x_ramp.ovf):
                ## if the x counter is max, increment y
                m.d.comb += y_ramp.en.eq(1)
        return m
        def ports(self):
            return[self.en, self.line_sync, self.frame_sync,
            self.x_data,self.y_data]

# --- TEST ---
if __name__ == "__main__":
    test_bits = 3
    test_width = pow(2,test_bits)
    dut = ScanGenerator(test_bits)
    def bench():
        yield dut.en.eq(1)
        for _ in range(3*test_width*test_width):
            yield
        yield


    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("scan_sim_ramp.vcd"):
        sim.run()