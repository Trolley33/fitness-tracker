import hashlib
import queue
import random
import select
import socket
import string
import threading
import tkinter as tk
from collections import OrderedDict
from tkinter import messagebox

# the master server's IP, set as programmer
global SERVER

if socket.gethostname() == "Trolley":
    SERVER = ("Trolley", 54321)
else:
    SERVER = ("SCI-STUD-010", 54321)


class Post:
    def __init__(self, container, username, activity, date, text, user_id, feed_id):
        self.container = container
        self.page_f = container.page_frame

        self.frame = tk.Frame(self.page_f, bg="white", width=20, bd=2, relief="groove", padx=4)
        self.frame.columnconfigure(0, minsize=150)
        self.frame.columnconfigure(1, minsize=200)

        self.username = username
        self.activity = activity
        self.date = date
        self.text = text
        self.user_id = user_id
        self.feed_id = feed_id

        self.user_lab = tk.Label(self.frame, text=self.username, fg="royalblue2", bg="white",
                                 font=("trebuchet ms", 12, "bold"))
        self.activity_lab = tk.Label(self.frame, text=self.activity, fg="black", bg="white",
                                     font=("trebuchet ms", 12, "bold"))
        self.profile_button = tk.Button(self.frame, text="View Profile", bd=0, fg="royalblue3", bg="white",
                                        font=("trebuchet ms", 12, "bold"),
                                        command=lambda: self.container.load(self.user_id))
        self.date_lab = tk.Label(self.frame, text=self.date, fg="black", bg="white",
                                 font=("trebuchet ms", 10), width=18)
        self.text_lab = tk.Label(self.frame, text=self.text, fg="black", bg="white", wrap=480,
                                 font=("trebuchet ms", 10), justify="left")

    def draw(self, row):
        self.frame.grid(column=0, row=row, pady=(5, 5), sticky="WE")

        self.user_lab.grid(column=0, row=0, sticky="W", padx=5)
        self.activity_lab.grid(column=1, row=0, sticky="W", padx=5)
        if self.user_id > 0:
            self.profile_button.configure(command=lambda: self.container.load(self.user_id), text="View Profile", bd=0,
                                          fg="royalblue3", bg="white")
            self.profile_button.grid(column=4, row=0, sticky="E", padx=(40, 0))
        elif (self.user_id < 0 and abs(self.user_id) == self.container.app.id) or Login.admin:
            self.profile_button.configure(command=self.remove_post, text="Delete Post", bd=0,
                                          fg="red", bg="white")
            self.profile_button.grid(column=4, row=0, sticky="E", padx=(40, 0))

        self.text_lab.grid(column=0, row=1, columnspan=5, sticky="W", padx=(10, 10))
        self.date_lab.grid(column=4, row=2, sticky="E")

    def remove_post(self):
        self.container.app.out_queue.put("deletepost|{}".format(self.feed_id))
        self.container.load(self.container.current_profile)

    def delete(self):
        self.frame.destroy()

        self.user_lab.destroy()
        self.activity_lab.destroy()
        self.profile_button.destroy()
        self.text_lab.destroy()
        self.date_lab.destroy()
        del self


class PostDialog:
    def __init__(self, container):
        self.container = container

        self.top = tk.Toplevel(self.container.app.root)
        self.top.title("Share Your Experiences!")
        self.top.geometry("640x208")
        self.top.configure(bg="royalblue2")
        self.top.columnconfigure(0, minsize=320)

        self.selected_opt = tk.StringVar(self.top)
        self.selected_opt.set("Nothing")
        self.options = OrderedDict([["Nothing", ""],
                                    ["Running", "run"],
                                    ["Swimming", "swim"],
                                    ["Weightlifting", "lift"],
                                    ["Cycling", "cycle"],
                                    ["Coding", "code"]])

        self.act_lab = tk.Label(self.top, text="What did you do today?", font=("trebuchet ms", 12, "bold"),
                                fg="white", bg="royalblue2")
        self.meta_lab = tk.Label(self.top, text="No activity selected.", font=("trebuchet ms", 12, "bold"),
                                 fg="white", bg="royalblue2")
        self.text_lab = tk.Label(self.top, text="How was it?", font=("trebuchet ms", 12, "bold"),
                                 fg="white", bg="royalblue2")

        self.menu = tk.OptionMenu(self.top, self.selected_opt, *self.options.keys())

        self.menu.configure(bd=0, bg="royalblue2", fg="white", width=10, relief="flat",
                            activeforeground="white", activebackground="royalblue2")
        self.menu["menu"].config(bd=0, bg="royalblue2", fg="white",
                                 activeforeground="white", relief="flat")

        self.meta = tk.Entry(self.top, font=("trebuchet ms", 11), width=10)
        self.text = tk.Text(self.top, width=35, height=3, wrap='word', font=("trebuchet ms", 11))

        self.selected_opt.trace('w', self.update_text)

        self.scroll_bar = tk.Scrollbar(self.top, command=self.text.yview)
        self.text['yscrollcommand'] = self.scroll_bar.set
        self.submit_but = tk.Button(self.top, text="Submit", command=self.validate, bg="steelblue2", fg="white",
                                    bd=0, width=7, font=("trebuchet ms", 12))

        self.draw()

    def draw(self):
        self.act_lab.grid(column=0, row=0, pady=(12, 0), padx=5, sticky="E")
        self.meta_lab.grid(column=0, row=1, pady=(12, 0), padx=5, sticky="E")
        self.text_lab.grid(column=0, row=2, pady=(12, 0), padx=5, sticky="E")

        self.menu.grid(column=1, row=0, sticky="W")
        self.meta.grid(column=1, row=1, sticky="W")
        self.text.grid(column=1, row=2, sticky="W")

        self.scroll_bar.grid(column=2, row=2, sticky="NEWS")

        self.submit_but.grid(column=1, row=3, columnspan=3, sticky="E", padx=16, pady=(5, 0))

    def validate(self):
        activity = self.selected_opt.get()
        meta = self.meta.get()
        post = self.text.get('1.0', 'end')

        if (activity != "Nothing" and meta.isdigit()) or (activity == "Nothing" and meta == ''):
            self.container.submit(self.options[activity], meta, post)
            self.top.destroy()
            del self
        else:
            App.popup("warning", "Drop-down and amount done do not match up.")

    def update_text(self, *args):
        act = self.selected_opt.get()
        x = ""
        m = ""
        if act in self.options.keys():
            x = self.options[act]
        if x == "run" or x == "cycle":
            m = "kilometres"
        elif x == "swim":
            m = "metres"
        elif x == "lift":
            m = "kilograms"
        elif x == "code":
            m = "lines"
        if x and m:
            self.meta_lab.configure(text="How many {} did you {}?".format(m, x))
        else:
            self.meta_lab.configure(text="No activity selected.")


class SearchDialog:
    def __init__(self, container):
        self.container = container

        self.top = tk.Toplevel(self.container.app.root)
        self.top.title("Search for Friends!")

        self.search_bar = tk.Entry(self.top)
        self.search_but = tk.Button(self.top, text="Search", command=self.search)

        self.results = []
        self.results_stuff = []

        self.draw()

    def draw(self):
        self.search_bar.grid(column=0, row=0, sticky="NESW")
        self.search_but.grid(column=1, row=0, sticky="W")

    def search(self):
        term = self.search_bar.get()
        self.clear()
        if term:
            self.container.app.out_queue.put("search|{}|{}".format(self.container.app.id, term))
            try:
                self.results = eval(self.container.app.in_queue.get(True, 4))
            except queue.Empty:
                App.popup("warning", "No response from server, are you connected to the internet?")
            q = 1
            for i, friend in enumerate(self.results[0]):
                self.results_stuff.append(SearchFrame(self, i + 1, friend[1], friend[0], 1))
                self.results_stuff[-1].draw()
                q += 1
            for i, user in enumerate(self.results[1]):
                self.results_stuff.append(SearchFrame(self, q + i + 1, user[1], user[0], 0))
                self.results_stuff[-1].draw()
            print([x.username for x in self.results_stuff])

    def clear(self):
        for p in self.results_stuff:
            p.destroy()
        self.results_stuff = []


class SearchFrame:
    def __init__(self, container, row, username, id, is_friend):
        self.container = container

        self.row = row
        self.username = username
        self.id = id
        self.is_friend = is_friend

        if is_friend:
            cmd = lambda: self.container.container.load(self.id)
            text = "View profile"
        else:
            cmd = self.add_friend
            text = "Add friend"

        self.frame = tk.Frame(self.container.top, bg="white")
        self.frame.columnconfigure(0, minsize=100)
        self.frame.columnconfigure(1, minsize=100)

        self.user_lab = tk.Label(self.frame, text=self.username, fg="royalblue2", bg="white",
                                 font=("trebuchet ms", 12, "bold"))

        self.profile_button = tk.Button(self.frame, text=text, bd=0, fg="royalblue3", bg="white",
                                        font=("trebuchet ms", 12, "bold"),
                                        command=cmd)

    def add_friend(self):
        self.container.container.app.out_queue.put("friends|{}|{}".format(self.container.container.app.id, self.id))
        self.profile_button.configure(command=lambda: App.popup("info", "Already sent a request!"))

    def draw(self):
        self.frame.grid(column=0, row=self.row, pady=(5, 5), sticky="NSWE", columnspan=2)

        self.user_lab.grid(column=0, row=0, sticky="W", padx=5)

        self.profile_button.grid(column=4, row=0, sticky="E", padx=(40, 0))

    def destroy(self):
        self.frame.destroy()

        self.user_lab.destroy()
        self.profile_button.destroy()

        del self


class FriendDialog:
    def __init__(self, container):
        self.container = container

        self.top = tk.Toplevel(self.container.app.root, bg="gray90")
        self.top.title("Add New Friends!")
        self.top.columnconfigure(0, minsize=240)
        self.top.columnconfigure(1, minsize=240)

        self.title_l = tk.Label(self.top, text="Requests", fg="white", bg="royalblue2",
                                font=("trebuchet ms", 14, "bold"))
        self.title_r = tk.Label(self.top, text="Friends", fg="white", bg="royalblue2",
                                font=("trebuchet ms", 14, "bold"))

        self.left = tk.Frame(self.top, bg="gray90")
        self.right = tk.Frame(self.top, bg="gray90")

        self.pending = []
        self.current = []

        self.get_stuff()
        self.draw()

    def draw(self):
        self.title_l.grid(column=0, row=0, sticky="NEWS")
        self.title_r.grid(column=1, row=0, sticky="NEWS")

        self.left.grid(column=0, row=1, padx=10)
        self.right.grid(column=1, row=1, padx=10)

    def get_stuff(self):
        self.container.app.out_queue.put("pending|{}".format(self.container.app.id))
        self.clear()
        print(self.pending, self.current)
        pending, current = [], []
        try:
            pending = eval(self.container.app.in_queue.get(True, 4))
        except queue.Empty:
            App.popup("warning", "No response from server, are you connected to the internet?")

        self.container.app.out_queue.put("current|{}".format(self.container.app.id))
        try:
            current = eval(self.container.app.in_queue.get(True, 4))
        except queue.Empty:
            App.popup("warning", "No response from server, are you connected to the internet?")

        for i, p in enumerate(pending):
            u = p[0]
            id = p[1]
            self.pending.append(Friend(self, i, u, id, 0, self.left))
        for i, p in enumerate(current):
            u = p[0]
            id = p[1]
            self.current.append(Friend(self, i, u, id, 1, self.right))
        if not self.pending:
            self.pending.append(Friend(self, 0, "Nothing here!", -1, -1, self.left))

        if not self.current:
            self.current.append(Friend(self, 0, "Nothing here!", -1, -1, self.right))

        for i, p in enumerate(self.pending):
            p.draw()

        for i, c in enumerate(self.current):
            c.draw()

    def clear(self):
        for p in self.pending + self.current:
            p.destroy()
        self.pending = []
        self.current = []


class Friend:
    def __init__(self, container, row, username, id, is_friend, frame):
        self.container = container

        self.row = row
        self.username = username
        self.id = id
        self.is_friend = is_friend

        self.frame = tk.Frame(frame, bg="white", bd=2, relief="groove")
        self.frame.columnconfigure(0, minsize=120)
        self.frame.columnconfigure(1, minsize=120)

        if is_friend:
            cmd = self.remove
            text = "Remove Friend"
        else:
            cmd = self.accept
            text = "Accept Request"

        self.button_draw = True

        if not id or is_friend == -1:
            self.button_draw = False
            self.frame.columnconfigure(0, minsize=0)
            self.frame.columnconfigure(1, minsize=0)

        self.user_lab = tk.Label(self.frame, text=self.username, fg="royalblue2", bg="white",
                                 font=("trebuchet ms", 12, "bold"))

        self.profile_button = tk.Button(self.frame, text=text, bd=0, fg="royalblue3", bg="white",
                                        font=("trebuchet ms", 12, "bold"),
                                        command=cmd)

    def draw(self):
        self.frame.grid(column=0, row=self.row, pady=(5, 5), sticky="NSWE", columnspan=2)

        self.user_lab.grid(column=0, row=0, sticky="W")
        if self.button_draw:
            self.profile_button.grid(column=4, row=0, sticky="E")

    def remove(self):
        self.container.container.app.out_queue.put("remove|{}|{}".format(self.id, self.container.container.app.id))
        self.container.container.app.root.after(1000, self.container.get_stuff)

    def accept(self):
        self.container.container.app.out_queue.put("accept|{}|{}".format(self.id, self.container.container.app.id))
        self.container.container.app.root.after(1000, self.container.get_stuff)

    def destroy(self):
        self.frame.destroy()

        self.user_lab.destroy()
        self.profile_button.destroy()

        del self


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("FitBook")
        self.root.configure(bg="royalblue2")
        self.root.resizable(width=False, height=False)

        self.id = -1
        self.username = ""

        self.s = socket.socket()

        try:
            self.s.connect(SERVER)
        except Exception as e:
            self.root.after(3500, self.root.destroy)
            App.popup("error", "No connection could be established, app will close.")
            del self
            exit()
        
        self.out_queue = queue.Queue()
        self.in_queue = queue.Queue()

        self.login_screen = Login(self)
        self.main = Main(self)

        self.login_screen.draw()

        t = threading.Thread(target=self.handler, args=(self.s, SERVER))
        t.setDaemon(True)
        t.start()

        self.root.mainloop()

    def handler(self, s, a):
        while 1:
            try:
                ready = select.select([s], [], [], 0.25)
                if ready[0]:
                    reply = s.recv(1024)
                    reply = reply.decode()
                    if not reply:
                        break
                    print('* received', reply)
                    self.in_queue.put(reply)
                if not self.out_queue.empty():
                    msg = self.out_queue.get()
                    s.send(msg.encode())
                    print("* sent:", msg)
            except Exception as e:
                print(e)
                break
        s.close()
        print("closed connection with", a)

    @staticmethod
    def popup(box, msg):
        if box == "info":
            messagebox.showinfo("Information", msg)
        if box == "warning":
            messagebox.showwarning("Warning", msg)
        if box == "error":
            messagebox.showerror("Error", msg)


class Login:
    admin = False

    def __init__(self, app):
        self.app = app
        self.title = tk.Label(text="FitBook", font=("trebuchet ms", 20, "bold"), bg="royalblue3",
                              fg="white")

        self.main_frame = tk.Frame(bg="royalblue2")

        self.mini_frame = tk.Frame(self.main_frame, bg="royalblue2")

        self.user_lab = tk.Label(self.mini_frame, text="Username:", font=("trebuchet ms", 13), bg="royalblue2",
                                 fg="white")
        self.user_entry = tk.Entry(self.mini_frame, font=("trebuchet ms", 10))

        self.pass_lab = tk.Label(self.mini_frame, text="Password:", font=("trebuchet ms", 13), bg="royalblue2",
                                 fg="white")
        self.pass_entry = tk.Entry(self.mini_frame, font=("trebuchet ms", 10), show="•")

        self.signup_button = tk.Button(self.main_frame, text="Sign up", bg="steelblue2", fg="white", bd=0, width=7,
                                       command=self.signup, font=("trebuchet ms", 12))
        self.login_button = tk.Button(self.main_frame, text="Log In", bg="steelblue2", fg="white", bd=0, width=7,
                                      command=self.login, font=("trebuchet ms", 12))

    def draw(self):
        self.app.root.configure(bg="royalblue2")

        self.title.grid(column=0, row=0, sticky="NEWS")

        self.main_frame.grid(column=0, row=1, padx=20, pady=(4, 8))

        self.mini_frame.grid(column=0, row=1, columnspan=2)
        # in frame
        self.user_lab.grid(column=0, row=0, padx=(0, 4))
        self.user_entry.grid(column=1, row=0)
        self.pass_lab.grid(column=0, row=1, padx=(0, 4))
        self.pass_entry.grid(column=1, row=1)

        self.signup_button.grid(column=0, row=2, sticky="E", padx=5, pady=(5, 0))
        self.login_button.grid(column=1, row=2, sticky="W", padx=5, pady=(5, 0))

    def undraw(self):
        self.title.grid_forget()

        self.main_frame.grid_forget()

        self.mini_frame.grid_forget()
        # in frame
        self.user_lab.grid_forget()
        self.user_entry.grid_forget()
        self.pass_lab.grid_forget()
        self.pass_entry.grid_forget()

        self.signup_button.grid_forget()
        self.login_button.grid_forget()

        self.user_entry.delete(0, 'end')
        self.pass_entry.delete(0, 'end')

    def signup(self):
        name = self.user_entry.get()
        passw = self.pass_entry.get()
        if name and passw:
            salt = Login.salt_generator()
            passw_hash = hashlib.sha256(str(passw + salt).encode()).hexdigest()
            self.app.out_queue.put("signup|{}|{}|{}".format(name, passw_hash, salt))
            success = self.app.in_queue.get(True, 10)
            if success == "true":
                App.popup("info", "Successfully signed up.")
            elif success == "false":
                App.popup("info", "An account with that username already exists.")

    def login(self):
        name = self.user_entry.get()
        passw = self.pass_entry.get()
        if name and passw:
            try:
                self.app.out_queue.put("request|salt|{}".format(name))
                salt = self.app.in_queue.get(True, 5)
                hash = hashlib.sha256(str(passw + salt).encode()).hexdigest()
                self.app.out_queue.put("login|{}|{}".format(name, hash))
                valid = self.app.in_queue.get(True, 5).split("|")
                if valid[0] == "true":
                    self.app.id = int(valid[1])
                    Login.admin = bool(int(valid[2]))
                    self.app.username = name
                    # do stuff
                    self.undraw()
                    self.app.main.draw()
                elif valid[0] == "false":
                    App.popup("info", "Invalid login credentials.")
                    self.user_entry.delete(0, 'end')
                    self.pass_entry.delete(0, 'end')

            except queue.Empty as e:
                App.popup("warning", "Could not establish a connection with server.")

            except Exception as e:
                print(e)

    @staticmethod
    def salt_generator(size=10):
        chars = string.ascii_uppercase + string.digits
        text = ''.join(random.choice(chars) for _ in range(size))
        return text


class Main:
    def __init__(self, app):
        self.app = app

        self.page = 1
        self.current_profile = 0

        self.top_bar = tk.Frame(bg="royalblue3")

        self.user_but = tk.Button(self.top_bar, text="Oi!", bg="royalblue2", fg="white", width=6,
                                  font=("trebuchet ms", 12), padx=5, bd=0, command=self.load)

        self.post_but = tk.Button(self.top_bar, text="Post Something", bg="royalblue2", fg="white", bd=0, width=14,
                                  command=self.post, font=("trebuchet ms", 12))

        self.search_but = tk.Button(self.top_bar, text="Search", bg="royalblue2", fg="white", bd=0,
                                    width=8, command=self.search, font=("trebuchet ms", 12))

        self.friends_but = tk.Button(self.top_bar, text="Friends", bg="royalblue2", fg="white", bd=0,
                                     width=8, command=self.friends, font=("trebuchet ms", 12))

        self.refresh_but = tk.Button(self.top_bar, text="↻", bg="royalblue2", fg="white", bd=0,
                                     width=3, command=lambda: self.load(self.current_profile),
                                     font=("trebuchet ms", 12))

        self.logout_but = tk.Button(self.top_bar, text="Log Out", bg="royalblue2", fg="white", bd=0, width=7,
                                    command=self.logout, font=("trebuchet ms", 12))

        self.page_frame = tk.Frame(bg="gray90")

        self.back_but = tk.Button(text="<--", bg="gray90", fg="royalblue2", bd=0, width=4,
                                  command=self.back, font=("trebuchet ms", 15))
        self.next_but = tk.Button(text="-->", bg="gray90", fg="royalblue2", bd=0, width=4,
                                  command=self.next, font=("trebuchet ms", 15))

        self.posts = []

    def post(self):
        PostDialog(self)

    def search(self):
        SearchDialog(self)

    def friends(self):
        FriendDialog(self)

    def back(self):
        if self.page > 1:
            self.page -= 1
            self.load(self.current_profile)

    def next(self):
        if not isinstance(self.posts[0], tk.Label):
            self.page += 1
            self.load(self.current_profile)

    def submit(self, activity, meta, text):
        self.app.out_queue.put("new|{}|{}|{}|{}".format(self.app.id, activity, meta, text))
        self.app.root.after(1000, self.load)

    def load(self, id=0):
        self.clear_posts()
        options = {
            "run": "Ran {} kilometres.",
            "swim": "Swam {} metres.",
            "lift": "Lifted {} kilograms.",
            "cycle": "Cycled {} kilometres.",
            "code": "Coded {} lines."
        }
        # load feed
        if id == 0:
            if self.current_profile != 0:
                self.page = 1
            self.app.out_queue.put("feed|{}|{}".format(self.app.id, self.page * 5))
            self.current_profile = 0
            feed = self.app.in_queue.get(True, 2)
            feed = eval(feed)
            for i, p in enumerate(feed):
                u = p[0]
                a = p[1]
                m = p[2]
                d = p[3]
                t = p[4]
                id = p[5]
                f_id = p[6]
                if a in options.keys():
                    a = options[a].format(m)
                else:
                    a = ""
                self.posts.append(Post(container=self, username=u, activity=a, date=d, text=t, user_id=id, feed_id=f_id))
                self.posts[-1].draw(i)
            self.user_but.configure(text="Profile", command=lambda: self.load(self.app.id))
        # load other page
        else:
            # query server for profile
            if self.current_profile != id:
                self.page = 1
            self.app.out_queue.put("profile|{}|{}|{}".format(id, self.app.id, self.page * 5))
            self.current_profile = id
            prof = self.app.in_queue.get(True, 2)
            prof = eval(prof)
            for i, p in enumerate(prof):
                u = p[0]
                a = p[1]
                m = p[2]
                d = p[3]
                t = p[4]
                f_id = p[5]
                if a in options.keys():
                    a = options[a].format(m)
                else:
                    a = ""
                self.posts.append(Post(container=self, username=u, activity=a, date=d, text=t, user_id=-id, feed_id=f_id))
                self.posts[-1].draw(i)
            self.user_but.configure(text="Feed", command=self.load)
        if len(self.posts) == 0:
            self.posts.append(tk.Label(self.page_frame, text="No posts here!", fg="gray65", bg="gray95",
                                       font=("trebuchet ms", 12, "bold"), bd=2, relief="groove", padx=40, pady=20))
            self.posts[0].grid(row=1, pady=10)

    def logout(self):
        self.app.id = -1
        self.app.username = ""

        self.undraw()
        self.app.login_screen.draw()

    def draw(self):
        self.app.root.configure(bg="gray90")
        self.top_bar.grid(column=0, row=0, sticky="NEWS", columnspan=2)

        self.user_but.grid(column=0, row=0, sticky="NSW", padx=(0, 5))
        self.user_but.configure(text="Profile")
        self.post_but.grid(column=3, row=0, sticky="NS", padx=(5, 5))
        self.search_but.grid(column=2, row=0, sticky="NS", padx=(5, 5))
        self.friends_but.grid(column=4, row=0, sticky="NS", padx=(5, 0))
        self.refresh_but.grid(column=99, row=0, sticky="NS", padx=(240, 5))
        self.logout_but.grid(column=100, row=0, sticky="NSE", padx=(5, 0))

        self.page_frame.grid(column=0, row=1, columnspan=2)

        self.back_but.grid(column=0, row=2, sticky="W")
        self.next_but.grid(column=1, row=2, sticky="E")

        self.app.root.title("{}'s FitBook".format(self.app.username))

        self.load()

    def undraw(self):
        self.top_bar.grid_forget()
        self.clear_posts()
        self.page_frame.grid_forget()

        self.back_but.grid_forget()
        self.next_but.grid_forget()

        self.app.root.title("FitBook")

    def clear_posts(self):
        for post in self.posts:
            if isinstance(post, Post):
                post.delete()
            else:
                post.destroy()
        self.posts = []


main = App()
