
def get_two_bytes(n: int):
    bits = "{0:016b}".format(n)
    b1 = int(bits[0:8], 2)
    b2 = int(bits[8:16], 2)
    return b1, b2


def generate_raster_config(x_resolution, y_resolution, eight_bit_output, lx=None, ux=None, ly=None, uy=None):
    x1, x2 = get_two_bytes(x_resolution-1)
    y1, y2 = get_two_bytes(y_resolution-1)
    if lx == None:
        lx1 = 0
        lx2 = 0
    else:
        lx1, lx2 = get_two_bytes(lx)
    if ly == None:
        ly1 = 0
        ly2 = 0
    else:
        ly1, ly2 = get_two_bytes(ly)
    if ux == None:
        ux1, ux2 = x1, x2
    else:
        ux1, ux2 = get_two_bytes(ux)
    if uy == None:
        uy1, uy2 = y1, y2
    else:
        uy1, uy2 = get_two_bytes(uy)
    if eight_bit_output:
        b8 = 1
    else:
        b8 = 0
    config_packet = [255, 255, x1, x2, y1, y2, ux1, ux2, lx1, lx2, uy1, uy2, ly1, ly2, 1, b8, 255, 255]
    return config_packet


def generate_vector_config(x_resolution, y_resolution):
    x1, x2 = get_two_bytes(x_resolution-1)
    y1, y2 = get_two_bytes(y_resolution-1)
    lx1 = 0
    lx2 = 0
    ly1 = 0
    ly2 = 0
    ux1, ux2 = x1, x2
    uy1, uy2 = y1, y2
    config_packet = [255, 255, x1, x2, y1, y2, ux1, ux2, lx1, lx2, uy1, uy2, ly1, ly2, 3, 0, 255, 255]
    return config_packet

def generate_vector_stream_singlepoint(point):
    while True:
        for n in point:
            b1, b2 = get_two_bytes(n)
            yield b2
            yield b1


def generate_frame(x_resolution, y_resolution):
    for y in range(0,y_resolution):
        for x in range(0, x_resolution):
            b1, b2 = get_two_bytes(x)
            print(b2)

def get_next_pixel(x_resolution, y_resolution, eight_bit_output, lx=None, ux=None, ly=None, uy=None):
    x = 0
    y = 0

    if lx == None:
        lx = 0
    if ly == None:
        ly = 0
    if ux == None:
        ux = x_resolution
    if uy == None:
        uy = y_resolution

    while True:
        if x >= ux:
            x = lx
            y += 1
        if y >= uy:
            y = ly
        x += 1
        b1, b2 = get_two_bytes(x)
        if not eight_bit_output:
            yield b1
        yield b2


def generate_raster_packet_with_config(*args, **kwargs):
    config = generate_raster_config(*args, **kwargs)
    packet = config
    n = 10
    framegenerator = get_next_pixel(*args, **kwargs)
    while n <= 16383:
        packet.append(next(framegenerator))
        n += 1
    yield packet
    n = 0
    while True:
        packet = []
        while n <= 16383:
            packet.append(next(framegenerator))
            n += 1
        yield packet
        n = 0

def generate_vector_packet():
    config = generate_vector_config(400,400)
    vec_stream = generate_vector_stream_singlepoint([255, 255, 0])
    packet = config
    n = 10
    while n <= 16383:
        packet.append(next(vec_stream))
        n += 1
    yield packet
    while True:
        packet = []
        n = 0
        while n <= 16383:
            packet.append(next(vec_stream))
            n += 1
        yield packet



if __name__ == "__main__":
    #print(bytes(generate_raster_config(400,400)))
    packet_generator = generate_raster_packet_with_config(400,400, True)
    text_file = open("fakepackets.txt", "w")
    for n in range(3):
        text_file.write(str(next(packet_generator)))

    # packet_generator = generate_vector_packet()
    #print(next(packet_generator))

