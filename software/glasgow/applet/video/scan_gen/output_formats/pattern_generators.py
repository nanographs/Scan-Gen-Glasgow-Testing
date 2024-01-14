
import struct

def vector_rectangle(x_width, y_height, dwell):
    for y in range(y_height):
        for x in range(x_width):
            yield x
            yield y
            yield dwell

def in2_out1_byte_stream(in_gen):
    while True:
        val = next(in_gen)
        bval = struct.pack("H",val)
        yield bytes([bval[0]])
        yield bytes([bval[1]])



def packet_from_generator(gen):
    gen = in2_out1_byte_stream(gen)
    packet = bytearray()
    for n in range(16384):
        val = next(gen)
        packet.extend(val)
    print(packet)

if __name__ == "__main__":
    r = vector_rectangle(1024,1024,1)
    packet_from_generator(r)