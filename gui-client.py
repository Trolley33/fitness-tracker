import hashlib
import operator
import queue
import random
import select
import socket
import string
import threading
import tkinter as tk
import webbrowser
from collections import OrderedDict
from tkinter import messagebox

# the master server's IP, set as programmer
global SERVER
# if my PC, automatically connect to self
if socket.gethostname() == "Trolley":
    SERVER = ("Trolley", 54321)
# otherwise connect to supplied address
else:
    SERVER = ("ICT-F16-022", 54321)


# Post container
# -----------------------------------------------
# | <Username> <Activity> <Amount> View Profile |
# | <Body of text>                              |
# |                                      <Date> |
# -----------------------------------------------
class Post:
    def __init__(self, container, username, activity, date, text, user_id, feed_id):
        # Initialise class variables.
        self.container = container
        self.page_f = container.page_frame #
        self.username = username
        self.activity = activity
        self.date = date
        self.text = text
        self.user_id = user_id
        self.feed_id = feed_id

        # Create main frame to contain other content.
        self.frame = tk.Frame(self.page_f, bg="white", width=20, bd=2, relief="groove", padx=4)
        # Make post a set width
        self.frame.columnconfigure(0, minsize=150)
        self.frame.columnconfigure(1, minsize=200)

        # Set up all labels.
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
        """Draw current post at row."""
        self.frame.grid(column=0, row=row, pady=(5, 5), sticky="WE")
        self.user_lab.grid(column=0, row=0, sticky="W", padx=5)
        self.activity_lab.grid(column=1, row=0, sticky="W", padx=5)
        # If post is on main feed draw regularly.
        if self.user_id > 0:
            self.profile_button.configure(command=lambda: self.container.load(self.user_id), text="View Profile", bd=0,
                                          fg="royalblue3", bg="white")
            self.profile_button.grid(column=4, row=0, sticky="E", padx=(40, 0))
        # If user is on a profile, and owns profile, or is admin.
        elif (self.user_id < 0 and abs(self.user_id) == self.container.app.id) or Login.admin:
            self.profile_button.configure(command=self.remove_post, text="Delete Post", bd=0,
                                          fg="firebrick3", bg="white")
            self.profile_button.grid(column=4, row=0, sticky="E", padx=(40, 0))

        self.text_lab.grid(column=0, row=1, columnspan=5, sticky="W", padx=(10, 10))
        self.date_lab.grid(column=4, row=2, sticky="E")

    def remove_post(self):
        """Remove post from server database."""
        # If admin or user requests removal of a post, send request and refresh page.
        self.container.app.out_queue.put("deletepost|{}".format(self.feed_id))
        self.container.load(self.container.current_profile)

    # Whenever new posts are loaded completely remove widgets from memory as they most likely won't be needed any more.
    def delete(self):
        """Remove post from memory and feed."""
        # Destroy all tkinter widgets.
        self.frame.destroy()
        self.user_lab.destroy()
        self.activity_lab.destroy()
        self.profile_button.destroy()
        self.text_lab.destroy()
        self.date_lab.destroy()
        # Delete this object from memory.
        del self


# Post Popup Dialog
# What did you do: <dropdown>
# How much did you do <textentry>
# How was it <textarea>
# <Submit>
class PostDialog:
    def __init__(self, container):
        # Initialise place where dialog is initiated.
        self.container = container
        # Create popup window and set parameters.
        self.top = tk.Toplevel(self.container.app.root)
        self.top.title("Share Your Experiences!")
        self.top.geometry("640x208")
        self.top.configure(bg="royalblue2")
        self.top.columnconfigure(0, minsize=320)
        # Set up variables for dropdown box.
        self.selected_opt = tk.StringVar(self.top)
        self.selected_opt.set("Nothing")
        # Link display words to keywords.
        self.options = OrderedDict([["Nothing", ""],
                                    ["Running", "run"],
                                    ["Swimming", "swim"],
                                    ["Weightlifting", "lift"],
                                    ["Cycling", "cycle"],
                                    ["Push ups", "push"]])
        # Question labels.
        self.act_lab = tk.Label(self.top, text="What did you do today?", font=("trebuchet ms", 12, "bold"),
                                fg="white", bg="royalblue2")
        self.meta_lab = tk.Label(self.top, text="No activity selected.", font=("trebuchet ms", 12, "bold"),
                                 fg="white", bg="royalblue2")
        self.text_lab = tk.Label(self.top, text="How was it?", font=("trebuchet ms", 12, "bold"),
                                 fg="white", bg="royalblue2")
        # Dropdown box.
        self.menu = tk.OptionMenu(self.top, self.selected_opt, *self.options.keys())
        # Fixing aesthetics.
        self.menu.configure(bd=0, bg="royalblue2", fg="white", relief="flat",
                            activeforeground="white", activebackground="royalblue2")
        self.menu["menu"].config(bd=0, bg="royalblue2", fg="white",
                                 activeforeground="white", relief="flat")
        # Entry boxes.
        self.meta = tk.Entry(self.top, font=("trebuchet ms", 11), width=10)
        self.text = tk.Text(self.top, width=35, height=3, wrap='word', font=("trebuchet ms", 11))
        # When dropdown is changed, update question text.
        self.selected_opt.trace('w', self.update_text)
        # Add scrollbar to text box.
        self.scroll_bar = tk.Scrollbar(self.top, command=self.text.yview)
        self.text['yscrollcommand'] = self.scroll_bar.set
        # Submit post to server.
        self.submit_but = tk.Button(self.top, text="Submit", command=self.validate, bg="steelblue2", fg="white",
                                    bd=0, width=7, font=("trebuchet ms", 12))
        self.draw()

    def draw(self):
        """Add all widgets to window."""
        self.act_lab.grid(column=0, row=0, pady=(12, 0), padx=5, sticky="E")
        self.meta_lab.grid(column=0, row=1, pady=(12, 0), padx=5, sticky="E")
        self.text_lab.grid(column=0, row=2, pady=(12, 0), padx=5, sticky="E")

        self.menu.grid(column=1, row=0, sticky="W")
        self.meta.grid(column=1, row=1, sticky="W")
        self.text.grid(column=1, row=2, sticky="W")

        self.scroll_bar.grid(column=2, row=2, sticky="NEWS")

        self.submit_but.grid(column=1, row=3, columnspan=3, sticky="E", padx=16, pady=(5, 0))

    def validate(self):
        """Check user entry before submitting."""
        activity = self.selected_opt.get()
        meta = self.meta.get()
        post = self.text.get('1.0', 'end')
        # If either: activity is something, and amount done is a number; or activity is not set, and no data is entered
        # but something has to be in the post box.
        if (activity != "Nothing" and meta.isdigit()) or (activity == "Nothing" and meta == '' and post != ''):
            self.container.submit(self.options[activity], meta, post)
            # After submitting post, close popup window.
            self.top.destroy()
            del self
        # If entered options are invalid alert user.
        else:
            App.popup("warning", "Drop-down and amount done do not match up.")

    def update_text(self, *args):
        """Change question based on context of dropdown."""
        act = self.selected_opt.get()
        # x = amount, m = activity done.
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
        elif x == "push":
            x = "do"
            m = "push-ups"
        if x and m:
            self.meta_lab.configure(text="How many {} did you {}?".format(m, x))
        else:
            self.meta_lab.configure(text="No activity selected.")

# <Entry box> [Search]
# <friend1> [view profile]
# <friend2> [view profile]
# <non-friend> [send friend request]
class SearchDialog:
    def __init__(self, container):
        # Initialise place where dialog is initiated.
        self.container = container
        # Create popup window and change title of window.
        self.top = tk.Toplevel(self.container.app.root)
        self.top.title("Search for Friends!")
        # Create search entry box and button.
        self.search_bar = tk.Entry(self.top)
        self.search_but = tk.Button(self.top, text="Search", command=self.search)
        # Initiliase where the search info and GUI elements will be stored.
        self.results = []
        self.results_stuff = []

        self.draw()

    def draw(self):
        """Add widgets to window."""
        self.search_bar.grid(column=0, row=0, sticky="NESW")
        self.search_but.grid(column=1, row=0, sticky="W")

    def search(self):
        """Search database for similar terms to ones in entry."""
        # Retrieve search term from entry and clear it.
        term = self.search_bar.get()
        self.clear()
        # If the entry bar has something it in.
        if term:
            # Send request for data to server.
            self.container.app.out_queue.put("search|{}|{}".format(self.container.app.id, term))
            # If client receives a response, set it as results.
            try:
                self.results = eval(self.container.app.in_queue.get(True, 4))
            # Otherwise warn client connection is loss.
            except queue.Empty:
                App.popup("warning", "No response from server, are you connected to the internet?")
                return
            # q is overall row counter.
            q = 1
            # Loop through friends and draw with <view profile> button.
            for i, friend in enumerate(self.results[0]):
                self.results_stuff.append(SearchFrame(self, i + 1, friend[1], friend[0], 2))
                self.results_stuff[-1].draw()
                q += 1
            # Loop through peopple that have friend requests sent.
            for i, pending in enumerate(self.results[1]):
                self.results_stuff.append(SearchFrame(self, q + i + 1, pending[1], pending[0], 1))
                self.results_stuff[-1].draw()
                q += 1
            # Loop through non-friends and draw with <add friend> button.
            for i, user in enumerate(self.results[2]):
                self.results_stuff.append(SearchFrame(self, q + i + 1, user[1], user[0], 0))
                self.results_stuff[-1].draw()

    def clear(self):
        """Empty out all search results."""
        for p in self.results_stuff:
            p.destroy()
        self.results_stuff = []

# <name> <button>
class SearchFrame:
    def __init__(self, container, row, username, id, friend):
        # Initiliase class variables.
        self.container = container

        self.row = row
        self.username = username
        self.id = id
        # friend = 0, not friends.
        # friend = 1, requested but not accepted.
        # friend= 2, users are friends.
        if friend == 1:
            cmd = None
            text = "Request pending"
        elif friend == 2 or Login.admin:
            cmd = lambda: self.container.container.load(self.id)
            text = "View profile"
        else:
            cmd = self.add_friend
            text = "Add friend"
        # Configure how frame looks.
        self.frame = tk.Frame(self.container.top, bg="white")
        self.frame.columnconfigure(0, minsize=100)
        self.frame.columnconfigure(1, minsize=100)
        # Configure name label and button.
        self.user_lab = tk.Label(self.frame, text=self.username, fg="royalblue2", bg="white",
                                 font=("trebuchet ms", 12, "bold"))

        self.profile_button = tk.Button(self.frame, text=text, bd=0, fg="royalblue3", bg="white",
                                        font=("trebuchet ms", 12, "bold"),
                                        command=cmd)

    def add_friend(self):
        """Send friend request to database."""
        self.container.container.app.out_queue.put("friends|{}|{}".format(self.container.container.app.id, self.id))
        # After clicking the button, prevent user from sending request again.
        self.profile_button.configure(command=lambda: App.popup("info", "Already sent a request!"))

    def draw(self):
        """Add widgets to frame."""
        self.frame.grid(column=0, row=self.row, pady=(5, 5), sticky="NSWE", columnspan=2)

        self.user_lab.grid(column=0, row=0, sticky="W", padx=5)

        self.profile_button.grid(column=4, row=0, sticky="E", padx=(40, 0))

    def destroy(self):
        """Delete this frame from memory."""
        self.frame.destroy()

        self.user_lab.destroy()
        self.profile_button.destroy()

        del self

# Requests                     | Friends
# <non-friend> <accept button> | <friend> <remove friend button>
class FriendDialog:
    def __init__(self, container):
        self.container = container
        # Create popup window and configure display.
        self.top = tk.Toplevel(self.container.app.root, bg="gray90")
        self.top.title("Add New Friends!")
        self.top.columnconfigure(0, minsize=240)
        self.top.columnconfigure(1, minsize=240)
        # _l = left, _r = right
        # Configure title labels and frames.
        self.title_l = tk.Label(self.top, text="Requests", fg="white", bg="royalblue2",
                                font=("trebuchet ms", 14, "bold"))
        self.title_r = tk.Label(self.top, text="Friends", fg="white", bg="royalblue2",
                                font=("trebuchet ms", 14, "bold"))

        self.left = tk.Frame(self.top, bg="gray90")
        self.right = tk.Frame(self.top, bg="gray90")
        # Initiliase storage lists.
        self.pending = []
        self.current = []

        self.get_stuff()
        self.draw()

    def draw(self):
        """Add widgets to this popup window."""
        self.title_l.grid(column=0, row=0, sticky="NEWS")
        self.title_r.grid(column=1, row=0, sticky="NEWS")

        self.left.grid(column=0, row=1, padx=10)
        self.right.grid(column=1, row=1, padx=10)

    def get_stuff(self):
        """Retrieve friend requests and current friends from database."""
        self.container.app.out_queue.put("pending|{}".format(self.container.app.id))
        self.clear()
        # Empty lists.
        pending, current = [], []
        # Get data from server and turn it into lists (eval).
        try:
            pending = eval(self.container.app.in_queue.get(True, 4))
        except queue.Empty:
            App.popup("warning", "No response from server, are you connected to the internet?")

        self.container.app.out_queue.put("current|{}".format(self.container.app.id))
        try:
            current = eval(self.container.app.in_queue.get(True, 4))
        except queue.Empty:
            App.popup("warning", "No response from server, are you connected to the internet?")
        # Loop through pending friends and create rows for each.
        for i, p in enumerate(pending):
            u = p[0]
            id = p[1]
            self.pending.append(Friend(self, i, u, id, 0, self.left))
        # Loop through current friends and create rows for each.
        for i, p in enumerate(current):
            u = p[0]
            id = p[1]
            self.current.append(Friend(self, i, u, id, 1, self.right))
        # If either list is empty, display nothing here.
        if not self.pending:
            self.pending.append(Friend(self, 0, "Nothing here!", -1, -1, self.left))
        if not self.current:
            self.current.append(Friend(self, 0, "Nothing here!", -1, -1, self.right))
        # Loop through both lists and draw the widgets to screen.
        for i, p in enumerate(self.pending):
            p.draw()
        for i, c in enumerate(self.current):
            c.draw()

    def clear(self):
        """Remove all of the GUI elements from memory."""
        for p in self.pending + self.current:
            p.destroy()
        self.pending = []
        self.current = []


class Friend:
    def __init__(self, container, row, username, id, is_friend, frame):
        # Initiliase class variables.
        self.container = container

        self.row = row
        self.username = username
        self.id = id
        self.is_friend = is_friend
        # Configure how frame looks.
        self.frame = tk.Frame(frame, bg="white", bd=2, relief="groove")
        self.frame.columnconfigure(0, minsize=120)
        self.frame.columnconfigure(1, minsize=120)
        # Set button to contextual command.
        if is_friend:
            cmd = self.remove
            text = "Remove Friend"
        else:
            cmd = self.accept
            text = "Accept Request"

        self.button_draw = True
        # Used for 'Nothing Here!' label case (no button.)
        if not id or is_friend == -1:
            self.button_draw = False
            self.frame.columnconfigure(0, minsize=0)
            self.frame.columnconfigure(1, minsize=0)
        # Initiliase labels.
        self.user_lab = tk.Label(self.frame, text=self.username, fg="royalblue2", bg="white",
                                 font=("trebuchet ms", 12, "bold"))

        self.profile_button = tk.Button(self.frame, text=text, bd=0, fg="royalblue3", bg="white",
                                        font=("trebuchet ms", 12, "bold"),
                                        command=cmd)

    def draw(self):
        """Add widgets to this frame."""
        self.frame.grid(column=0, row=self.row, pady=(5, 5), sticky="NSWE", columnspan=2)

        self.user_lab.grid(column=0, row=0, sticky="W")
        if self.button_draw:
            self.profile_button.grid(column=4, row=0, sticky="E")

    def remove(self):
        """Request removal of friend from friends."""
        self.container.container.app.out_queue.put("remove|{}|{}".format(self.id, self.container.container.app.id))
        self.container.container.app.root.after(1000, self.container.get_stuff)
        self.container.container.update_notifications()

    def accept(self):
        """Accept friend request."""
        self.container.container.app.out_queue.put("accept|{}|{}".format(self.id, self.container.container.app.id))
        self.container.container.app.root.after(1000, self.container.get_stuff)
        self.container.container.update_notifications()

    def destroy(self):
        """Remove this class and GUI from memory."""
        self.frame.destroy()

        self.user_lab.destroy()
        self.profile_button.destroy()

        del self


class StatisticsDialog:
    def __init__(self, container):
        # Initiliase class variable.
        self.container = container
        # Translate stored activity to regular sentences.
        self.options = {
            "run": "Ran {} kilometres.",
            "swim": "Swam {} metres.",
            "lift": "Lifted {} kilograms.",
            "cycle": "Cycled {} kilometres.",
            "push": "Did {} push-ups."
        }
        # Create popup window.
        self.top = tk.Toplevel(self.container.app.root)
        self.top.title("Statistics")
        self.top.configure(bg="royalblue2")
        # Configure drop-down box settings.
        self.selected_opt = tk.StringVar(self.top)
        self.selected_opt.set("Past week")
        self.dropdown = OrderedDict([["Past week", "7"],
                                     ["Past 2 weeks", "14"],
                                     ["Past month", "31"],
                                     ["All time", "-1"]])
        self.top_bar = tk.Frame(self.top, bg="royalblue3")
        # Initiliase labels and menu.
        self.username_label = tk.Label(self.top_bar, text="{}'s Statistics Page".format(self.container.app.username),
                                       fg="white", bg="royalblue3", font=("trebuchet ms", 14, "bold"), pady=2)
        self.calories_label = tk.Label(self.top, text="", fg="white", bg="royalblue2", font=("trebuchet ms", 10,
                                       "bold"))
        self.time_menu = tk.OptionMenu(self.top_bar, self.selected_opt, *self.dropdown.keys())

        self.time_menu.configure(bd=0, bg="royalblue3", fg="white", width=12, relief="flat",
                                 font=("trebuchet ms", 10, "bold"), activeforeground="white",
                                 activebackground="royalblue3")
        self.time_menu["menu"].config(bd=0, bg="royalblue3", fg="white",
                                      activeforeground="white", relief="flat",
                                      font=("trebuchet ms", 10, "bold"))

        self.selected_opt.trace('w', self.get_stuff)


        # Create 4 base labels to populate rather than create and remove temporary ones.
        self.activity_labels = []
        for x in range(4):
            self.activity_labels.append(tk.Label(self.top, text="", fg="white", bg="deepskyblue2",
                                                 font=("trebuchet ms", 12, "bold")))
        self.draw()
        self.get_stuff()

    def draw(self):
        """Add basic widgets to this window."""
        self.top_bar.grid(column=0, row=0)
        self.username_label.grid(column=0, row=0, padx=20)
        self.time_menu.grid(column=1, row=0)
        # drawing of activites done later.

    def get_stuff(self, *args):
        """Retrieve data from server, organise, and display."""
        self.clear()
        stuff_done = 0  # Used to work out relative width of each row.
        self.period = self.dropdown[self.selected_opt.get()]
        # Send request and evaluate the result.
        self.container.app.out_queue.put("activities|{}|{}".format(self.container.app.id, self.period))
        result = eval(self.container.app.in_queue.get(True, 4))
        # Loop through all posts and calculate total of each activity done.
        activities = {}
        for post in result:
            if post[0] in activities.keys():
                activities[post[0]] += int(post[1])
            else:
                activities[post[0]] = int(post[1])
            stuff_done += int(post[1])
        # Sort activities by amount done, and get last 4 from list (highest).
        top4 = list(sorted(activities.items(), key=operator.itemgetter(1)))[-4:]
        top4.reverse()
        r = 10  # keeps track of bottom of list
        # Loop through top 4 activities and display them appropriately.
        for row, activity in enumerate(top4):
            if activity[0] != "":
                self.activity_labels[row].configure(text=self.options[activity[0]].format(activity[1]),
                                                    width=int(activity[1] / stuff_done * 20) + 22)
                self.activity_labels[row].grid(column=0, row=row + 10, pady=5)
                r += 1
        # Attempt to retrieve personal info on user.
        self.container.app.out_queue.put("getinfo|{}".format(self.container.app.id))
        info = eval(self.container.app.in_queue.get(True, 4))[0]
        # If the info is not set, assume average height and weight.
        if int(info[0]) == 0:
            info = (177.0, 76.0)
        calories = 0
        # Loop through top 4 activities and estimate number of calories burned.
        for row, activity in enumerate(top4):
            if activity[0] != "":
            # first number = calories burned per x on average, which is multplied by percent of average weight and height
                if activity[0] == "run":
                    calories += (78 * int(activity[1])) * (info[0]/177.0) * (info[1]/76.0)
                elif activity[0] == "swim":
                    calories += (0.25 * int(activity[1])) * (info[0]/177.0) * (info[1]/76.0)
                elif activity[0] == "lift":
                    calories += (0.239 * int(activity[1])) * (info[0]/177.0) * (info[1]/76.0)
                elif activity[0] == "cycle":
                    calories += (37 * int(activity[1])) * (info[0]/177.0) * (info[1]/76.0)
                elif activity[0] == "push":
                    calories += (0.75 * int(activity[1])) * (info[0]/177.0) * (info[1]/76.0)
        self.calories_label.configure(text="{} calories burned doing these activities.".format(round(calories)))
        self.calories_label.grid(column=0, row=r)


    def clear(self):
        """Wipe labels in this class but keep them in memory."""
        for lab in self.activity_labels:
            lab.configure(text="")
            lab.grid_forget()



class AdminStats:
    def __init__(self, container):
        # Initiliase class variable.
        self.container = container
        self.top = tk.Toplevel(self.container.app.root)
        self.top.title("View stats.")
        self.top.configure(bg="gray90")

        self.options = {
            "run": ["Running: ", "{} kilometres."],
            "swim": ["Swimming: ", "{} metres."],
            "lift": ["Lifting: ", "{} kilograms."],
            "cycle": ["Cycling: ", "{} kilometres."],
            "push": ["Push-ups: ", "{} done."]
        }

        # Initiliase labels and stuff.
        # Activity popularity area.
        self.activity_frame = tk.Frame(self.top, bg="white", bd=2, relief="groove", padx=4)
        self.a_title = tk.Label(self.activity_frame, text="Activity Popularity", fg="black", bg="white",
                                font=("trebuchet ms", 18, "bold"))
        # Drop down stuff.
        self.a_selected_opt = tk.StringVar(self.top)
        self.a_selected_opt.set("Order by number of posts")
        self.a_dropdown = OrderedDict([["Order by number of posts", "p"],
                                     ["Order by amount done", "a"]])
        self.a_menu = tk.OptionMenu(self.activity_frame, self.a_selected_opt, *self.a_dropdown.keys())
        self.a_menu.configure(bd=0, bg="white", fg="black", width=22, relief="flat",
                                 font=("trebuchet ms", 12, "bold"), activeforeground="black",
                                 activebackground="white")
        self.a_menu["menu"].config(bd=0, bg="white", fg="black",
                                      activeforeground="black", relief="flat",
                                      font=("trebuchet ms", 12, "bold"))
        self.a_selected_opt.trace('w', self.activities)
        # End of dropdown.
        self.a_acts_labs = []

        self.draw()

    def draw(self):
        self.activity_frame.grid(row=0, column=0)
        self.a_title.grid(row=0, column=0)
        self.a_menu.grid(row=0, column=1)
        self.activities()

    def activities(self, *args):
        self.clear_activities()
        flag = self.a_dropdown[self.a_selected_opt.get()]
        self.container.app.out_queue.put("allactivity")
        result = eval(self.container.app.in_queue.get())
        acts = {}
        for activity, amount, date, text in result:
            if flag == 'p':
                if activity in acts.keys():
                    acts[activity] += 1
                else:
                    acts[activity] = 1
            if flag == 'a':
                if activity in acts.keys():
                    acts[activity] += int(amount)
                else:
                    acts[activity] = int(amount)

        for i, (name, number) in enumerate(list(sorted(acts.items(), key=operator.itemgetter(1), reverse=True))):
            if flag == 'p':
                x = self.options[name][0]+str(number)
            elif flag == 'a':
                x = ''.join(self.options[name]).format(number)
            self.a_acts_labs.append(tk.Label(self.activity_frame, text=x, fg="black", bg="white",
                                             font=("trebuchet ms", 12)))
            self.a_acts_labs[-1].grid(row=i+1, column=0, columnspan=2)

    def clear_activities(self):
        for lab in self.a_acts_labs:
            lab.destroy()
        self.a_acts_labs = []


# Account Info Popup Dialog
# Height: <textentry>
# Weight: <textentry>
# Age: <textentry>
# <Submit>
class AccountDialog:
    def __init__(self, container):
        # Initiliase class variable.
        self.container = container
        # Create popup window.
        self.top = tk.Toplevel(self.container.app.root)
        self.top.title("Tell us about yourself.")
        self.top.configure(bg="royalblue2")
        self.top.resizable(0,0)
        # Initiliase labels, entries, and button.
        self.title_label = tk.Label(self.top, text="Update Your Information", font=("trebuchet ms", 14, "bold"),
                                fg="white", bg="royalblue2")
        # h = height, w = weight, a = age.
        self.h_lab = tk.Label(self.top, text="Height (cm):", font=("trebuchet ms", 12, "bold"),
                                fg="white", bg="royalblue2")
        self.w_lab = tk.Label(self.top, text="Weight (kg):", font=("trebuchet ms", 12, "bold"),
                                 fg="white", bg="royalblue2")
        self.a_lab = tk.Label(self.top, text="Age:", font=("trebuchet ms", 12, "bold"),
                                 fg="white", bg="royalblue2")

        self.h = tk.Entry(self.top, font=("trebuchet ms", 11), width=12)
        self.w = tk.Entry(self.top, font=("trebuchet ms", 11), width=12)
        self.a = tk.Entry(self.top, font=("trebuchet ms", 11), width=12)

        self.submit_but = tk.Button(self.top, text="Submit", command=self.validate, bg="steelblue2", fg="white",
                                    bd=0, width=7, font=("trebuchet ms", 12))
        self.get_stuff()
        self.draw()


    def draw(self):
        """Add basic widgets to this window."""
        self.title_label.grid(column=0, row=0, columnspan=3, sticky="NEWS", padx=(0,5))

        self.h_lab.grid(column=0, row=1, padx=5, sticky="E")
        self.w_lab.grid(column=0, row=2,  padx=5, sticky="E")
        self.a_lab.grid(column=0, row=3, padx=5, sticky="E")

        self.h.grid(column=1, row=1, sticky="E")
        self.w.grid(column=1, row=2, sticky="E")
        self.a.grid(column=1, row=3, sticky="E")

        self.submit_but.grid(column=1, row=4, sticky="E", padx=0, pady=(5, 5))

    def validate(self):
        """Validate inputs and convert to correct floats."""
        height = self.isfloat(self.h.get())
        weight = self.isfloat(self.w.get())
        age = self.isfloat(self.a.get())
        # Check all inputs have been entered.
        if (height and weight and age):
            # If height, weight, and age are within reasonable ranges.
            if 0 < height < 300 and 0 < weight < 250 and 0 < age < 150:
                # Update data in database.
                self.container.app.out_queue.put("info|{}|{}|{}|{}".format(self.container.app.id, height, weight, age))
                # Destroy this window.
                self.top.destroy()
                del self
            else:
                App.popup("warning", "One or more of the details you have submitted are invalid, please ensure your details are correctly entered.")
        else:
            App.popup("warning", "One or more entries have been left blank, all are required to update info.")

    def isfloat(self, x):
        """If string is float, return value. Otherwise return false."""
        try:
            x = float(x)
            return x
        except TypeError:
            return False

    def get_stuff(self):
        """Retrieve personal data about user from database."""
        self.container.app.out_queue.put("getinfo|{}".format(self.container.app.id))
        info = eval(self.container.app.in_queue.get())
        # Insert data in database to input boxes.
        self.h.insert('end', info[0][0])
        self.w.insert('end', info[0][1])
        self.a.insert('end', info[0][2])

class App:
    def __init__(self):
        # Initiliase root tk window.
        self.root = tk.Tk()
        self.root.title("FitBook")
        self.root.configure(bg="royalblue2")
        self.root.resizable(width=False, height=False)
        # Initiliase variables for later use.
        self.id = -1
        self.username = ""

        self.s = socket.socket()
        # Attempt to connect to supplied server, otherwise raise error and close app.
        try:
            self.s.connect(SERVER)
        except Exception as e:
            self.root.after(3500, self.root.destroy)
            App.popup("error", "No connection could be established, app will close.")
            del self
            exit()

        # Queues are used for proper communication between threads, and tkinter.
        # This prevents overwrites and errors that can come from the other method.
        self.out_queue = queue.Queue()  # holds data to be sent to server.
        self.in_queue = queue.Queue()  # holds data received from server.
        # Create gui objects from classes.
        self.login_screen = Login(self)
        self.main = Main(self)
        # Draw login window as first window.
        self.login_screen.draw()
        # Start networking thread.
        t = threading.Thread(target=self.handler, args=(self.s, SERVER))
        t.setDaemon(True)  # closes thread when main app is closed.
        t.start()

        self.root.mainloop()

    def handler(self, s, a):
        """Network handling method. Takes socket and server ip as arguments."""
        # Loop below code unless stopped.
        while 1:
            # Attempt to:
            try:
                # Check if any data has been sent.
                ready = select.select([s], [], [], 0.25)
                # If some data does exist.
                if ready[0]:
                    # Retrieve the data and decode to regular text.
                    reply = s.recv(1024)
                    reply = reply.decode()
                    if not reply:
                        break
                    # Log data in console.
                    print('* received', reply)
                    # Place received data in in_queue.
                    self.in_queue.put(reply)
                # If data needs to be sent out.
                if not self.out_queue.empty():
                    # Encode data and send to server.
                    msg = self.out_queue.get()
                    s.send(msg.encode())
                    # Log data in console.
                    print("* sent:", msg)
            # If error occurs, print and properly close connection.
            except Exception as e:
                print(e)
                break
        s.close()
        print("closed connection with", a)

    @staticmethod
    def popup(box, msg):
        """Create popup message window. Takes box type, and message to display as arguments."""
        if box == "info":
            messagebox.showinfo("Information", msg)
        if box == "warning":
            messagebox.showwarning("Warning", msg)
        if box == "error":
            messagebox.showerror("Error", msg)


class Login:
    # Set static admin variable.
    admin = False

    def __init__(self, app):
        # Initiliase class variable.
        self.app = app  # store main app object locally.
        # Initiliase labels and frames.
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
        """Add this class's widgets to main window."""
        self.app.root.configure(bg="royalblue2")

        self.app.root.bind("<Return>", self.press_enter)

        self.title.grid(column=0, row=0, sticky="NEWS")

        self.main_frame.grid(column=0, row=1, padx=20, pady=(4, 8))

        self.mini_frame.grid(column=0, row=1, columnspan=2)
        # in frame
        self.user_lab.grid(column=0, row=0, padx=(0, 4))
        self.user_entry.grid(column=1, row=0)
        self.user_entry.focus_set()
        self.pass_lab.grid(column=0, row=1, padx=(0, 4))
        self.pass_entry.grid(column=1, row=1)

        self.signup_button.grid(column=0, row=2, sticky="E", padx=5, pady=(5, 0))
        self.login_button.grid(column=1, row=2, sticky="W", padx=5, pady=(5, 0))

    def undraw(self):
        """Remove this class's widgets from main window."""
        self.title.grid_forget()

        self.app.root.unbind("<Return>")

        self.main_frame.grid_forget()

        self.mini_frame.grid_forget()
        # in frame
        self.user_lab.grid_forget()
        self.user_entry.grid_forget()
        self.pass_lab.grid_forget()
        self.pass_entry.grid_forget()

        self.signup_button.grid_forget()
        self.login_button.grid_forget()
        # Also remove data from entry boxes.
        self.user_entry.delete(0, 'end')
        self.pass_entry.delete(0, 'end')

    def press_enter(self, event=None):
        self.login()

    def signup(self):
        """Signup new account routine."""
        # Retrieve name and password from entry.
        name = self.user_entry.get()
        passw = self.pass_entry.get()
        # If both are set.
        if name and passw:
            # Create salt for user.
            salt = Login.salt_generator()
            # Generate sha256 hash using password and salt, return hex version.
            passw_hash = hashlib.sha256(str(passw + salt).encode()).hexdigest()
            # Send request to server asking to create new account.
            self.app.out_queue.put("signup|{}|{}|{}".format(name, passw_hash, salt))
            success = self.app.in_queue.get(True, 10)
            # If server gives the ok.
            if success == "true":
                App.popup("info", "Successfully signed up.")
            # Otherwise the account already exists.
            elif success == "false":
                App.popup("info", "An account with that username already exists.")
                self.user_entry.delete(0, 'end')
                self.pass_entry.delete(0, 'end')
                self.user_entry.focus_set()

    def login(self):
        """Login existing account routine."""
        # Retrieve name and password from entry.
        name = self.user_entry.get()
        passw = self.pass_entry.get()
        # If both are set.
        if name and passw:
            # Attempt to:
            try:
                # Request the account's salt from the sever.
                self.app.out_queue.put("request|salt|{}".format(name))
                salt = self.app.in_queue.get(True, 5)
                # Generate sha256 hash using password entered and retrieved salt, return hex version.
                hash = hashlib.sha256(str(passw + salt).encode()).hexdigest()
                # Send request to server asking to login with given details.
                self.app.out_queue.put("login|{}|{}".format(name, hash))
                valid = self.app.in_queue.get(True, 5).split("|")
                # If account is valid
                if valid[0] == "true":
                    # Set app's user id and admin variable accordingly.
                    self.app.id = int(valid[1])
                    Login.admin = bool(int(valid[2]))
                    self.app.username = name
                    # Change from curretn window to main app window.
                    self.undraw()
                    self.app.main.draw()
                # If account is not valid.
                elif valid[0] == "false":
                    # Warn user of their mistake and clear entry boxes.
                    App.popup("info", "Invalid login credentials.")
                    self.user_entry.delete(0, 'end')
                    self.pass_entry.delete(0, 'end')
                    self.user_entry.focus_set()

            except queue.Empty as e:
                # If no data is retrieved from server.
                App.popup("warning", "Could not establish a connection with server.")

            except Exception as e:
                # If any other errors occur.
                print(e)

    @staticmethod
    def salt_generator(size=10):
        """Generate random ascii string."""
        # All letters and numbers.
        chars = string.ascii_uppercase + string.digits
        # Randomly join them.
        text = ''.join(random.choice(chars) for _ in range(size))
        return text


class Main:
    def __init__(self, app):
        # Initiliase class variable.
        self.app = app
        # Set defaults variables for later use.
        self.page = 1
        self.current_profile = 0
        self.notifs = 0
        # Initiliase labels, frames, and buttons.
        self.top_bar = tk.Frame(bg="royalblue3")

        self.user_but = tk.Button(self.top_bar, text="Oi!", bg="royalblue2", fg="white", width=6,
                                  font=("trebuchet ms", 12), padx=5, bd=0, command=self.load)

        self.post_but = tk.Button(self.top_bar, text="Post Something", bg="royalblue2", fg="white", bd=0, width=14,
                                  command=self.post, font=("trebuchet ms", 12))

        self.search_but = tk.Button(self.top_bar, text="Search", bg="royalblue2", fg="white", bd=0,
                                    width=8, command=self.search, font=("trebuchet ms", 12))

        self.friends_but = tk.Button(self.top_bar, text="Friends", bg="royalblue2", fg="white", bd=0,
                                     width=10, command=self.friends, font=("trebuchet ms", 12))
        self.stats_but = tk.Button(self.top_bar, text="Statistics", bg="royalblue2", fg="white", bd=0,
                                   width=10, command=self.stats, font=("trebuchet ms", 12))
        self.acc_but = tk.Button(self.top_bar, text="Account", bg="royalblue2", fg="white", bd=0,
                                   width=10, command=self.acc, font=("trebuchet ms", 12))
        self.ad_stats_but = tk.Button(self.top_bar, text="Admin Statistics", bg="royalblue2", fg="white", bd=0,
                                   width=13, command=self.ad_stats, font=("trebuchet ms", 12))
        self.delete_but = tk.Button(self.top_bar, text="Delete Account", bg="firebrick3", fg="white", bd=0,
                                    width=15, command=self.delete_account, font=("trebuchet ms", 12))
        self.refresh_but = tk.Button(self.top_bar, text="↻", bg="royalblue2", fg="white", bd=0,
                                     width=3, command=lambda: self.load(self.current_profile),
                                     font=("trebuchet ms", 12))

        self.logout_but = tk.Button(self.top_bar, text="Log Out", bg="royalblue2", fg="white", bd=0, width=7,
                                    command=self.logout, font=("trebuchet ms", 12))

        self.page_frame = tk.Frame(bg="gray90")

        self.bottom_bar = tk.Frame()
        self.ad_label = tk.Label(self.bottom_bar, text="")
        self.back_but = tk.Button(self.bottom_bar, text="<--", bg="gray90", fg="royalblue2", bd=0, width=4,
                                  command=self.back, font=("trebuchet ms", 15))
        self.next_but = tk.Button(self.bottom_bar, text="-->", bg="gray90", fg="royalblue2", bd=0, width=4,
                                  command=self.next, font=("trebuchet ms", 15))

        self.posts = []

    def advertisement(self):
        options = {
            "run": ["running", "shoes", "shorts"],
            "swim": ["swimming", "trunks", "goggles", "bikinis"],
            "lift": ["lifting", "gloves"],
            "cycle": ["cycling", "helmets", "shorts", "repair kits"]
        }
        self.app.out_queue.put("allactivity")
        result = eval(self.app.in_queue.get())
        acts = {}
        for activity, amount, date, text in result:
            if activity in acts.keys():
                acts[activity] += 1
            else:
                acts[activity] = 1
        popular = sorted(acts.items(), key=operator.itemgetter(1), reverse=True)
        print(popular)
        if popular[0][0] == "push":
            popular[0] = popular[1]
        popular = popular[0]
        message = "Get {}% off on {} {}.".format(random.randint(1,5)*10, options[popular[0]][0], random.choice(options[popular[0]][0:]))
        self.ad_label.configure(text=message)

    def post(self):
        """Instantiate post creation window."""
        PostDialog(self)

    def search(self):
        """Instantiate search window."""
        SearchDialog(self)

    def friends(self):
        """Instantiate friends window."""
        FriendDialog(self)

    def stats(self):
        """Instantiate statistics window."""
        StatisticsDialog(self)

    def acc(self):
        """Instantiate account information window."""
        AccountDialog(self)

    def ad_stats(self):
        """Initiate admin statistics window."""
        AdminStats(self)

    def delete_account(self):
        """Remove currently selected account from server."""
        # Ask for user confirmation.
        yn = messagebox.askyesno("Confirmation", "Deleting this account will remove it permanently from the server.\n"
                                                 "Are you sure?")
        # If user is sure.
        if yn:
            # Tell server to delete account.
            self.app.out_queue.put("deleteacc|{}".format(self.current_profile))
            # If the deleted account is the user's; logout.
            if self.current_profile == self.app.id:
                self.logout()
            # Otherwise redirect to main feed.
            else:
                self.load()

    def back(self):
        """Change the next more recent page."""
        if self.page > 1:
            self.page -= 1
            self.load(self.current_profile)

    def next(self):
        """Change to next less recent page."""
        # If the current page is not blank.
        if not isinstance(self.posts[0], tk.Label):
            self.page += 1
            self.load(self.current_profile)

    def submit(self, activity, meta, text):
        """Create new activity post."""
        # Send server data.
        self.app.out_queue.put("new|{}|{}|{}|{}".format(self.app.id, activity, meta, text))
        # After 1 second refresh the feed.
        self.app.root.after(1000, self.load)

    def load(self, id=0):
        """Load the given ID's profile."""
        # Empty out any remaining posts.
        self.clear_posts()
        # Initiliase for later use.
        options = {
            "run": "Ran {} kilometres.",
            "swim": "Swam {} metres.",
            "lift": "Lifted {} kilograms.",
            "cycle": "Cycled {} kilometres.",
            "push": "Did {} push-ups."
        }
        # If no id is supplied, load the activity feed (all friends and self).
        if id == 0:
            # Ensure delete account button is not drawn.
            self.delete_but.grid_forget()
            # Move refresh button to given position (changes when delete button exists).
            self.refresh_but.grid(column=99, row=0, sticky="NS", padx=(156, 5))
            # If the feed has just been loaded (current profile will still be representing the profile just viewed.)
            if self.current_profile != 0:
                # Set page to 1st.
                self.page = 1
            # Load data from server.
            self.app.out_queue.put("feed|{}|{}".format(self.app.id, self.page * 5))
            # Set profile to 0 to match what is being dispayed.
            self.current_profile = 0
            feed = self.app.in_queue.get(True, 2)
            feed = eval(feed)  # interpret string as actual code (turn into list.)
            # Loop through the feed with i for row, and p for data.
            for i, p in enumerate(feed):
                u = p[0]  # username
                a = p[1]  # activity
                m = p[2]  # amount done (meta data)
                d = p[3]  # date
                t = p[4]  # body of text
                id = p[5] # user id
                f_id = p[6] # feed id
                # If activity is in 'options', format the given metadata into the string.
                if a in options.keys():
                    a = options[a].format(m)
                # Otherwise leave blank.
                else:
                    a = ""
                # Create Post object using above data.
                self.posts.append(Post(container=self, username=u, activity=a, date=d, text=t, user_id=id, feed_id=f_id))
                # Draw just added post to row i.
                self.posts[-1].draw(i)
            # Change top-left button to load own profile.
            self.user_but.configure(text="Profile", command=lambda: self.load(self.app.id))
        # Otherwise, load supplied profile id.
        else:
            # If the current_profile is not the one supplied, set page to 1st.
            if self.current_profile != id:
                self.page = 1
            flag = 0  # admin flag
            if Login.admin:
                flag = 1
            # Request profile from server
            self.app.out_queue.put("profile|{}|{}|{}|{}".format(id, self.app.id, self.page * 5, flag))
            # Set profile to one supplied to match what is being displayed.
            self.current_profile = id
            # If the account is an admin, or the account is owned by the user.
            if Login.admin or self.current_profile == self.app.id:
                # Allow them to delete the page.
                self.delete_but.grid(column=98, row=0, sticky="NS", padx=(5, 5))
                # Move refresh button to given postion (changes when delete button exists).
                self.refresh_but.grid(column=99, row=0, sticky="NS", padx=(5, 5))
            prof = self.app.in_queue.get(True, 2)
            prof = eval(prof)  # interpret string as actual code (turn into list.)
            # Loop through the profile with i for row, and p for data.
            for i, p in enumerate(prof):
                u = p[0]  # username
                a = p[1]  # activity
                m = p[2]  # amount done (meta data)
                d = p[3]  # date
                t = p[4]  # body of text
                f_id = p[5]  # feed id
                 # If activity is in 'options', format the given metadata into the string.
                if a in options.keys():
                    a = options[a].format(m)
                # Otherwise leave blank.
                else:
                    a = ""
                 # Create Post object using above data.
                self.posts.append(Post(container=self, username=u, activity=a, date=d, text=t, user_id=-id, feed_id=f_id))
                # Draw just added post to row i.
                self.posts[-1].draw(i)
            # Change top-left button to load own profile.
            self.user_but.configure(text="Feed", command=self.load)
        # If no posts have been drawn
        if len(self.posts) == 0:
            # Add a friendly message instead of displaying a blank page.
            self.posts.append(tk.Label(self.page_frame, text="No posts here!", fg="gray65", bg="gray95",
                                       font=("trebuchet ms", 12, "bold"), bd=2, relief="groove", padx=40, pady=20))
            self.posts[0].grid(row=1, pady=10)

    def logout(self):
        """Clear user data and go back to login page."""
        self.app.id = -1
        self.app.username = ""

        self.undraw()
        self.app.login_screen.draw()

    def draw(self):
        """Add this class's widgets to the main window."""
        self.app.root.configure(bg="gray90")
        self.top_bar.grid(column=0, row=0, sticky="NEWS", columnspan=2)

        self.user_but.grid(column=0, row=0, sticky="NSW", padx=(0, 5))
        self.user_but.configure(text="Profile")
        self.post_but.grid(column=3, row=0, sticky="NS", padx=(5, 5))
        self.search_but.grid(column=2, row=0, sticky="NS", padx=(5, 5))
        self.friends_but.grid(column=4, row=0, sticky="NS", padx=(5, 5))
        self.stats_but.grid(column=5, row=0, sticky="NS", padx=(5, 5))
        self.acc_but.grid(column=6, row=0, sticky="NS", padx=(5, 5))
        self.ad_stats_but.grid(column=7, row=0, sticky="NS", padx=(5, 5))
        self.refresh_but.grid(column=99, row=0, sticky="NS", padx=(200, 5))
        self.logout_but.grid(column=100, row=0, sticky="NSE", padx=(5, 0))

        self.page_frame.grid(column=0, row=1, columnspan=2)

        self.bottom_bar.grid(column=0, row=2, columnspan=2, sticky="NEWS")
        self.ad_label.grid(column=1, row=0)
        self.back_but.grid(column=0, row=0, sticky="W")
        self.next_but.grid(column=2, row=0, sticky="E")
        self.update_notifications()

        self.app.root.title("{}'s FitBook".format(self.app.username))

        self.load()
        self.advertisement()

    def undraw(self):
        """Remove this class's widgets from the main window."""
        self.top_bar.grid_forget()
        self.clear_posts()
        self.page_frame.grid_forget()

        self.back_but.grid_forget()
        self.next_but.grid_forget()

        self.app.root.title("FitBook")

    def update_notifications(self):
        """Check how many friend requests a user has."""
        self.app.out_queue.put("pending|{}".format(self.app.id))
        # Number of requests.
        n = len(eval(self.app.in_queue.get(True, 4)))
        # If there are some requests, display them next 'friends' text.
        if n:
            self.friends_but.configure(text="Friends ({})".format(n))
        else:
            self.friends_but.configure(text="Friends")

    def clear_posts(self):
        """Remove all current posts from memory."""
        # Loop through all drawn posts.
        for post in self.posts:
            # If the post is a Post object, use delete method.
            if isinstance(post, Post):
                post.delete()
            # Otherwise the post is a regular label, use the destroy method.
            else:
                post.destroy()
        # Empty posts list.
        self.posts = []


main = App()
