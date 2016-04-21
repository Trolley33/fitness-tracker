import select
import queue
import socket
import random
import threading
import hashlib
import string
import tkinter as tk
from tkinter import messagebox

# the master server's IP, set as programmer
global SERVER
SERVER = ("Trolley", 54321)


class Post:
    def __init__(self, container, username, activity, date, text, user_id):
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
        if self.user_id != -1:
            self.profile_button.grid(column=4, row=0, sticky="E", padx=(40, 0))

        self.text_lab.grid(column=0, row=1, columnspan=5, sticky="W", padx=(10, 10))
        self.date_lab.grid(column=4, row=2, sticky="E")

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
        self.selected_opt = tk.StringVar(self.top)
        self.selected_opt.set("Nothing")
        self.options = {"Nothing": "",
                        "Running": "run",
                        "Swimming": "swim",
                        "Weightlifting": "lift"}

        self.act_lab = tk.Label(self.top, text="What did you do today?", font=("trebuchet ms", 12, "bold"))
        self.meta_lab = tk.Label(self.top, text="How much did you do?", font=("trebuchet ms", 12, "bold"))
        self.text_lab = tk.Label(self.top, text="How was it?", font=("trebuchet ms", 12, "bold"))

        self.menu = tk.OptionMenu(self.top, self.selected_opt, *sorted(self.options.keys()))
        self.meta = tk.Entry(self.top, font=("trebuchet ms", 11), width=10)
        self.text = tk.Text(self.top, width=35, height=3, wrap='word', font=("trebuchet ms", 11))

        self.scroll_bar = tk.Scrollbar(self.top, command=self.text.yview)
        self.text['yscrollcommand'] = self.scroll_bar.set
        self.submit_but = tk.Button(self.top, text="Submit", command=self.validate)

        self.draw()

    def draw(self):
        self.act_lab.grid(column=0, row=0, pady=(12, 0))
        self.meta_lab.grid(column=0, row=1, pady=(12, 0))
        self.text_lab.grid(column=0, row=2, pady=(12, 0))

        self.menu.grid(column=1, row=0, sticky="W")
        self.meta.grid(column=1, row=1, sticky="W")
        self.text.grid(column=1, row=2, sticky="W")

        self.scroll_bar.grid(column=2, row=2, sticky="NEWS")

        self.submit_but.grid(column=1, row=3, columnspan=3, sticky="E", padx=16)

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


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("FitBook")
        self.root.configure(bg="royalblue2")
        self.root.resizable(width=False, height=False)

        self.id = -1
        self.username = ""

        self.s = socket.socket()

        self.s.connect(SERVER)

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
                ready = select.select([s], [], [], 0.5)
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
            passw_hash = hashlib.sha256(str(passw+salt).encode()).hexdigest()
            self.app.out_queue.put("signup|{}|{}|{}".format(name, passw_hash, salt))
            success = self.app.in_queue.get(True, 10)
            print(success)

    def login(self):
        name = self.user_entry.get()
        passw = self.pass_entry.get()
        if name and passw:
            try:
                self.app.out_queue.put("request|salt|{}".format(name))
                salt = self.app.in_queue.get(True, 5)
                hash = hashlib.sha256(str(passw+salt).encode()).hexdigest()
                self.app.out_queue.put("login|{}|{}".format(name, hash))
                valid = self.app.in_queue.get(True, 5).split("|")
                if valid[0] == "true":
                    self.app.id = valid[1]
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
        self.current_profile = -1

        self.top_bar = tk.Frame(bg="royalblue3")

        self.user_but = tk.Button(self.top_bar, text="Oi!", bg="royalblue2", fg="white",
                                  font=("trebuchet ms", 12), padx=5, bd=0, command=self.load)

        self.post_but = tk.Button(self.top_bar, text="Post Something", bg="royalblue2", fg="white", bd=0, width=14,
                                  command=self.post, font=("trebuchet ms", 12))

        self.logout_but = tk.Button(self.top_bar, text="Log Out", bg="royalblue2", fg="white", bd=0, width=7,
                                    command=self.logout, font=("trebuchet ms", 12))

        self.page_frame = tk.Frame(bg="gray90")

        self.back_but = tk.Button(text="<--", bg="gray90", fg="royalblue2", bd=0, width=4,
                                  command=self.back, font=("trebuchet ms", 15))
        self.next_but = tk.Button(text="-->", bg="gray90", fg="royalblue2", bd=0, width=4,
                                  command=self.next, font=("trebuchet ms", 15))

        self.posts = []

    def post(self):
        t = PostDialog(self)

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
        self.app.root.after(4000, self.load)

    def load(self, id=-1):
        self.clear_posts()
        options = {
            "run": "Ran {} kilometres.",
            "swim": "Swam {} metres.",
            "lift": "Lifted {} kilograms."
        }
        if id == -1:
            if self.current_profile != -1:
                self.page = 1
            self.app.out_queue.put("feed|{}|{}".format(self.app.id, self.page*5))
            self.current_profile = -1
            feed = self.app.in_queue.get(True, 2)
            feed = eval(feed)
            for i, p in enumerate(feed):
                u = p[0]
                a = p[1]
                m = p[2]
                d = p[3]
                t = p[4]
                id = p[5]
                if a in options.keys():
                    a = options[a].format(m)
                self.posts.append(Post(container=self, username=u, activity=a, date=d, text=t, user_id=id))
                self.posts[-1].draw(i)
        else:
            # query server for profile
            if self.current_profile != id:
                self.page = 1
            self.app.out_queue.put("profile|{}|{}|{}".format(id, self.app.id, self.page*5))
            self.current_profile = id
            prof = self.app.in_queue.get(True, 2)
            prof = eval(prof)
            for i, p in enumerate(prof):
                u = p[0]
                a = p[1]
                m = p[2]
                d = p[3]
                t = p[4]
                if a in options.keys():
                    a = options[a].format(m)
                self.posts.append(Post(container=self, username=u, activity=a, date=d, text=t, user_id=-1))
                self.posts[-1].draw(i)
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

        self.user_but.grid(column=0, row=0, sticky="NSW", padx=(0, 120))
        self.user_but.configure(text=self.app.username)
        self.post_but.grid(column=50, row=0, sticky="NS", padx=(60, 60))
        self.logout_but.grid(column=100, row=0, sticky="NSE", padx=(120, 0))

        self.page_frame.grid(column=0, row=1, columnspan=2)

        self.back_but.grid(column=0, row=2, sticky="W")
        self.next_but.grid(column=1, row=2, sticky="E")

        self.load()

    def undraw(self):
        self.top_bar.grid_forget()
        self.clear_posts()
        self.page_frame.grid_forget()

        self.back_but.grid_forget()
        self.next_but.grid_forget()

    def clear_posts(self):
        for post in self.posts:
            if isinstance(post, Post):
                post.delete()
            else:
                post.destroy()
        self.posts = []

main = App()
