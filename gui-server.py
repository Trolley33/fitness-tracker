import socket
import threading
import queue
import select
import sqlite3


def db_handler(db_name):
    with sqlite3.connect(db_name) as db:
        while 1:
            try:
                if not db_in.empty():
                    cursor = db.cursor()
                    x = cursor.execute(db_in.get())
                    if x:
                        db_out.put(list(x))
            except Exception as e:
                print(e)
                break
            db.commit()

db_in = queue.Queue()
db_out = queue.Queue()

d = threading.Thread(target=db_handler, args=("db/db.db",))
d.setDaemon(True)
d.start()

# setup
s = socket.socket()

server = (socket.gethostname(), 54321)

# create
s.bind(server)

s.listen(10)


def handler(c, a):
    while 1:
        try:
            ready = select.select([c], [], [], 0.5)
            if ready[0]:
                reply = c.recv(1024)
                reply = reply.decode()
                if not reply:
                    break
                print('received', reply)
                split = reply.split("|")
                # load|who|username|activities|timespan
                if split[0] == "profile" and len(split) >= 3:
                    friend_id = split[1]
                    user_id = split[2]
                    if friend_id != user_id:
                        db_in.put(
                            """SELECT * FROM friends
                               WHERE (friends.friend_id = {0} AND friends.id = {1})
                               OR (friends.friend_id = {1} AND friends.id = {0})""".format(user_id, friend_id))
                        result = db_out.get(True, 2)
                    else:
                        result = True
                    if result:
                        timespan = 4
                        activities = ()
                        flag = ""
                        if len(split) == 5:
                            timespan = split[4]
                        if len(split) >= 4:
                            activities = split[3]
                        if not activities:
                            flag = "NOT"
                        query = ("""SELECT login.username, feed.activity, feed.metadata, feed.date
                                    FROM login
                                    JOIN feed
                                    ON login.id=feed.id
                                    WHERE date(feed.date) >= date('now', '-{} day')
                                    AND feed.activity {} IN {}
                                    AND login.id={}
                                    ORDER BY feed.date DESC""".format(timespan, flag, str(activities), friend_id))
                        db_in.put(query)
                        result = db_out.get(True, 2)
                        if result:
                            c.send('|'.join([str(x) for x in result]).encode())
                    else:
                        print("not friends youth")
                if split[0] == "feed" and len(split) >= 2:
                    user_id = split[1]
                    print(user_id)

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
