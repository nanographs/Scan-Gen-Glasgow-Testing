import struct

def get_two_bytes(n: int):
    bits = "{0:016b}".format(n)
    b1 = int(bits[0:8], 2)
    b2 = int(bits[8:16], 2)
    return b1, b2


def generate_raster_config(x_resolution, y_resolution):
    x1, x2 = get_two_bytes(x_resolution-1)
    y1, y2 = get_two_bytes(y_resolution-1)
    config_packet = [255, 255, x1, x2, y1, y2, 1, 1, 255, 255]
    return config_packet


def generate_vector_config(x_resolution, y_resolution):
    x1, x2 = get_two_bytes(x_resolution-1)
    y1, y2 = get_two_bytes(y_resolution-1)
    config_packet = [255, 255, x1, x2, y1, y2, 3, 0, 255, 255]
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

def get_next_pixel(x_resolution, y_resolution):
    x = 0
    y = 0

    while True:
        if x >= x_resolution:
            x = 0
            y += 1
        if y >= y_resolution:
            y = 0
        b1, b2 = get_two_bytes(x)
        x += 1
        yield b2


def generate_packet_with_config(x_resolution, y_resolution):
    config = generate_raster_config(x_resolution, y_resolution)
    packet = config
    n = 10
    framegenerator = get_next_pixel(x_resolution, y_resolution)
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
    vec_stream = generate_vector_stream_singlepoint([255, 255, 0])
    packet = []
    while True:
        n = 0
        while n <= 16383:
            packet.append(next(vec_stream))
            n += 1
        yield packet


from hilbert_test import hilbert

def generate_hilbert_packet():
    vec_stream = hilbert()
    packet = bytearray()
    while True:
        n = 0
        while n <= 16383:
            val = next(vec_stream)
            packet.extend(struct.pack( "<H", val ))
            n += 1
        yield packet





if __name__ == "__main__":
    h = generate_hilbert_packet()
    print(next(h))
    #print(bytes(generate_raster_config(400,400)))
    # packet_generator = generate_packet_with_config(400,400)
    # text_file = open("fakepackets.txt", "w")
    # for n in range(3):
    #     text_file.write(str(next(packet_generator)))

    #packet_generator = generate_vector_packet()
    #print(next(packet_generator))

