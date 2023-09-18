import socket
import asyncio

# HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
# PORT = 1234  # Port to listen on (non-privileged ports are > 1023)
# sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# sock.connect((HOST, PORT))

n = 0
async def scan():
    global n
    # global sock, n
    print("in scan")
    await asyncio.sleep(0)
    print("slept")
    msg = ("scan").encode("UTF-8")
    event_loop = asyncio.get_event_loop()
    print(event_loop)
    if n < 10:
        # n += 1
        print("scan", n), 
        sock.send(msg)
        data = sock.recv(16384)
        return data
        #threading.Thread(target=updateData).start()
    #return "result"
    # event_loop.close()



# scanning = False
def watch_scan():
    global scanning, n
    # scanning = True
    task_scan = None
    print("Start")
    while True:
        n += 1
        print("In loop", n)
        if n >= 10:
            scanning = False
            break
        if scanning and task_scan is None:
            event_loop = asyncio.get_event_loop()
            # print(event_loop)
            task_scan = asyncio.ensure_future(scan()) ## start scanning, in another thread or something
            print("set task")
            # #event_loop.run_forever()
            event_loop.run_until_complete(task_scan)
            
            print('task: {!r}'.format(task_scan))
            #print(task_scan.result())
            print("eeee")
            scanning = False
        elif not scanning and task_scan:
            print("End")
            if not task_scan.cancelled():
                task_scan.cancel()
            else:
                task_scan = None
            # break
            task_scan = None
            scanning = True

        elif not scanning and not task_scan:
            print("Nothing to see here")

# scanning = True
# watch_scan()

# run_app = asyncio.ensure_future(watch_scan())
# event_loop = asyncio.get_event_loop()
# event_loop.run_forever()
# # event_loop.run_until_complete(run_app)

# print("Start from the top")

