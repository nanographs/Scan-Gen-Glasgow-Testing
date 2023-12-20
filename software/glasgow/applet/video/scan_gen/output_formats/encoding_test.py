import re

data = [255, 255, 255, 0, 255, 0, 3, 1, 255, 255] + [255, 0, 255, 0, 3, 0]*100 + [255, 255, 255, 1, 255, 1, 3, 1, 255, 255] 

d = bytes(data)
print(type(d))

sep = bytes([255,255])

#print(d.find(sep))


pattern = re.compile(b'\xff{2}.{6}\xff{2}')
n = re.finditer(pattern, d)
prev_stop = 0
while True:
    try:
        match = next(n)
        start, stop = match.span()
        config = match.group()
        data = d[prev_stop:start]
        prev_stop = stop
    except StopIteration:
        break

# l = d.partition(bytes([80]))
# print(l)

e = memoryview(d)
