data = [255, 0, 255, 0, 3, 0]*16384 + [80] + [255, 0, 255, 0, 3, 0]*16384 + [80] + [255, 0, 255, 0, 3, 0]*16384

d = bytes(data)
print(type(d))

print(80 in d)
print(d.find(80))

l = d.partition(bytes([80]))
print(l)

e = memoryview(d)
