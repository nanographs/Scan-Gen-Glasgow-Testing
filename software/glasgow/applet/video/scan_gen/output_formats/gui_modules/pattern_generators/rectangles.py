def vector_rectangle(x_width, y_height, dwell):
    for y in range(y_height):
        for x in range(x_width):
            yield x
            yield y
            yield dwell

def vector_gradient_rectangle(x_width, y_height, dwell):
    for y in range(y_height):
        for x in range(x_width):
            yield x
            yield y
            yield x+y


if __name__ == "__main__":
    from patterngen_utils import packet_from_generator, in2_out1_byte_stream
    r = vector_rectangle(1024,1024,1)
    packet_from_generator(r)