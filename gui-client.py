import select
import queue
import socket
import random
import hashlib
import string
import tkinter as tk

# the master server's IP, set as programmer
global SERVER
SERVER = ("Trolley", 54321)


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("FitBook")
        self.root.configure(bg="royalblue2")

        self.s = socket.socket()

        self.s.connect(SERVER)

        self.out_queue = queue.Queue()
        self.in_queue = queue.Queue()

        self.login_screen = Login(self)

        self.login_screen.draw()
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
                    print('received', reply)
                if not self.out_queue.empty():
                    msg = self.out_queue.get()
                    s.send(msg.encode())
            except Exception as e:
                print(e)
                break
        s.close()
        print("closed connection with", a)


class Login:
    def __init__(self, app):
        self.app = app
        self.title = tk.Label(text="FitBook", font=("trebuchet ms", 20, "bold"), bg="royalblue3",
                              fg="white")

        self.main_frame = tk.Frame(bg="royalblue2")

        self.mini_frame = tk.Frame(self.main_frame, bg="royalblue2")

        self.user_lab = tk.Label(self.mini_frame, text="Username", font=("trebuchet ms", 13), bg="royalblue2",
                                 fg="white")
        self.user_entry = tk.Entry(self.mini_frame, font=("trebuchet ms", 10))

        self.pass_lab = tk.Label(self.mini_frame, text="Password", font=("trebuchet ms", 13), bg="royalblue2",
                                 fg="white")
        self.pass_entry = tk.Entry(self.mini_frame, font=("trebuchet ms", 10), show="•")

        self.signup_button = tk.Button(self.main_frame, text="Sign up", bg="steelblue2", fg="white", bd=0, width=7,
                                       command=self.signup, font=("trebuchet ms", 12))
        self.login_button = tk.Button(self.main_frame, text="Log In", bg="steelblue2", fg="white", bd=0, width=7,
                                      command=self.login, font=("trebuchet ms", 12))

    def draw(self):
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

    def signup(self):
        name = self.user_entry.get()
        passw = self.pass_entry.get()
        if name and passw:
            salt = Login.salt_generator()
            passw_hash = hashlib.sha256(str(passw+salt).encode())

    def login(self):
        name = self.user_entry.get()
        passw = self.pass_entry.get()
        if name and passw:

            passw_hash = hashlib.sha256(passw+salt)


    @staticmethod
    def salt_generator(size=10):
        chars = string.ascii_uppercase + string.digits
        text = ''.join(random.choice(chars) for _ in range(size))
        return text

main = App()