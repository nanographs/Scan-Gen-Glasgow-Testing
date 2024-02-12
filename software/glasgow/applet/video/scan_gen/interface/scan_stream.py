import re
import array
import numpy as np
import time

#import matplotlib.pyplot as plt
#from mock_output import generate_raster_packet_with_config, generate_vector_packet, get_two_bytes

import struct 
def get_two_bytes(n: int):
    b = struct.pack('H', n)
    b1, b2 = list(b)
    return b2, b1

class ScanStream:
    def __init__(self):
        self.y_height = 512
        self.x_width = 512

        self.current_x = 0
        self.current_y = 0

        self.x_upper = self.x_width
        self.x_lower = 0
        self.y_upper = self.y_height
        self.y_lower = 0

        ## frame-shaped buffer
        self.buffer = np.zeros(shape = (self.y_height,self.x_width),dtype = np.uint8) 

        self.config_match = re.compile(b'\xff{2}.{14}\xff{2}', flags=re.DOTALL)

        self.scan_mode = 0
        self.eight_bit_output = 0
        self.patterngen = None

        ## place to stash <6 bytes of an incomplete vector point
        ## until the point is completed in the next packet
        self.point_buffer = bytearray()

        ## stream-shaped buffer
        self._buffer = bytearray()

        self.totalbytes = 0
    
    def writeto(self, d:bytes, print_debug = False):
        if print_debug:
            print(f'extend {len(d)} bytes')
        self._buffer.extend(d)
        if print_debug:
            print(f'length: {len(self._buffer)}')
        self.readfrom()
    
    def readfrom(self, print_debug = False):
        if print_debug:
            print(f'buffer len: {len(self._buffer)}')
        while len(self._buffer) >= 16384:
            if print_debug:
                print("chunk 16384")
            d = self._buffer[:16384]
            self._buffer = self._buffer[16384:]
            if print_debug:
                print(f'new buffer length: {len(self._buffer)}')
            self.parse_config_from_data(d)
        


    def change_buffer(self, x_width, y_height):
        self.x_width = x_width
        self.y_height = y_height
        self.buffer = np.zeros(shape=(self.y_height, self.x_width),
                dtype = np.uint8)
        print("new buffer size:", x_width, y_height)
        self.current_x = self.x_lower
        self.current_y = self.y_lower

    def clear_buffer(self):
        self.buffer = np.zeros(shape=(self.y_height, self.x_width),
                    dtype = np.uint8)
        print("cleared buffer")

    def check_left_sync(self):
        b1, b2 = get_two_bytes(self.x_lower)
        print(f'checking if buffer[{self.current_y},{self.x_lower}] == {b2}')
        assert(self.buffer[self.current_y,self.x_lower] == self.x_lower)

    
    def new_points_to_frame(self, m:memoryview, print_debug = True):
        data_length = len(m)
        if print_debug:
            print("\tdata length:", data_length)
            print("\tframe size (x, y):", self.x_width, self.y_height)
            print("\tcurrent x, current y:", self.current_x, self.current_y)
            print("\tx lower, x upper:", self.x_lower, self.x_upper)
            print("\ty lower, y upper:", self.y_lower, self.y_upper)
        
        buffer_segment_start = 0
        buffer_segment_end = 0

        while True:
            ## not bothering to deal with the case of 1 pixel by 1 pixel
            if (self.x_upper - self.x_lower) <= 1:
                break
            if (self.y_upper - self.y_lower) <= 1:
                break
            #     
            # [....................................]
            #
            #             LX    CX     UX
            #             │      │     │
            #    (0,0)    │      │     │
            #      ┌──────┼──────┼─────┼─────┐RX
            #      │      │      │     │     │
            #      │      │      │     │     │
            #      │      │      │     │     │
            #      │      │      │     │     │
            # LY───┼──────┼──────┼─────┼─────┤
            #      │      │      │     │     │
            #      │      │      ▼     │     │
            #  CY──┼──────┼─────►      │     │
            #      │      │            │     │
            #      │      │            │     │
            # UY───┼──────┼────────────┼─────┤
            #      │      │            │     │
            #      │      │            │     │
            #      │      │            │     │
            #      └──────┴────────────┴─────┘
            #     RY

            # [######..............................]
            #
            #             LX    CX     UX
            #             │      │     │
            #    (0,0)    │      │     │
            #      ┌──────┼──────┼─────┼─────┐RX
            #      │      │      │     │     │
            #      │      │      │     │     │
            #      │      │      │     │     │
            #      │      │      │     │     │
            # LY───┼──────┼──────┼─────┼─────┤
            #      │      │      │     │     │
            #      │      │      ▼     │     │
            #  CY──┼──────┼─────►######│     │
            #      │      │            │     │
            #      │      │            │     │
            # UY───┼──────┼────────────┼─────┤
            #      │      │            │     │
            #      │      │            │     │
            #      │      │            │     │
            #      └──────┴────────────┴─────┘
            #     RY
            #
            

            ### ===========================STEP A: FIRST LINE================================
            if not self.current_x == self.x_lower:
                if print_debug:
                    print("\t===STEP 1: FIRST LINE===")
                buffer_segment_end += self.x_upper - self.current_x
                if buffer_segment_end > data_length: ## if the data doesn't reach the end of the line
                    self.buffer[self.current_y][self.current_x:(self.current_x+data_length)] =\
                        m[buffer_segment_start:data_length].cast('B')
                    break
                

                if print_debug:
                    print(f'\t\t packet [{buffer_segment_start}:{buffer_segment_end}] out of {data_length}')
                    print(f'\t\t      {self.x_lower: <5}    {self.current_x: <5}           {self.x_upper: <5}')
                    print(f'\t\t{self.current_y: <5} [--------#################]     ')

                self.buffer[self.current_y][self.current_x:self.x_upper] =\
                    m[buffer_segment_start:buffer_segment_end].cast('B')
                buffer_segment_start += buffer_segment_end
                
                self.current_x = self.x_lower

                ### roll over into the next frame if necessary
                if self.current_y + 1 == self.y_upper:
                    if print_debug:
                        print(f'\tat end of frame, y = {self.current_y} --> y = {self.y_upper}')
                    self.current_y = self.y_lower
                else:
                    self.current_y += 1
                

            

            ### ===========================STEP 2: FULL LINES TO END OF FRAME================================
            full_lines = (data_length - buffer_segment_start)//(self.x_upper - self.x_lower)
            total_full_lines = full_lines
            if print_debug:
                print("\t===STEP 2: FULL LINES TO END OF FRAME===")
                print(f'\t\tpacket contains {full_lines} full lines')

            while (self.current_y + full_lines) > self.y_upper:
                #  [######..............................]
                #        ^
                #
                #       LX         UX
                #       |          |
                #   CY──............ 
                #       ............
                #       ............
                #   UY──............──lines_left_in_frame
                #       ............──full_lines
                #       .....  
                #   

                lines_left_in_frame = self.y_upper - self.current_y

                
                #             LX           UX
                #             CX           │
                #    (0,0)    │            │
                #      ┌──────┼────────────┼─────┐RX
                #      │      │            │     │
                #      │      │            │     │
                #      │      │            │     │
                #      │      │            │     │
                # LY───┼──────┼────────────┼─────┤
                #      │      │            │     │
                #      │      |            │     │
                #      │      ▼      ######│     │
                #  CY──┼──────►++++++++++++│     │
                #      │      │++++++++++++│     │
                # UY───┼──────┼────────────┼─────┤
                #      │      │            │     │
                #      │      │            │     │
                #      │      │            │     │
                #      └──────┴────────────┴─────┘
                #     RY
                #
                # [######++++++++++++++++++++++++......]  

                buffer_segment_end += (self.x_upper - self.x_lower)*lines_left_in_frame

                if print_debug:
                    print(f'\t\t packet [{buffer_segment_start}:{buffer_segment_end}] out of {data_length}')
                    print(f'\t\t with shape ({lines_left_in_frame},{self.x_upper-self.x_lower})')
                    print(f'\t\t      {self.x_lower: <5}                    {self.x_upper: <5}')
                    print(f'\t\t{self.current_y: <5} [+++++++++++++++++++++++++]     ')
                    print(f'\t\t      [+++++++++++++++++++++++++]     +{lines_left_in_frame} lines')
                    print(f'\t\t{self.y_upper: <5}                    {full_lines - lines_left_in_frame} remaining / {total_full_lines} total')
                    
                self.buffer[self.current_y:self.y_upper,self.x_lower:self.x_upper] = \
                    m[buffer_segment_start:buffer_segment_end]\
                        .cast('B',shape = (lines_left_in_frame, (self.x_upper - self.x_lower)))
                
                buffer_segment_start = buffer_segment_end
                full_lines -= lines_left_in_frame
                self.current_y = self.y_lower

            #if self.current_y + full_lines < self.y_upper: 
            if full_lines > 0:
                if print_debug:
                    print(f'\t===STEP 2B: FULL LINES, SAME FRAME ===')
                #  [######..............................]
                #        ^
                #
                #       LX         UX
                #       |          |
                #   CY__............ 
                #       ............__ full_lines
                #       ......
                #   UY__   
                #     

                #
                #             LX           UX
                #             CX           │
                #    (0,0)    │            │
                #      ┌──────┼────────────┼─────┐RX
                #      │      │            │     │
                #      │      │            │     │
                #      │      │            │     │
                #      │      │            │     │
                # LY───┼──────┼────────────┼─────┤
                #      │      │            │     │
                #      │      |            │     │
                #      │      ▼      ######│     │
                #  CY──┼──────►++++++++++++│     │
                #      │      │++++++++++++│     │
                # UY───┼──────┼────────────┼─────┤
                #      │      │            │     │
                #      │      │            │     │
                #      │      │            │     │
                #      └──────┴────────────┴─────┘
                #     RY
                #
                # [######++++++++++++++++++++++++......]

                buffer_segment_end += (self.x_upper - self.x_lower)*full_lines
                
                if print_debug:
                    print(f'\t\t packet [{buffer_segment_start}:{buffer_segment_end}] out of {data_length}')
                    print(f'\t\t with shape ({full_lines},{self.x_upper-self.x_lower})')
                    print(f'\t\t      {self.x_lower: <5}                    {self.x_upper: <5}')
                    print(f'\t\t{self.current_y: <5} [+++++++++++++++++++++++++]     ')
                    print(f'\t\t      [+++++++++++++++++++++++++]     +{full_lines}')
                    print(f'\t\t{self.current_y+full_lines: <5}                    0 remaining / {total_full_lines} total')
                self.buffer[self.current_y:self.current_y + full_lines, self.x_lower:self.x_upper] = \
                    m[buffer_segment_start:buffer_segment_end]\
                        .cast('B', shape = (full_lines, self.x_upper - self.x_lower))
                
                buffer_segment_start = buffer_segment_end
                self.current_y += full_lines

            #             LX    CX     UX
            #             |     |      │
            #    (0,0)    │     |      │
            #      ┌──────┼─────┼──────┼─────┐RX
            #      │      │     |      │     │
            #      │      │     |      │     │
            #      │      │     |      │     │
            #      │      │     |      │     │
            # LY───┼──────┼─────┼──────┼─────┤
            #      │      │     |      │     │
            #      │      |     |      │     │
            #      │      |     |######│     │
            #      |      |+++++|++++++│     │
            #      │      │+++++▼++++++│     │
            # CY───┼──────►@@@@@@      │     │
            # UY───┼──────┼────────────┼─────┤
            #      │      │            │     │
            #      │      │            │     │
            #      │      │            │     │
            #      └──────┴────────────┴─────┘
            #     RY
            #
            # [######++++++++++++++++++++++++@@@@@@]  
            #                               ^     ^ 

            ### ===========================STEP 3: LAST LINE================================
            remaining_points = data_length - buffer_segment_start
            self.current_x = self.x_lower + remaining_points


            if remaining_points > 0:
                if print_debug:
                    print("\t===STEP 3: LAST LINE===")
                    print(f'\t\t{remaining_points} remaining, brings current x to {self.current_x}')
                    print(f'\t\t packet [{buffer_segment_start}:{data_length}] out of {data_length}')
                    print(f'\t\t      {self.x_lower: <5}    {self.current_x: <5}           {self.x_upper: <5}')
                    print(f'\t\t{self.current_y: <5} [@@@@@@@@-----------------]     ')

                self.buffer[self.current_y, self.x_lower:self.current_x] = \
                    m[buffer_segment_start:data_length].cast('B')

            break

            self.check_left_sync()

            





        


        

    def points_to_frame(self, m:memoryview, print_debug = True):
        cast_type = 'B'

        m_len = len(m)
        if print_debug:
            print("data length:", m_len)
            print("frame size (x, y):", self.x_width, self.y_height)
            print("current x, current y:", self.current_x, self.current_y)
        
        current_x = self.current_x + self.x_lower
        current_y = self.current_y + self.y_lower
        x_width = self.x_upper - self.x_lower
        y_height = self.y_upper - self.y_lower

        if print_debug:
            print("ROI frame size (x, y):", x_width, y_height)
            print("ROI current x, current y:", current_x, current_y)
            print(f'current line: {self.buffer[current_y]}')
            print(f'{self.buffer[current_y][current_x]}')
        

        if self.current_x > 0: ## if not at the beginning of a line
            partial_start_points = x_width - self.current_x
            if print_debug:
                print(f'partial start points: {partial_start_points}')
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
                    print(f'buffer [{current_y}][{current_x}:{x_width + self.x_lower}]')
                    print(f'set to m[0:{partial_start_points}]')
                full_lines = ((m_len) - partial_start_points)//x_width
                self.buffer[current_y][current_x:(x_width+self.x_lower)] = \
                    m[0:partial_start_points]
                partial_end_points = (m_len - partial_start_points)%x_width

            if print_debug:
                print(f'current line: {self.buffer[current_y]}')
                print(f'full lines: {full_lines}')
                print(f'top rollover index 0:{partial_start_points}')  
                self.check_sync()
            
            if current_y >= y_height - 1:
                current_y = self.y_lower
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

        
        ## fill in solid middle rectangle

        if not full_lines == 0:
            if print_debug:
                print(f'{full_lines} >= {y_height}?')
            if full_lines >= y_height:
                full_frames = full_lines//y_height
                extra_lines = m_len%y_height
                if print_debug:
                    print(f'{full_frames} full frames')
                    print(f'{extra_lines} extra lines')

            if print_debug:
                print(f'{current_y + full_lines} >= {y_height}?')
            if (current_y + full_lines) >= y_height:
                bottom_rows = y_height - current_y
                top_rows =  full_lines - bottom_rows
                if print_debug:
                    print("rolled into next frame")
                    print(f'bottom rows: {bottom_rows}')
                    print(f'buffer [{current_y}:{current_y + bottom_rows},{self.x_lower}:{self.x_lower+x_width}]')
                    print(f'with shape {self.buffer[current_y:(current_y + bottom_rows),self.x_lower:self.x_lower+x_width].shape}')
                    print(f'set to data [{partial_start_points} : {partial_start_points + x_width*bottom_rows}]')
                    print(f'with m shape {m[partial_start_points:(partial_start_points + x_width*bottom_rows)].shape}')
                    print(f'with shape [{bottom_rows}, {x_width}]')
                    

                self.buffer[current_y:(current_y + bottom_rows),self.x_lower:self.x_lower+x_width] = \
                        m[partial_start_points:(partial_start_points + x_width*bottom_rows)]\
                            .cast(cast_type,shape=([bottom_rows,x_width]))

                if print_debug:
                    self.check_sync()

                if top_rows == 0:
                    current_y = top_rows
                else:
                    if print_debug:
                        print(f'top rows: {top_rows}')
                        print(f'buffer [0:{top_rows},{self.x_lower}:{self.x_lower+x_width}]')
                        print(f'with shape {self.buffer[0:top_rows, self.x_lower:self.x_lower+x_width].shape}')
                        print(f'set to: {partial_start_points + x_width*bottom_rows} :{partial_start_points + x_width*bottom_rows+ x_width*top_rows}')
                        print(f'cast shape: {top_rows},{self.x_width}')

                    self.buffer[0:top_rows, self.x_lower:self.x_lower+x_width] = \
                            m[(partial_start_points + x_width*bottom_rows):\
                                (partial_start_points + x_width*bottom_rows+ x_width*top_rows)]\
                                .cast(cast_type,shape=([top_rows,x_width]))
                    if print_debug:
                        self.check_sync()

                    if top_rows >= y_height: ## there's more than one full frame left
                        skip_frames = top_rows//y_height
                        extra_rows = top_rows%y_height
                        self.buffer[0:extra_rows] = \
                                m[(partial_start_points + x_width*y_height*skip_frames):\
                                    (partial_start_points + x_width*y_height*skip_frames + x_width*extra_rows)]\
                                    .cast(cast_type,shape=([top_rows,x_width]))
                        current_y = extra_rows
                    else:
                        current_y = top_rows
            
            else:
                if print_debug:
                    print(f'buffer[{current_y}:{current_y+full_lines}][{self.x_lower}:{self.x_lower + x_width}]')
                    print(f'with shape {self.buffer[current_y:current_y+full_lines, self.x_lower:self.x_lower+x_width].shape}')
                    print(f'set to data [{partial_start_points}:{partial_start_points + x_width*full_lines}]')
                    print(f'with shape [{full_lines},{x_width}]')
                self.buffer[current_y:current_y+full_lines,self.x_lower:self.x_lower+x_width] = \
                        m[partial_start_points:(partial_start_points + x_width*full_lines)]\
                            .cast(cast_type,shape=([full_lines,x_width]))
                # if print_debug:
                #     print(f'beginning of block: {self.buffer[current_y]}')
                current_y += full_lines
                # if print_debug:
                #     print(f'end of block: {self.buffer[current_y]}')
                ## printing these takes up way too much space

                if print_debug:
                    self.check_sync()
                



        if print_debug:
            print(f'partial end points: {partial_end_points}')
            print(f'buffer [{current_y}][{self.x_lower}:{self.x_lower + partial_end_points}]')
            print(f' = m[{m_len-partial_end_points}:]')
            print(f'last line: {str(m[m_len-partial_end_points:].tolist())} ')
            print(f'length: {len(m[m_len-partial_end_points:])}')
            self.check_sync()


        self.buffer[current_y][self.x_lower:self.x_lower+partial_end_points] = m[m_len-partial_end_points:]


        self.current_y = current_y - self.y_lower
        self.current_x = partial_end_points

        if print_debug:
            print(self.buffer[self.y_lower:self.y_upper, self.x_lower:self.x_upper])
            #self.check_sync()
    
            

    
    def check_sync(self):
        try:
            assert (self.buffer[self.current_y+self.y_lower][self.x_lower] == self.x_lower)
            b1, b2 = get_two_bytes(self.x_upper-1)
            if b2 == 255:
                b2 = 254
            assert (self.buffer[self.current_y+self.y_lower][self.x_upper-1] == b2)
        except AssertionError:
            b1, b2 = get_two_bytes(self.x_upper-1)
            if b2 == 255:
                b2 = 254
            print("****frame is out of sync****")
            print(f'buffer [{self.current_y + self.y_lower}][{self.x_lower}] != {self.x_lower}')
            print(self.buffer[self.current_y+self.y_lower][self.x_lower-5: self.x_lower+5])
            print(f'buffer [{self.current_y + self.y_lower}][{self.x_upper-1}] != {b2}')
            print(self.buffer[self.current_y+self.y_lower][self.x_upper-1-5: self.x_upper-1+5])
            print(self.buffer[self.current_y+self.y_lower][self.x_upper-1])
            #assert (self.buffer[self.current_y+self.y_lower][self.x_lower] == self.x_lower)
            #assert (self.buffer[self.current_y+self.y_lower][self.x_upper] == b2)


    def points_to_vector(self, m:memoryview, print_debug = True):
        self.point_buffer.extend(m)
        while len(self.point_buffer) >= 2:
            point = self.point_buffer[:2]
            self.point_buffer = self.point_buffer[2:]
            a = memoryview(point).cast('H').tolist()[0]
            if print_debug:
                print(f' a: {a}')
            x2 = next(self.patterngen)
            y2 = next(self.patterngen)
            a2 = next(self.patterngen)
            if print_debug:
                print(f' x2: {x2}, y2: {y2}, a2: {a2}')
            self.buffer[y2][x2] = a
            self.totalbytes += 6
            print(f'total bytes: {self.totalbytes}')
            assert(a == a2)

    def handle_data_with_config(self, data:memoryview, config = None, print_debug = None):
        if not config == None:
            if print_debug:
                print(f'using this config: {config}')
            self.parse_config_packet(config)
        else:
            if print_debug:
                print("continue with existing config")

        if print_debug:
            print("data starts with", data.tolist()[0:10])

        if self.scan_mode == 0:
            pass

        if len(data) > 0: 
            if (self.scan_mode == 1) | (self.scan_mode == 2):
                if self.eight_bit_output == 0:
                    start = time.perf_counter()
                    #data = data.cast('H')
                    eight_bit_data = data.tobytes()[1::2]
                    data = memoryview(eight_bit_data)
                    end = time.perf_counter()
                    if print_debug:
                        print(f'16 to 8 time {end-start}')
                start = time.perf_counter()
                self.new_points_to_frame(data)
                end = time.perf_counter()
                if print_debug:
                    print(f'Time to stuff {end-start}')
            if self.scan_mode == 3:
                start = time.perf_counter()
                self.points_to_vector(data)
                end = time.perf_counter()
                if print_debug:
                    print(f'Time to stuff {end-start}')


    def parse_config_packet(self, d:memoryview, print_debug = False):
        f = d[0:12].tolist()
        if print_debug:
            print("decoded config packet", f)
        new_x = f[0]*256  + f[1] + 1
        new_y = f[2]*256 + f[3] + 1

        new_x_upper = f[4]*256  + f[5]
        new_x_lower = f[6]*256 + f[7]
        new_y_upper = f[8]*256  + f[9]
        new_y_lower = f[10]*256 + f[11]

        if any ([(new_x_upper != self.x_upper), (new_x_lower != self.x_lower), 
            (new_y_upper != self.y_upper), (new_y_lower != self.y_lower)]):
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
            
            self.current_x = self.x_lower
            self.current_y = self.y_lower
        

        if ((new_x != self.x_width) | (new_y != self.y_height)):
            self.change_buffer(new_x, new_y)

        print(f'x width, y height: {self.x_width}, {self.y_height}')
        print(f'x lower, x upper: {self.x_lower}, {self.x_upper}')
        print(f'y lower, y upper: {self.y_lower}, {self.y_upper}')

        s = d[12:14].tolist()
        self.scan_mode = s[0]
        self.eight_bit_output = s[1]
        print(f'scan mode: {self.scan_mode}')
        print(f'8bit mode: {self.eight_bit_output}')
        

    def parse_config_from_data(self, d:bytes, print_debug=True):
        n = re.finditer(self.config_match, d)
        prev_stop = 0
        prev_config = None
        try: 
            match = next(n)
            start, stop = match.span()
            config = match.group()
            data = d[prev_stop:start]
            if print_debug:
                print(f'[{prev_stop}----data----{start}]')
            prev_stop = stop
            prev_config = config
            self.handle_data_with_config(memoryview(data))
            if print_debug:
                print(f'[{start}--config--{stop}]')

            while True:
                try:
                    match = next(n)
                    start, stop = match.span()
                    config = match.group()
                    data = d[prev_stop:start]
                    if print_debug:
                        print(f'[{prev_stop}----data----{start}]')
                    self.handle_data_with_config(memoryview(data), memoryview(prev_config[2:16]))
                    if print_debug:
                        print(f'[{start}config{stop}]')
                    prev_stop = stop
                    prev_config = config
                except StopIteration:
                    data = d[prev_stop:]
                    if print_debug:
                        print(f'[{prev_stop}----data----]\t stop iteration')
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
    from mock_output import generate_raster_packet_with_config, generate_vector_packet, get_two_bytes
    import matplotlib.pyplot as plt
    def test_frame_stuffing():
        #data = [4, 5, 6] + [n for n in range(0,6)]*10 + [0, 1, 2]
        s = ScanStream()
        s.change_buffer(512, 512)
        packet_generator = generate_raster_packet_with_config(512, 512, True, 32, 100, 50, 100)
        for n in range(2):
            data = next(packet_generator)
            d = bytes(data)
            try:
                s.writeto(d)
            except:
                break
        # for n in range(100, 200):
        #     packet_generator = generate_raster_packet_with_config(512,512, False, 32, 255+n, 54, 255+n)
        #     for n in range(100):
        #         print("=====start new packet======")
        #         data = next(packet_generator)
        #         d = bytes(data)
        #         try:
        #             s.writeto(d)
        #         except:
        #             break
        plt.matshow(s.buffer)
        plt.show()

    def test_vector_stuffing():
        s = ScanStream()
        packet_generator = generate_vector_packet()
        for n in range(3):
            print("=====start new packet======")
            data = next(packet_generator)
            d = memoryview(bytes(data))
            s.writeto(d)
        
    #test_vector_stuffing()
    test_frame_stuffing()