import socket
import threading
import queue
import select
import time

# setup
s = socket.socket()

server = (socket.gethostname(), 54321)

# create
s.bind(server)

s.listen(10)


def send_nudes(recipient, victim):
    # search database for victim to give to the recipient
    return "your mum lel " + victim


def new_nudes(sender, victim):
    # put nudes in database with sender id/name whatever
    pass


def handler(c, a):
    while 1:
        try:
            ready = select.select([c], [], [], 0.5)
            if ready[0]:
                reply = c.recv(1024)
                reply = reply.decode()
                print('received', reply)
                split = reply.split("|")
                # commands send_nudes, here's some nudes
                if split[0] == "send_nudes":
                    if len(split) == 3:
                        c.send(send_nudes(split[1], split[2]).encode())
                if split[0] == "have_nudes":
                    if len(split) == 3:
                        c.send("nudes confirmed".encode())
                        new_nudes(split[1], split[2])

        except Exception as e:
            print(e)
            break
    c.close()
    print("closed connection with", a)

while 1:
    print("listening on", *server)
    client, address = s.accept()
    print("... connected from", address)
    t = threading.Thread(target=handler, args=(client, address))
    t.setDaemon(True)
    t.start()

