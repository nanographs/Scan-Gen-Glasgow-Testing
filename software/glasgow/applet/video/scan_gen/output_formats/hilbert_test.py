from hilbertcurve.hilbertcurve import HilbertCurve


def hilbert():
    N = 2 # number of dimensions

    #text_file = open("hilbert.txt", "w")
    points = []

    pmax = 10
    side = 2**pmax
    min_coord = 0
    max_coord = side - 1
    cmin = min_coord - 0.5
    cmax = max_coord + 0.5

    offset = 0
    dx = 0.5

    for p in range(pmax, 0, -1):
        hc = HilbertCurve(p, N)
        sidep = 2**p

        npts = 2**(N*p)
        pts = []
        for i in range(npts):
            pt = hc.point_from_distance(i)
            x = pt[0]*side/sidep + offset
            y = pt[1]*side/sidep + offset
            yield int(x)
            yield int(y)
            yield 1

        offset += dx
        dx *= 2
        # pts = [
        #     [(pt[0]*side/sidep) + offset,
        #     (pt[1]*side/sidep) + offset]
        #     for pt in pts]


        # for i in pts:
        #     print(i)
        #     #text_file.write(str([int(i[0]*8), int(i[1]*8), 2])+",\n")
        #     points.append([int(i[0]), int(i[1]), 2])


        #yield points

# def hilbert_generator():
#     points = next(hilbert())
#     yield points

    

if __name__ == "__main__":
    hil = hilbert()
    for n in range(100):
        print(next(hil))
        
        
    