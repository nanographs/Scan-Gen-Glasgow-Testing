data = []

## create data
for num in range(0,pow(2,14)+1):
    bits = [n for n in bin(num)[2:].zfill(14)]
    data.append(int("".join(bits[7:14]),2))
    data.append(int("".join(bits[0:7]),2))

## process data
last_7_bits = [data[index]for index in range(0, len(data),2)]
first_7_bits = [data[index]*pow(2,7) for index in range(1, len(data)-1,2)]

combined = [first_7_bits[index] + last_7_bits[index] for index in range(min(len(last_7_bits),len(first_7_bits)))]

file = open("TEST_fifo_output.txt","w")
for n in range(len(combined)):
    start = data[2*n:(2*n+2)]
    end = combined[n]
    print(start,end)
    file.write(f'{start}, {end}\n')


