import socket
import threading
import queue
import select
import time

# setup
s = socket.socket()

server = (socket.gethostname(), 54321)

s.connect(server)

output_queue = queue.Queue()


def handler(s, a):
    while 1:
        try:
            ready = select.select([s], [], [], 0.5)
            if ready[0]:
                reply = s.recv(1024)
                reply = reply.decode()
                if not reply:
                    break
                print('received', reply)
            if not output_queue.empty():
                msg = output_queue.get()
                s.send(msg.encode())
        except Exception as e:
            print(e)
            break
    s.close()
    print("closed connection with", a)

t = threading.Thread(target=handler, args=(s, server))
t.setDaemon(True)
t.start()

while 1:
    ui = input("> ")
    output_queue.put(ui)

