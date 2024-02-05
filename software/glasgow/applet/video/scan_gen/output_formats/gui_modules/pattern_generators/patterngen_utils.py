import struct

def in2_out1_byte_stream(in_gen):
    while True:
        val = next(in_gen)
        bval = struct.pack("H",val)
        yield bytes([bval[0]])
        yield bytes([bval[1]])



def packet_from_generator(gen, two_bytes = True):
    if two_bytes:
        gen = in2_out1_byte_stream(gen)
    while True:
        packet = bytearray()
        for n in range(16384):
            val = next(gen)
            packet.extend(val)
        yield packet
