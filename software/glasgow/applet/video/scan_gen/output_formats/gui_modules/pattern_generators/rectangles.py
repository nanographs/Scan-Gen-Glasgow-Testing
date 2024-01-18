def vector_rectangle(x_width, y_height, dwell, x_lower = None,
x_upper = None, y_lower = None, y_upper = None):
    if x_lower == None:
        x_lower = 0
    if x_upper == None:
        x_upper = x_width
    if y_lower == None:
        y_lower = 0
    if y_upper == None:
        y_upper = y_height
    for y in range(y_lower, y_upper):
        for x in range(x_lower, x_upper):
            yield x
            yield y
            yield dwell

def vector_gradient_rectangle(x_width, y_height, dwell, x_lower = None,
x_upper = None, y_lower = None, y_upper = None):
    if x_lower == None:
        x_lower = 0
    if x_upper == None:
        x_upper = x_width
    if y_lower == None:
        y_lower = 0
    if y_upper == None:
        y_upper = y_height
    for y in range(y_lower, y_upper):
        for x in range(x_lower, x_upper):
            yield x
            yield y
            yield x+y


if __name__ == "__main__":
    from patterngen_utils import packet_from_generator, in2_out1_byte_stream
    r = vector_rectangle(1024,1024,1, 5, 100, 5, 100)
    for n in range(20):
        print(next(r))
    #packet_from_generator(r)