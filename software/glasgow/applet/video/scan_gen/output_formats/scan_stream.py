import re
import array
import numpy as np
import time

from tests import generate_packet_with_config, generate_vector_packet


class ScanStream:
    def __init__(self):
        self.y_height = 400
        self.x_width = 400

        self.current_x = 0
        self.current_y = 0

        self.x_upper = self.x_width
        self.x_lower = 0
        self.y_upper = self.y_height
        self.y_lower = 0

        self.buffer = np.zeros(shape = (self.y_height,self.x_width),dtype = np.uint8)

        self.config_match = re.compile(b'\xff{2}.{14}\xff{2}')

        self.scan_mode = 0
        self.eight_bit_output = 1
        self.point_buffer = memoryview(bytes([]))

        self._buffer = bytearray()
    
    def writeto(self, d:bytes):
        print(f'extend {len(d)} bytes')
        self._buffer.extend(d)
        print(f'length: {len(self._buffer)}')
        self.readfrom()
    
    def readfrom(self):
        print(f'buffer len: {len(self._buffer)}')
        while len(self._buffer) >= 16384:
            d = self._buffer[:16384]
            self._buffer = self._buffer[16384:]
            self.parse_config_from_data(d)
        


    def change_buffer(self, x_width, y_height):
        self.x_width = x_width
        self.y_height = y_height
        self.buffer = np.zeros(shape=(self.y_height, self.x_width),
                    dtype = np.uint8)
        print("new buffer size:", x_width, y_height)
        self.current_x = 0
        self.current_y = 0

    def clear_buffer(self):
        self.buffer = np.zeros(shape=(self.y_height, self.x_width),
                    dtype = np.uint8)
        print("cleared buffer")

    def points_to_frame(self, m:memoryview, print_debug = True):
        m_len = len(m)
        if print_debug:
            print("data length:", m_len)
            print("frame size (x, y):", self.x_width, self.y_height)
            print("current x, current y:", self.current_x, self.current_y)
            self.check_sync()
        
        current_x = self.current_x + self.x_lower
        current_y = self.current_y + self.y_lower
        x_width = self.x_upper - self.x_lower
        y_height = self.y_upper - self.y_lower

        if print_debug:
            print("ROI frame size (x, y):", x_width, y_height)
            print("ROI current x, current y:", current_x, current_y)
            self.check_sync()
        
        if current_x > 0:
            partial_start_points = x_width - current_x
            if print_debug:
                print(f'partial start points: {partial_start_points}')
                self.check_sync()
            if partial_start_points > m_len: ## the current line will not be completed
                
                full_lines = 0
                self.buffer[current_y][current_x:(current_x + m_len)] = \
                    m[0:partial_start_points]
                partial_end_points = 0
                if print_debug:
                    print(f'partial start points {partial_start_points} > data len {m_len}')
                    self.check_sync()
            else: ## fill in to the end of current line
                if print_debug:
                    print(f'buffer [{current_y}][{current_x}:{x_width}]')
                    print(f'set to m[0:{partial_start_points}]')
                full_lines = ((m_len) - partial_start_points)//x_width
                self.buffer[current_y][current_x:x_width] = \
                    m[0:partial_start_points]
                partial_end_points = (m_len - partial_start_points)%x_width

            if print_debug:
                print(f'full lines: {full_lines}')
                print(f'top rollover index 0:{partial_start_points}')  
                self.check_sync()
            
            if current_y >= y_height - 1:
                current_y = 0 + self.y_lower
            else:
                current_y += 1
            if print_debug:
                print(f'current y: {current_y}')

        else: 
            partial_start_points = 0
            partial_end_points = m_len%x_width
            full_lines = m_len//x_width
            if print_debug:
                print("no top rollover")
                print(f'full lines: {full_lines}')
                self.check_sync()

        
        ## fill in solid middle rectangle

        if not full_lines == 0:
            print(f'{full_lines} >= {y_height}?')
            if full_lines >= y_height:
                full_frames = full_lines//y_height
                extra_lines = m_len%y_height
                if print_debug:
                    print(f'{full_frames} full frames')
                    print(f'{extra_lines} extra lines')
                    self.check_sync()


            print(f'{current_y + full_lines} >= {y_height}?')
            if (current_y + full_lines) >= y_height:
                bottom_rows = y_height - current_y
                top_rows =  full_lines - bottom_rows
                if print_debug:
                    print("rolled into next frame")
                    print(f'bottom rows: {bottom_rows}')
                    print(f'set to: {partial_start_points} : {partial_start_points + x_width*bottom_rows}')
                    self.check_sync()

                self.buffer[current_y:] = \
                        m[partial_start_points:(partial_start_points + x_width*bottom_rows)]\
                            .cast('B',shape=([bottom_rows,self.x_width]))

                if top_rows == 0:
                    current_y = top_rows
                else:
                    if print_debug:
                        print(f'top rows: {top_rows}')
                        print(f'set to: {partial_start_points + x_width*bottom_rows} :{partial_start_points + x_width*bottom_rows+ x_width*top_rows}')
                        print(f'buffer shape: 0:{top_rows}')
                        print(f'cast shape: {top_rows},{self.x_width}')
                        self.check_sync()
                    self.buffer[0:top_rows] = \
                            m[(partial_start_points + x_width*bottom_rows):\
                                (partial_start_points + x_width*bottom_rows+ x_width*top_rows)]\
                                .cast('B',shape=([top_rows,x_width]))
                    if top_rows >= y_height: ## there's more than one full frame left
                        skip_frames = top_rows//y_height
                        extra_rows = top_rows%y_height
                        self.buffer[0:extra_rows] = \
                                m[(partial_start_points + x_width*y_height*skip_frames):\
                                    (partial_start_points + x_width*y_height*skip_frames + x_width*extra_rows)]\
                                    .cast('B',shape=([top_rows,x_width]))
                        current_y = extra_rows
                    else:
                        current_y = top_rows
            
            else:
                if print_debug:
                    print(f'buffer[{current_y}:{current_y+full_lines}]')
                    print(f'set to data [{partial_start_points}:{partial_start_points + x_width*full_lines}]')
                    self.check_sync()
                self.buffer[current_y:current_y+full_lines] = \
                        m[partial_start_points:(partial_start_points + x_width*full_lines)]\
                            .cast('B',shape=([full_lines,x_width]))
                if print_debug:
                    print(f'beginning of block: {self.buffer[current_y]}')
                current_y += full_lines
                if print_debug:
                    print(f'end of block: {self.buffer[current_y]}')
                



        if print_debug:
            print(f'partial end points: {partial_end_points}')
            print(f'buffer [{current_y}][0:{partial_end_points}]')
            print(f' = m[{m_len-partial_end_points}:]')
            print(f'last line: {str(m[m_len-partial_end_points:].tolist())} ')
            print(f'length: {len(m[m_len-partial_end_points:])}')
            self.check_sync()


        self.buffer[current_y][0:partial_end_points] = m[m_len-partial_end_points:]

        current_x = partial_end_points

        if print_debug:
            print(self.buffer)
            self.check_sync()

        self.current_y = current_y - self.y_lower
        self.current_x = current_x - self.x_lower
            

    
    def check_sync(self):
        try:
            assert (self.buffer[self.current_y][self.x_lower] == self.x_lower)
        except AssertionError:
            print("****frame is out of sync****")
            print(self.buffer[self.current_y][0:10])
            #assert (self.buffer[self.current_y][self.x_lower] == self.x_lower)


    def points_to_vector(self, m:memoryview, print_debug = True):
        
        n_extra = len(self.point_buffer)
        full_points = (len(m)-n_extra)//6

        if n_extra != 0:
            start_offset = 6-(n_extra)
        else:
            start_offset = 0

        if print_debug:
            print(f'm len: {len(m)}')
            print(f'extra points from prev packet: {n_extra}')
            print(f'full points: {full_points}')
            print(f'start offset: {start_offset}')
            print(f'start incomplete points: [0:{start_offset}]')
            
        #extra = len(m)%6
                
        if n_extra != 0:
            start_incomplete_points = m[0:start_offset]
            overflow_points = self.point_buffer.tobytes() + start_incomplete_points.tobytes()

            if print_debug:
                print(f'point buffer: {self.point_buffer.tolist()}, {self.point_buffer.tobytes()}')
                print(f'start points: {start_incomplete_points.tolist()}')
                print(f'first point completed: {overflow_points}')
                #print(memoryview(overflow_points).cast('H').tolist())

            x, y, a  = memoryview(overflow_points).cast('H').tolist()
            self.buffer[y][x] = a
        
        points = m[start_offset:(full_points*6 + start_offset)].cast('H', shape=[full_points,3]).tolist()
    
        for n in points:
            x, y, a  = n
            self.buffer[y][x] = a

        if print_debug:
            print(f'end points: [{full_points*6 + start_offset}:]')
        end_incomplete_points = m[(full_points*6 + start_offset):]
        if print_debug:
            print(f'end points: {end_incomplete_points.tolist()}')
        

        self.point_buffer = end_incomplete_points
        # self.point.buffer = m[full_points*6:].tolist()

    def handle_data_with_config(self, data:memoryview, config = None):
        if not config == None:
            print(f'using this config: {config}')
            self.parse_config_packet(config)
        else:
            print("continue with existing config")

        print("data start with", data.tolist()[0:10])

        if self.scan_mode == 0:
            pass

        if len(data) > 0: 
            if self.scan_mode == 1:
                if self.eight_bit_output == 0:
                    start = time.perf_counter()
                    data = data.cast('H')
                    end = time.perf_counter()
                    print(f'16 to 8 time {end-start}')
                start = time.perf_counter()
                self.points_to_frame(data)
                end = time.perf_counter()
                print(f'Time to stuff {end-start}')
            if self.scan_mode == 3:
                start = time.perf_counter()
                self.points_to_vector(data)
                end = time.perf_counter()
                print(f'Time to stuff {end-start}')


    def parse_config_packet(self, d:memoryview):
        f = d[0:12].tolist()
        print("decoded config packet", f)
        new_x = f[0]*256  + f[1] + 1
        new_y = f[2]*256 + f[3] + 1

        new_x_upper = f[4]*256  + f[5]
        new_x_lower = f[6]*256 + f[7]
        new_y_upper = f[8]*256  + f[9]
        new_y_lower = f[10]*256 + f[11]
        
        if ((new_x != self.x_width) | (new_y != self.y_height)):
            self.current_x = 0
            self.current_y = 0
            self.change_buffer(new_x, new_y)

        if any ([(new_x_upper != self.x_upper), (new_x_lower != self.x_lower), 
            (new_y_upper != self.y_upper), (new_y_lower != self.y_lower)]):
            self.current_x = 0
            self.current_y = 0
            if not new_x_upper == 0:
                self.x_upper = new_x_upper + 1
            else:
                self.x_upper = self.x_width
            self.x_lower = new_x_lower
            if not new_y_upper == 0:
                self.y_upper = new_y_upper + 1
            else:
                self.y_upper = self.y_height
            self.y_lower = new_y_lower

        print(f'x width, y height: {self.x_width}, {self.y_height}')
        print(f'x lower, x upper: {self.x_lower}, {self.x_upper}')
        print(f'y lower, y upper: {self.y_lower}, {self.y_upper}')

        s = d[12:14].tolist()
        self.scan_mode = s[0]
        self.eight_bit_output = s[1]
        print(f'scan mode: {self.scan_mode}')
        print(f'8bit mode: {self.eight_bit_output}')
        

    def parse_config_from_data(self, d:bytes, print_debug=False):
        n = re.finditer(self.config_match, d)
        prev_stop = 0
        prev_config = None
        if print_debug:
            print(f'd start with...{list(d)[0:10]}')
        try: 
            match = next(n)
            start, stop = match.span()
            config = match.group()
            data = d[prev_stop:start]
            if print_debug:
                print("Config packet detected")
                print(f'start, stop: {start}, {stop}')
                print(f'data: {prev_stop}:{start}')
                print(f'data start with...{list(data)[0:10]}')
            prev_stop = stop
            prev_config = config
            self.handle_data_with_config(memoryview(data))

            while True:
                try:
                    match = next(n)
                    start, stop = match.span()
                    config = match.group()
                    data = d[prev_stop:start]
                    if print_debug:
                        print("Config packet detected")
                        print(f'start, stop: {start}, {stop}')
                        print(f'data: {prev_stop}:{start}')
                    self.handle_data_with_config(memoryview(data), memoryview(prev_config[2:16]))
                    prev_stop = stop
                    prev_config = config
                except StopIteration:
                    data = d[prev_stop:]
                    if print_debug:
                        print("Stop")
                        print(f'data: {prev_stop}:')
                        print(f'data start with...{list(data)[0:10]}')
                    if prev_config == None:
                        self.handle_data_with_config(memoryview(data))
                    else:
                        self.handle_data_with_config(memoryview(data), memoryview(prev_config[2:16]))
                    break

        except StopIteration:
            if print_debug:
                print("No config packets in here")
            self.handle_data_with_config(memoryview(d))


            













if __name__ == "__main__":
    def test_frame_stuffing():
        #data = [4, 5, 6] + [n for n in range(0,6)]*10 + [0, 1, 2]
        s = ScanStream()
        s.change_buffer(400, 400)
        packet_generator = generate_packet_with_config(400,400)
        for n in range(3):
            print("=====start new packet======")
            data = next(packet_generator)
            d = bytes(data)
            #s.parse_config_from_data(d)
            s.writeto(d)

    def test_vector_stuffing():
        s = ScanStream()
        packet_generator = generate_vector_packet()
        for n in range(3):
            data = next(packet_generator)
            d = memoryview(bytes(data))
            s.points_to_vector(d)
        
    #test_vector_stuffing()
    test_frame_stuffing()