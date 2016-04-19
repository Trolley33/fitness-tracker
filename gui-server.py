import hashlib
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
                msg = ''
                if split[0] == "profile" and len(split) >= 3:
                    friend_id = split[1]
                    user_id = split[2]
                    if friend_id != user_id:
                        query = """SELECT * FROM friends
                                   WHERE (friends.friend_id = {0} AND friends.id = {1})
                                   OR (friends.friend_id = {1} AND friends.id = {0})""".format(user_id, friend_id)
                        db_in.put(query)
                        result = db_out.get(True, 2)
                    else:
                        result = True
                    if result:
                        time1 = 'now'
                        time2 = 7
                        activities = ()
                        flag = ""
                        if len(split) >= 5:
                            time2 = split[4]
                        if len(split) == 6:
                            time1 = str(split[5]) + " day"
                        if len(split) >= 4:
                            activities = split[3]
                        if not activities:
                            flag = "NOT"
                        query = ("""SELECT login.username, feed.activity, feed.metadata, feed.date, feed.text
                                    FROM login
                                    JOIN feed
                                    ON login.id=feed.id
                                    WHERE date(feed.date) >= date('{}', '-{} day')
                                    AND feed.activity {} IN {}
                                    AND login.id={}
                                    ORDER BY feed.date DESC""".format(time1, time2, flag, str(activities), friend_id))
                        db_in.put(query)
                        result = db_out.get(True, 2)
                        if result:
                            msg = str(result)
                    else:
                        print("not friends youth")
                if split[0] == "feed" and len(split) >= 2:
                    user_id = split[1]
                    time1 = 'now'
                    time2 = 7
                    if len(split) >= 3:
                        time2 = split[2]
                    if len(split) == 4:
                        time1 = str(split[3]) + " day"
                    query = """SELECT login.username, feed.activity, feed.metadata, feed.date, feed.text, login.id
                               FROM login
                               JOIN feed
                               ON login.id=feed.id
                               JOIN friends
                               ON feed.id=friends.friend_id OR feed.id = friends.id
                               WHERE date(feed.date) >= date('{}', '-{} day')
                               AND friends.id = {}
                               ORDER BY feed.date DESC""".format(time1, time2, user_id)
                    db_in.put(query)
                    result = db_out.get(True, 2)
                    if result:
                        msg = str(result)
                if split[0] == "request" and len(split) == 3:
                    what = split[1]
                    if what == "salt":
                        name = split[2]
                        query = ("""SELECT login.salt, login.pass
                                    FROM login
                                    WHERE login.username='{}'""".format(name))
                        db_in.put(query)
                        result = db_out.get(True, 2)
                        if result:
                            salt = result[0][0]
                            msg = salt
                        else:
                            msg = "impossible salt"
                if split[0] == "login" and len(split) == 3:
                    name = split[1]
                    sub_passw = split[2]
                    query = ("""SELECT login.pass, login.id
                                FROM login
                                WHERE login.username='{}'""".format(name))
                    db_in.put(query)
                    result = db_out.get(True, 2)
                    if result:
                        pass_hash = result[0][0]
                        if pass_hash == sub_passw:
                            msg = "true|" + str(result[0][1])
                        else:
                            msg = "false"
                    else:
                        msg = "false"

                if msg:
                    print("sending:", msg)
                    c.send(msg.encode())

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
