import queue
import select
import socket
import sqlite3
import threading


def db_handler(db_name):
    db = sqlite3.connect(db_name)
    while 1:
        try:
            if not db_in.empty():
                y = db_in.get()
                x = db.execute(y).fetchall()
                db.commit()
                if x:
                    db_out.put(x)
                else:
                    db_out.put("")
        except Exception as e:
            print(e)
            break
    db.close()

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


def scrub(text):
    return text.replace("'", "''")


def handler(c, a):
    while 1:
        try:
            ready = select.select([c], [], [], 0.25)
            if ready[0]:
                reply = c.recv(1024)
                reply = scrub(reply.decode())
                if not reply:
                    break
                print('* received:', reply)
                split = reply.split("|")
                # load|who|username|activities|timespan
                msg = ''
                if split[0] == "profile" and len(split) >= 3:
                    friend_id = split[1]
                    user_id = split[2]
                    flag = int(split[3])
                    if friend_id != user_id and not flag:
                        query = """SELECT * FROM friends
                                   WHERE ((friends.friend_id = {0} AND friends.id = {1})
                                   OR (friends.friend_id = {1} AND friends.id = {0}))
                                   AND friends.state='active'""".format(user_id, friend_id)
                        db_in.put(query)
                        result = db_out.get(True, 10)
                    else:
                        result = True
                    if result:
                        max = 6
                        if len(split) >= 4:
                            max = int(split[3])
                        query = ("""SELECT login.username, feed.activity, feed.metadata, feed.date, feed.text, feed.feed_id
                                    FROM login
                                    JOIN feed
                                    ON login.id=feed.id
                                    WHERE login.id={2}
                                    ORDER BY feed.date DESC
                                    LIMIT {0},{1}""".format(max-5, max, friend_id))
                        db_in.put(query)
                        result = db_out.get(True, 10)
                        if result:
                            msg = str(result)
                        else:
                            msg = "[]"
                    else:
                        print("not friends youth")
                if split[0] == "feed" and len(split) >= 2:
                    user_id = split[1]
                    max = 6
                    if len(split) >= 3:
                        max = int(split[2])
                    query = """SELECT DISTINCT login.username, feed.activity, feed.metadata, feed.date, feed.text, login.id, feed.feed_id
                               FROM login
                               JOIN feed
                               ON login.id=feed.id
                               JOIN friends
                               ON feed.id=friends.friend_id OR feed.id=friends.id
                               WHERE (friends.id = {2} OR friends.friend_id = {2})
                               AND friends.state='active'
                               ORDER BY feed.date DESC
                               LIMIT {0},{1}""".format(max-5, max, user_id)
                    db_in.put(query)
                    result = db_out.get(True, 10)
                    if result:
                        msg = str(result)
                    else:
                        msg = "[]"
                if split[0] == "request" and len(split) == 3:
                    what = split[1]
                    if what == "salt":
                        name = split[2]
                        query = ("""SELECT login.salt, login.pass
                                    FROM login
                                    WHERE login.username='{}'""".format(name))
                        db_in.put(query)
                        result = db_out.get(True, 10)
                        if result:
                            salt = result[0][0]
                            msg = salt
                        else:
                            msg = "no user"
                if split[0] == "login" and len(split) == 3:
                    name = split[1]
                    sub_passw = split[2]
                    query = ("""SELECT login.pass, login.id, login.admin
                                FROM login
                                WHERE login.username='{}'""".format(name))
                    db_in.put(query)
                    result = db_out.get(True, 10)
                    if result:
                        pass_hash = result[0][0]
                        if pass_hash == sub_passw:
                            msg = "true|{}|{}".format(result[0][1], result[0][2])
                        else:
                            msg = "false"
                    else:
                        msg = "false"
                if split[0] == "signup" and len(split) == 4:
                    name = split[1]
                    hash = split[2]
                    salt = split[3]
                    query = """SELECT login.id
                               FROM login
                               WHERE login.username='{}'""".format(name)
                    db_in.put(query)
                    result = db_out.get(True, 10)
                    if result:
                        print("already exists")
                        msg = "false"
                    else:
                        query = """INSERT INTO login (username, pass, salt)
                                   VALUES ('{}', '{}', '{}')""".format(name, hash, salt)
                        db_in.put(query)
                        db_out.get()
                        query = "SELECT id FROM login WHERE username='{}'".format(name)
                        db_in.put(query)
                        result = db_out.get()
                        query = "INSERT INTO friends VALUES ('{0}', '{0}', 'active'," \
                                "datetime('now', 'localtime'))".format(result[0][0])
                        db_in.put(query)
                        db_out.get()
                        query = "INSERT INTO info (id) VALUES ('{}')".format(result[0][0])
                        db_in.put(query)
                        db_out.get()
                        msg = "true"

                if split[0] == "new" and len(split) == 5:
                    id = split[1]
                    act = split[2]
                    meta = split[3].replace('\n', '')
                    text = split[4].replace('\n', '')
                    query = """INSERT INTO feed (id, activity, text, date, metadata)
                               VALUES ('{}', '{}', '{}', datetime('now', 'localtime'), '{}')""".format(id, act, text,
                                                                                                       meta)

                    db_in.put(query)
                    db_out.get(True, 10)
                    print("added")
                if split[0] == "search" and len(split) == 3:
                    id = split[1]
                    name = split[2]
                    # get friends with similar names to term
                    query = """SELECT login.id, username FROM login
                               JOIN friends
                               ON (login.id=friends.id AND friends.friend_id='{1}')
                               OR (login.id=friends.friend_id AND friends.id='{1}')
                               WHERE username LIKE '%{0}%' AND state='active'
                               LIMIT 15""".format(name, id)
                    db_in.put(query)
                    friends = db_out.get(True, 10)
                    # get all with similar names to term
                    query = """SELECT login.id, username FROM login
                               WHERE username LIKE '%{0}%'
                               AND login.id != '{1}'
                               LIMIT 15""".format(name, id)
                    db_in.put(query)
                    not_friends = db_out.get(True, 10)
                    # get pending with similar names to term
                    query = """SELECT login.id, username FROM login
                               JOIN friends
                               ON (login.id=friends.id AND friends.friend_id='{1}')
                               OR (login.id=friends.friend_id AND friends.id='{1}')
                               WHERE username LIKE '%{0}%' AND state='waiting'
                               LIMIT 15""".format(name, id)
                    db_in.put(query)
                    pending = db_out.get(True, 10)
                    if len(friends) > 0:
                        not_friends = [x for x in not_friends if x not in friends]
                    if len(pending) > 0:
                        not_friends = [x for x in not_friends if x not in pending]

                    print(friends, pending, not_friends)

                    if friends or pending or not_friends:
                        msg = str([set(friends), set(pending), set(not_friends)][:15])
                    else:
                        msg = "[[], []]"

                if split[0] == "friends" and len(split) == 3:
                    id1 = split[1]
                    id2 = split[2]

                    query = "INSERT INTO friends VALUES ('{}', '{}', 'waiting', datetime('now'))".format(id1, id2)
                    db_in.put(query)
                    db_out.get()

                if split[0] == "pending" and len(split) == 2:
                    id = split[1]
                    query = """SELECT DISTINCT username, login.id  FROM login
                               JOIN friends
                               ON (login.id=friends.id)
                               WHERE friends.state = 'waiting'
                               AND friends.friend_id = '{0}'
                               LIMIT 15""".format(id)
                    db_in.put(query)
                    friends = db_out.get(True, 10)
                    if friends:
                        msg = str(friends)
                    else:
                        msg = "[]"

                if split[0] == "current" and len(split) == 2:
                    id = split[1]
                    query = """SELECT DISTINCT username, login.id FROM login
                               JOIN friends
                               ON (login.id=friends.id AND friends.friend_id='{0}')
                               OR (login.id=friends.friend_id AND friends.id='{0}')
                               WHERE friends.state = 'active'
                               AND login.id != '{0}'
                               LIMIT 15""".format(id)
                    db_in.put(query)
                    friends = db_out.get(True, 10)
                    if friends:
                        msg = str(friends)
                    else:
                        msg = "[]"

                if split[0] == "accept" and len(split) == 3:
                    id1 = split[1]
                    id2 = split[2]

                    query = """UPDATE friends
                               SET state='active'
                               WHERE friends.id = '{0}'
                               AND friends.friend_id = '{1}'""".format(id1, id2)

                    db_in.put(query)
                    db_out.get()

                if split[0] == "remove" and len(split) == 3:
                    id1 = split[1]
                    id2 = split[2]

                    query = """DELETE FROM friends
                               WHERE (friends.id = '{0}'
                               AND friends.friend_id = '{1}')
                               OR (friends.id = '{1}'
                               AND friends.friend_id = '{0}')""".format(id1, id2)

                    db_in.put(query)
                    db_out.get()

                if split[0] == "deletepost" and len(split) == 2:
                    feed_id = split[1]
                    query = """DELETE FROM feed
                            WHERE feed_id = '{}'""".format(feed_id)

                    db_in.put(query)
                    db_out.get()

                if split[0] == "deleteacc" and len(split) == 2:
                    acc_id = split[1]
                    query = """DELETE FROM login
                               WHERE id = '{}'""".format(acc_id)
                    db_in.put(query)
                    db_out.get()
                    query = """DELETE FROM feed
                               WHERE id = '{}'""".format(acc_id)
                    db_in.put(query)
                    db_out.get()
                    query = """DELETE FROM friends
                               WHERE id = '{0}' OR friend_id='{0}'""".format(acc_id)
                    db_in.put(query)
                    db_out.get()

                if split[0] == "activities" and len(split) == 3:
                    id = split[1]
                    timespan = int(split[2])
                    date = ""
                    if timespan > 0:
                        date = "date >= datetime('now' , '-{} day', 'localtime') AND".format(timespan)
                    query = """SELECT activity, metadata FROM feed
                            WHERE {}
                            id='{}' AND activity <> '' """.format(date, id)
                    db_in.put(query)
                    result = db_out.get()
                    if result:
                        msg = str(result)
                        print(result)
                    else:
                        msg = "[]"
                if split[0] == "info" and len(split) == 5:
                    id = split[1]
                    height = split[2]
                    weight = split[3]
                    age = split[4]
                    query = """UPDATE info
                               SET height='{}',weight='{}',age='{}'
                               WHERE id='{}'""".format(height, weight, age, id)
                    db_in.put(query)
                    db_out.get()

                if msg:
                    print("* sending:", msg)
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
