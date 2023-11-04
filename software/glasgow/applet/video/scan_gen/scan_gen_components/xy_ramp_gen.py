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
        #assert resolution_bits <= 14
        self.bits = resolution_bits
        self.max_resolution = Signal(14, reset = 16383)
        self.width = Signal(14)

        ## state
        self.rst = Signal()
        self.en = Signal()
        self.line_sync = Signal()
        self.frame_sync = Signal()

        
        ## x and y position values
        self.x_data = Signal(14)
        self.y_data = Signal(14)

        self.x_rst = Signal()
        self.y_rst = Signal()

        
    def elaborate(self,platform):
        m = Module()

        m.submodules.x_ramp = x_ramp = RampGenerator(self.width)
        m.submodules.y_ramp = y_ramp = RampGenerator(self.width)
        m.d.comb += [x_ramp.en.eq(0),y_ramp.en.eq(0)]

        m.d.comb += [            
        self.width.eq(self.max_resolution >> (14-self.bits).as_unsigned()),
        # self.x_data.eq(x_ramp.count*pow(2,14-self.bits)), 
        self.x_data.eq(x_ramp.count << (14-self.bits).as_unsigned()),
        self.y_data.eq(y_ramp.count << (14-self.bits).as_unsigned()), 
        self.line_sync.eq(x_ramp.ovf),
        self.frame_sync.eq(y_ramp.ovf),
        ]


        m.d.comb += [
                x_ramp.rst.eq(self.x_rst),
                y_ramp.rst.eq(self.y_rst)
            ]
        with m.If(self.rst):
            m.d.comb += [
                y_ramp.rst.eq(1),
                x_ramp.rst.eq(1)
            ]
        with m.Else():
            with m.If(self.en):
                ## start counting when enabled
                m.d.comb += x_ramp.en.eq(1)
                with m.If(x_ramp.ovf):
                    ## if the x counter is max, increment y
                    m.d.comb += y_ramp.en.eq(1)
        return m
        def ports(self):
            return[self.en, self.line_sync, self.frame_sync,
            self.x_data,self.y_data, self.width]



class AnySizeScanGenerator(Elaboratable):
    def __init__(self, resolution_bits, x_resolution, y_resolution):
        self.bits = resolution_bits
        
        self.x_resolution = x_resolution
        self.y_resolution = y_resolution

        self.x_res_sig = Signal(x_resolution.bit_length())
        self.y_res_sig = Signal(y_resolution.bit_length())

        ## state
        self.rst = Signal()
        self.en = Signal()
        self.line_sync = Signal()
        self.frame_sync = Signal()

        
        ## x and y position values
        self.x_data = Signal(14)
        self.y_data = Signal(14)

        self.x_rst = Signal()
        self.y_rst = Signal()

        
    def elaborate(self,platform):
        m = Module()

        m.d.comb += [
            self.x_res_sig.eq(self.x_resolution),
            self.y_res_sig.eq(self.x_resolution)
        ]

        m.submodules.x_ramp = x_ramp = RampGenerator(self.x_resolution)
        m.submodules.y_ramp = y_ramp = RampGenerator(self.y_resolution)
        m.d.comb += [x_ramp.en.eq(0),y_ramp.en.eq(0)]

        m.d.comb += [       
        # self.x_data.eq(x_ramp.count),
        # self.y_data.eq(y_ramp.count),  
        self.x_data.eq(x_ramp.count << (14-self.bits).as_unsigned()),
        self.y_data.eq(y_ramp.count << (14-self.bits).as_unsigned()), 
        self.line_sync.eq(x_ramp.ovf),
        self.frame_sync.eq(y_ramp.ovf),
        ]


        m.d.comb += [
                x_ramp.rst.eq(self.x_rst),
                y_ramp.rst.eq(self.y_rst)
            ]
        with m.If(self.rst):
            m.d.comb += [
                y_ramp.rst.eq(1),
                x_ramp.rst.eq(1)
            ]
        with m.Else():
            with m.If(self.en):
                ## start counting when enabled
                m.d.comb += x_ramp.en.eq(1)
                with m.If(x_ramp.ovf):
                    ## if the x counter is max, increment y
                    m.d.comb += y_ramp.en.eq(1)
        return m
        def ports(self):
            return[self.en, self.line_sync, self.frame_sync,
            self.x_data,self.y_data, self.width]

# --- TEST ---
if __name__ == "__main__":
    print("testing")
    test_bits = Signal(4, reset=4)
    test_width = 64
    dut = ScanGenerator(test_bits)
    def bench():
       
        for _ in range(2*test_width*test_width):
            yield dut.en.eq(1)
            yield
            yield dut.en.eq(0)
            yield
                
        yield


    sim = Simulator(dut)
    sim.add_clock(1e-6) # 1 MHz
    sim.add_sync_process(bench)
    with sim.write_vcd("scan_sim_ramp.vcd"):
        sim.run()