import multiprocessing




def sender(connection):
    print("sending")
    data = bytes([5]*16384)
    connection.send(data)
    print("send")

def receiver(connection):
    data = connection.recv()
    print(f'received {data}')

if __name__ == "__main__":
    conn1, conn2 = multiprocessing.Pipe(duplex=True)
    p = multiprocessing.Process(target=sender, args = [conn1])
    p2 = multiprocessing.Process(target=receiver, args = [conn2])
    print("start process")
    p.start()
    p2.start()
    p.join()
    p2.join()

