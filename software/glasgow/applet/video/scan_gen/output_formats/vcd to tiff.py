
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

class VCD:
    def __init__(self,vcd):
        self.parse_vcd(vcd)
    def parse_vcd(self,vcd):
        self.comment = next(vcd)[9:-6]
        self.date = next(vcd)[6:-6]
        self.timescale = next(vcd)[11:-6]
        self.module_path = []
        module_labels_section = True
        while module_labels_section:
            m = next(vcd)
            if m[1:6] == "scope":
                module_name = m[14:-6]
                self.module_path.append(Module(module_name))
            elif m[1:4] == "var":
                if m[5:9] == "wire":
                    wire_info = m[10:-6].split()
                    wire = Wire(wire_info[0],wire_info[1],wire_info[2])
                    current_module = self.module_path[:-1][0]
                    current_module.wires.append(wire)
            else:
                for module in self.module_path:
                    print(module.name)
                    for wire in module.wires:
                        print(wire.name)
                break


vcd_obj = VCD(vcd)
