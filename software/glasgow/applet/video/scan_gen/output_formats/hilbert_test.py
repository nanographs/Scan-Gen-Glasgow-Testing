from hilbertcurve.hilbertcurve import HilbertCurve


def hilbert(dwell_time = 0):
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
            yield dwell_time

        offset += dx
        dx *= 2


    

if __name__ == "__main__":
    hil = hilbert()
    for n in range(16384):
        print(f'n:{n}')
        print(next(hil))
        
        
    