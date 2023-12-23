import re
import array
import numpy as np
import time


class ScanStream:
    def __init__(self):
        self.y_height = 512
        self.x_width = 512

        self.current_x = 0
        self.current_y = 0

        self.buffer = np.zeros(shape = (self.y_height,self.x_width),dtype = np.uint8)

        self.config_match = re.compile(b'\xff{2}.{6}\xff{2}')

        self.scan_mode = 0
        self.eight_bit_output = 1
        self.point_buffer = []

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
            assert (self.buffer[self.current_y][0] == 0)
        
        if self.current_x > 0:
            partial_start_points = self.x_width - self.current_x
            if print_debug:
                print(f'partial start points: {partial_start_points}')
                assert (self.buffer[self.current_y][0] == 0)
            if partial_start_points > m_len: ## the current line will not be completed
                full_lines = 0
                self.buffer[self.current_y][self.current_x:(self.current_x + m_len)] = \
                    m[0:partial_start_points]
                partial_end_points = 0
                if print_debug:
                    print(f'partial start points {partial_start_points} > data len {m_len}')
                    assert (self.buffer[self.current_y][0] == 0)
            else: ## fill in to the end of current line
                full_lines = ((m_len) - partial_start_points)//self.x_width
                self.buffer[self.current_y][self.current_x:self.x_width] = \
                    m[0:partial_start_points]
                partial_end_points = (m_len - partial_start_points)%self.x_width

            if print_debug:
                print(f'full lines: {full_lines}')
                print(f'top rollover index 0:{partial_start_points}')  
                assert (self.buffer[self.current_y][0] == 0) 
            
            def check_frame_rollover():
                if self.current_y >= self.y_height - 1:
                    self.current_y = 0
                else:
                    self.current_y + 1
            check_frame_rollover()

        else: 
            partial_start_points = 0
            partial_end_points = m_len%self.x_width
            full_lines = m_len//self.x_width
            if print_debug:
                print("no top rollover")
                print(f'full lines: {full_lines}')
                assert (self.buffer[self.current_y][0] == 0)

        
        ## fill in solid middle rectangle

        if not full_lines == 0:
            print(f'{full_lines} >= {self.y_height}?')
            if full_lines >= self.y_height:
                full_frames = full_lines//self.y_height
                extra_lines = m_len%self.y_height
                if print_debug:
                    print(f'{full_frames} full frames')
                    print(f'{extra_lines} extra lines')
                    assert (self.buffer[self.current_y][0] == 0)


            print(f'{self.current_y + full_lines} >= {self.y_height}?')
            if (self.current_y + full_lines) >= self.y_height:
                bottom_rows = self.y_height - self.current_y
                top_rows =  full_lines - bottom_rows
                if print_debug:
                    print("rolled into next frame")
                    print(f'bottom rows: {bottom_rows}')
                    print(f'set to: {partial_start_points} : {partial_start_points + self.x_width*bottom_rows}')
                    assert (self.buffer[self.current_y][0] == 0)

                self.buffer[self.current_y:] = \
                        m[partial_start_points:(partial_start_points + self.x_width*bottom_rows)]\
                            .cast('B',shape=([bottom_rows,self.x_width]))

                if top_rows == 0:
                    self.current_y = top_rows
                else:
                    if print_debug:
                        print(f'top rows: {top_rows}')
                        print(f'set to: {partial_start_points + self.x_width*bottom_rows} :\
                             {partial_start_points + self.x_width*bottom_rows+ self.x_width*top_rows}')
                        print(f'buffer shape: 0:{top_rows}')
                        print(f'cast shape: {top_rows},{self.x_width}')
                        assert (self.buffer[self.current_y][0] == 0)
                    self.buffer[0:top_rows] = \
                            m[(partial_start_points + self.x_width*bottom_rows):\
                                (partial_start_points + self.x_width*bottom_rows+ self.x_width*top_rows)]\
                                .cast('B',shape=([top_rows,self.x_width]))
                    if top_rows >= self.y_height: ## there's more than one full frame left
                        skip_frames = top_rows//self.y_height
                        extra_rows = top_rows%self.y_height
                        self.buffer[0:extra_rows] = \
                                m[(partial_start_points + self.x_width*self.y_height*skip_frames):\
                                    (partial_start_points + self.x_width*self.y_height*skip_frames + self.x_width*extra_rows)]\
                                    .cast('B',shape=([top_rows,self.x_width]))
                        self.current_y = extra_rows
                    else:
                        self.current_y = top_rows
            
            else:
                if print_debug:
                    print(f'buffer[{self.current_y}:{self.current_y+full_lines}]')
                    print(f'set to data [{partial_start_points}:{partial_start_points + self.x_width*full_lines}]')
                    assert (self.buffer[self.current_y][0] == 0)
                self.buffer[self.current_y:self.current_y+full_lines] = \
                        m[partial_start_points:(partial_start_points + self.x_width*full_lines)]\
                            .cast('B',shape=([full_lines,self.x_width]))
                self.current_y += full_lines


        if print_debug:
            print(f'partial end points: {partial_end_points}')
            assert (self.buffer[self.current_y][0] == 0)


        self.buffer[self.current_y][0:partial_end_points] = m[m_len-partial_end_points:]

        self.current_x = partial_end_points

        if print_debug:
            print(self.buffer)
            assert (self.buffer[self.current_y][0] == 0)
        # try:
        #     assert (self.buffer[self.current_y][0] == 0)
        # except AssertionError:
        #     print("****frame is out of sync****")
    
    def points_to_vector(self, m:memoryview):
        full_points = len(m)//6
        #extra = len(m)%6
        points = m[0:full_points*6].cast('H', shape=[full_points,3])
        points = points.append(self.point_buffer)
        for n in p.tolist():
            x, y, a  = n
            self.buffer[y][x] = a
        self.point.buffer = m[full_points*6:].tolist()

    def handle_data_with_config(self, data:memoryview, config = None):
        if not config == None:
            print("using this: config")
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
                if self.eight_bit_output == 1:
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
        f = d[0:4].tolist()
        print("decoded config packet", f)
        new_x = f[0]*256  + f[1] + 1
        new_y = f[2]*256 + f[3] + 1
        
        if ((new_x != self.x_width) | (new_y != self.y_height)):
            self.current_x = 0
            self.current_y = 0
            self.change_buffer(new_x, new_y)

        print(f'x width, y height: {self.x_width}, {self.y_height}')

        s = d[4:6].tolist()
        self.scan_mode = s[0]
        self.eight_bit_output = s[1]
        print(f'scan mode: {self.scan_mode}')
        print(f'8bit mode: {self.eight_bit_output}')
        

    def parse_config_from_data(self, d:bytes, print_debug=False):
        n = re.finditer(self.config_match, d)
        prev_stop = 0
        prev_config = None
        try: 
            match = next(n)
            start, stop = match.span()
            config = match.group()
            data = d[prev_stop:start]
            if print_debug:
                print("Config packet detected")
                print(f'start, stop: {start}, {stop}')
                print(f'data: {prev_stop}:{start}')
            prev_stop = stop
            prev_config = config
            self.handle_data_with_config(memoryview(data))
        except StopIteration:
            if print_debug:
                print("No config packets in here")
            self.handle_data_with_config(memoryview(d))

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
                self.handle_data_with_config(memoryview(data), memoryview(prev_config[2:8]))
                prev_stop = stop
                prev_config = config
            except StopIteration:
                data = d[prev_stop:]
                if print_debug:
                    print("Stop")
                    print(f'data: {prev_stop}:')
                if prev_config == None:
                    self.handle_data_with_config(memoryview(data))
                else:
                    self.handle_data_with_config(memoryview(data), memoryview(prev_config[2:8]))
                break

            













if __name__ == "__main__":
    def test_frame_stuffing():
        data = [252, 253, 254] + [n for n in range(0,255)]*10 + [0, 1, 2]
        d = bytes(data)
        m = memoryview(d)
        s = ScanStream()
        #s.change_buffer(255, 255)
        s.current_x = 509
        s.current_y = 510
        s.points_to_frame(m)

    test_frame_stuffing()