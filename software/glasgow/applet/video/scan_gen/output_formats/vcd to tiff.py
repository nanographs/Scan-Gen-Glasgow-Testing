
vcd = open("/Users/isabelburgos/glasgow_env/Scan-Gen-Glasgow-Testing/scan_sim_average.vcd")

class Module:
        def __init__(self, name):
            self.name = name
            self.wires = []

class Wire:
    def __init__(self, width, symbol, name):
        self.width = width
        self.symbol = symbol
        self.name = name
        self.time_series = {}

class VCD:
    def __init__(self):
        self.wire_dict = {}
        self.wire_name_dict = {}
    def parse_vcd(self,vcd):
        self.comment = next(vcd)[9:-6]
        self.date = next(vcd)[6:-6]
        self.timescale = next(vcd)[11:-6]
        self.module_path = []
        module_labels_section = True
        data_section = False
        while module_labels_section:
            m = next(vcd)
            if m[1:6] == "scope":
                module_name = m[14:-6]
                self.module_path.append(Module(module_name))
            elif m[1:4] == "var":
                if m[5:9] == "wire":
                    wire_width, wire_symbol, wire_name = m[10:-6].split()
                    wire = Wire(wire_width,wire_symbol,wire_name)
                    current_module = self.module_path[::-1][0]
                    current_module.wires.append(wire)
                    self.wire_dict.update({wire_symbol:wire})
                    self.wire_name_dict.update({wire_name:wire})
            elif m[1:8] == "upscope":
                self.module_path = self.module_path[:-1]
            elif m[1:9] == "dumpvars":
                data_section = True
                break
        self.current_time = 0
        while data_section:
            try:
                d = next(vcd)
                if d.startswith("#"):
                    self.current_time = d[1:].strip("\n")
                else:
                    d = d.split()
                    if len(d) == 1:
                        val = d[0][0]
                        symbol = d[0][1]
                    else:
                        val = d[0]
                        symbol = d[1]
                    wire = self.wire_dict.get(symbol)
                    if wire: 
                        wire.time_series.update({self.current_time:val})
            except StopIteration as e:
                break
                    


vcd_obj = VCD()
vcd_obj.parse_vcd(vcd)

image_data_name = "in_pixel"
image_bits = vcd_obj.wire_name_dict.get(image_data_name).time_series.values()
image_bytes = [int(n[1:],2) for n in image_bits]
print(image_bytes)
