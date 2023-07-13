
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
        self.values = []

class VCD:
    def __init__(self,vcd):
        self.wire_dict = {}
        self.parse_vcd(vcd)
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
                    wire_info = m[10:-6].split()
                    wire = Wire(wire_info[0],wire_info[1],wire_info[2])
                    current_module = self.module_path[::-1][0]
                    current_module.wires.append(wire)
                    self.wire_dict.update({wire_info[1]:wire_info[2]})
            elif m[1:8] == "upscope":
                self.module_path = self.module_path[:-1]
            elif m[1:9] == "dumpvars":
                print("end")
                data_section = True
                break
            # else:
            #     for module in self.module_path:
            #         print(module.name)
            #         for wire in module.wires:
            #             print(wire.name)
            #     break
        while data_section:
            d = next(vcd)
            if d.startswith("#"):
                pass #timestamp
            else:
                d = d.split()
                if len(d) == 1:
                    val = d[0][0]
                    symbol = d[0][1]
                else:
                    val = d[0]
                    symbol = d[1]
                wire = self.wire_dict.get(symbol)
                print(wire, val,symbol)
                    


vcd_obj = VCD(vcd)
