import json
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, simpledialog
import os
import shutil
import hashlib
import base64
from datetime import datetime
from pathlib import Path
from cryptography.fernet import Fernet
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import defaultdict


MAX_LOGIN_ATTEMPTS = 3
LOGIN_TIMEOUT = 300

PROTECTED_PATHS = [
    "/System", "/Windows", "/Program Files", "/Program Files (x86)",
    "C:\\Windows", "C:\\Program Files", "C:\\Program Files (x86)",
    "/bin", "/sbin", "/usr/bin", "/usr/sbin"
]

PASSWORD_HASH = hashlib.sha256("admin123".encode()).hexdigest()
LOG_FILE = os.path.join(os.path.dirname(__file__), "file_manager.log")
PASSWORD_CONFIG = os.path.join(os.path.dirname(__file__), "password.cfg")
TRASH_DIR = os.path.join(os.path.dirname(__file__), ".trash")
LOGIN_ATTEMPTS_FILE = os.path.join(os.path.dirname(__file__), "login_attempts.json")

os.makedirs(TRASH_DIR, exist_ok=True)


def get_key():
    key_file = os.path.join(os.path.dirname(__file__), ".key")
    if os.path.exists(key_file):
        with open(key_file, "rb") as f:
            return f.read()
    key = Fernet.generate_key()
    with open(key_file, "wb") as f:
        f.write(key)
    return key


def encrypt_data(data):
    key = get_key()
    f = Fernet(key)
    return base64.b64encode(f.encrypt(data.encode())).decode()


def decrypt_data(data):
    try:
        key = get_key()
        f = Fernet(key)
        return f.decrypt(base64.b64decode(data.encode())).decode()
    except Exception:
        return data


def load_password():
    global PASSWORD_HASH
    if os.path.exists(PASSWORD_CONFIG):
        with open(PASSWORD_CONFIG, "r") as f:
            PASSWORD_HASH = decrypt_data(f.read().strip())


def save_password(pwd_hash):
    global PASSWORD_HASH
    with open(PASSWORD_CONFIG, "w") as f:
        f.write(encrypt_data(pwd_hash))
    PASSWORD_HASH = pwd_hash


def verifyPassword(password):
    return hashlib.sha256(password.encode()).hexdigest() == PASSWORD_HASH


def load_attempts():
    if os.path.exists(LOGIN_ATTEMPTS_FILE):
        with open(LOGIN_ATTEMPTS_FILE, "r") as f:
            return json.load(f)
    return {"attempts": 0, "last_attempt": 0}


def save_attempts(data):
    with open(LOGIN_ATTEMPTS_FILE, "w") as f:
        json.dump(data, f)


def reset_attempts():
    save_attempts({"attempts": 0, "last_attempt": 0})


def increment_attempts():
    data = load_attempts()
    data["attempts"] += 1
    data["last_attempt"] = datetime.now().timestamp()
    save_attempts(data)


def is_locked():
    data = load_attempts()
    if data["attempts"] >= MAX_LOGIN_ATTEMPTS:
        elapsed = datetime.now().timestamp() - data["last_attempt"]
        if elapsed < LOGIN_TIMEOUT:
            return True, LOGIN_TIMEOUT - int(elapsed)
        reset_attempts()
    return False, 0


def is_protected_path(path):
    abs_path = os.path.abspath(path)
    for p in PROTECTED_PATHS:
        if abs_path.startswith(p):
            return True
    return False


def check_path(path, operation):
    if not os.path.exists(path):
        return False, "Path does not exist!"
    if is_protected_path(path):
        return False, f"Cannot {operation} protected system path!"
    forbidden = [PASSWORD_CONFIG, LOG_FILE, LOGIN_ATTEMPTS_FILE]
    if os.path.abspath(path) in [os.path.abspath(f) for f in forbidden]:
        return False, f"Cannot {operation} application files!"
    return True, ""


def moveToTrash(path):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(TRASH_DIR, f"{ts}_{os.path.basename(path)}")
    size = os.path.getsize(path) if os.path.isfile(path) else get_dir_size(path)

    with open(dest + ".meta", "w") as f:
        json.dump({
            "original_path": os.path.abspath(path),
            "deleted_at": datetime.now().isoformat(),
            "size": size
        }, f)

    shutil.move(path, dest)
    return True


def log_action(action, target, success, message=""):
    try:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result = "SUCCESS" if success else "FAIL"
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{ts} | {action.upper():15} | {result:7} | {target} | {message}\n")
    except IOError:
        pass


def get_dir_size(path):
    total = 0
    for dirpath, dirs, files in os.walk(path):
        for file in files:
            try:
                total += os.path.getsize(os.path.join(dirpath, file))
            except OSError:
                pass
    return total


def format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes:.2f} bytes"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    elif size_bytes < 1024 * 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024 * 1024):.2f} TB"


def login_screen():
    login_root = tk.Tk()
    login_root.title("File Manager - Login")
    login_root.geometry("400x300")
    login_root.resizable(False, False)
    login_root.configure(bg="SystemButtonFace")

    frame = tk.Frame(login_root, bg="SystemButtonFace")
    frame.pack(expand=True, fill="both", padx=30, pady=30)

    tk.Label(frame, text="File Manager", font=("Arial", 18, "bold"),
             bg="SystemButtonFace", fg="black").pack(pady=15)

    locked, remaining = is_locked()

    if locked:
        tk.Label(frame, text="Account locked!", font=("Arial", 12, "bold"),
                 bg="SystemButtonFace", fg="red").pack(pady=5)
        lbl = tk.Label(frame, text=f"Try again in {remaining} seconds",
                       font=("Arial", 10), bg="SystemButtonFace", fg="red")
        lbl.pack(pady=5)

        def countdown():
            locked2, rem2 = is_locked()
            if locked2 and rem2 > 0:
                lbl.config(text=f"Try again in {rem2} seconds")
                login_root.after(1000, countdown)
            else:
                login_root.destroy()
                login_screen()

        countdown()
        login_root.mainloop()
        return

    data = load_attempts()
    attemptsLeft = MAX_LOGIN_ATTEMPTS - data["attempts"]

    attempts_label = tk.Label(frame, text=f"Attempts left: {attemptsLeft}",
                              bg="SystemButtonFace", fg="gray", font=("Arial", 9))
    attempts_label.pack(pady=5)

    tk.Label(frame, text="Password:", bg="SystemButtonFace", fg="black",
             font=("Arial", 12)).pack(anchor="w", padx=5, pady=(10, 5))

    password_entry = tk.Entry(frame, show="*", width=35, font=("Arial", 12))
    password_entry.pack(pady=5)

    def attempt_login():
        locked2, _ = is_locked()
        if locked2:
            messagebox.showerror("Locked", "Too many failed attempts!")
            return

        pwd = password_entry.get()
        if verifyPassword(pwd):
            print("Login successful")
            log_action("login", "file_manager", True)
            reset_attempts()
            login_root.destroy()
            main_window()
        else:
            increment_attempts()
            d = load_attempts()
            left = MAX_LOGIN_ATTEMPTS - d["attempts"]

            if left > 0:
                messagebox.showerror("Wrong Password", f"Incorrect password!\n{left} attempts remaining.")
                attempts_label.config(text=f"Attempts left: {left}")
            else:
                messagebox.showerror("Locked", f"Locked for {LOGIN_TIMEOUT // 60} minutes.")
                login_root.destroy()
                login_screen()

            password_entry.delete(0, tk.END)

    password_entry.bind("<Return>", lambda e: attempt_login())

    tk.Button(frame, text="LOGIN", width=25, command=attempt_login,
              bg="SystemButtonFace", fg="black", font=("Arial", 10, "bold"),
              relief="raised", cursor="hand2").pack(pady=20)

    password_entry.focus()
    login_root.mainloop()


def main_window():
    root = tk.Tk()
    root.title("File Manager")
    root.geometry("900x700")
    root.configure(bg="SystemButtonFace")

    style = ttk.Style()
    style.theme_use('clam')
    style.configure('TNotebook', background="SystemButtonFace", borderwidth=0)
    style.configure('TNotebook.Tab', padding=[20, 10], font=("Arial", 10, "bold"))

    header = tk.Frame(root, bg="SystemButtonFace", height=60)
    header.pack(fill="x")
    header.pack_propagate(False)

    tk.Label(header, text="File Manager", font=("Arial", 16, "bold"),
             bg="SystemButtonFace", fg="black").pack(side="left", padx=20, pady=15)

    current_dir_var = tk.StringVar(value=os.getcwd())
    tk.Label(header, textvariable=current_dir_var, font=("Arial", 11),
             bg="SystemButtonFace", fg="black", anchor="w").pack(
        side="left", padx=10, pady=15, fill="x", expand=True)

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True, padx=10, pady=10)

    file_tab = tk.Frame(notebook, bg="SystemButtonFace")
    notebook.add(file_tab, text="Files")

    file_frame = tk.LabelFrame(file_tab, text="File Operations", bg="SystemButtonFace",
                               fg="black", font=("Arial", 11, "bold"), padx=15, pady=15)
    file_frame.pack(fill="both", expand=True, padx=10, pady=10)

    tk.Label(file_frame, text="File Name:", bg="SystemButtonFace", fg="black",
             font=("Arial", 10)).grid(row=0, column=0, sticky="w", pady=5)
    file_entry = tk.Entry(file_frame, width=50, font=("Arial", 10))
    file_entry.grid(row=0, column=1, pady=5, padx=5)

    def browse_file():
        filename = filedialog.askopenfilename()
        if filename:
            file_entry.delete(0, tk.END)
            file_entry.insert(0, filename)

    tk.Button(file_frame, text="Browse", command=browse_file,
              bg="SystemButtonFace", fg="black").grid(row=0, column=2, padx=5)

    tk.Label(file_frame, text="Content:", bg="SystemButtonFace", fg="black",
             font=("Arial", 10)).grid(row=1, column=0, sticky="nw", pady=5)
    content_text = scrolledtext.ScrolledText(file_frame, width=60, height=12, font=("Consolas", 9))
    content_text.grid(row=1, column=1, columnspan=2, pady=5, padx=5)

    btn_frame = tk.Frame(file_frame, bg="SystemButtonFace")
    btn_frame.grid(row=2, column=0, columnspan=3, pady=10)

    def create_file():
        filename = file_entry.get().strip()
        content = content_text.get("1.0", tk.END).strip()
        if not filename:
            messagebox.showwarning("Warning", "Please enter a file name!")
            return
        if os.path.exists(filename):
            if not messagebox.askyesno("Confirm", f"'{filename}' already exists. Overwrite?"):
                return
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Created: {filename}")
        messagebox.showinfo("Success", f"File '{filename}' created!")
        log_action("create", filename, True)
        refresh_file_tree()

    def read_file():
        filename = file_entry.get().strip()
        if not filename:
            messagebox.showwarning("Warning", "Please enter a file name!")
            return
        try:
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
            content_text.delete("1.0", tk.END)
            content_text.insert("1.0", content)
            log_action("read", filename, True)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def save_file():
        filename = file_entry.get().strip()
        content = content_text.get("1.0", tk.END).strip()
        if not filename:
            messagebox.showwarning("Warning", "Please enter a file name!")
            return
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Saved: {filename}")
        messagebox.showinfo("Success", "Saved!")
        log_action("save", filename, True)
        refresh_file_tree()

    def delete_file():
        filename = file_entry.get().strip()
        if not filename:
            messagebox.showwarning("Warning", "Please enter a file name!")
            return
        if not os.path.exists(filename):
            messagebox.showerror("Error", "File not found!")
            return
        valid, msg = check_path(filename, "delete")
        if not valid:
            messagebox.showerror("Error", msg)
            return
        if messagebox.askyesno("Confirm", f"Move '{filename}' to trash?"):
            if moveToTrash(filename):
                messagebox.showinfo("Success", "Moved to trash!")
                log_action("delete", filename, True)
                file_entry.delete(0, tk.END)
                content_text.delete("1.0", tk.END)
                refresh_file_tree()

    def copy_file():
        filename = file_entry.get().strip()
        if not filename or not os.path.exists(filename):
            messagebox.showwarning("Warning", "File not found!")
            return
        dest = filedialog.asksaveasfilename(initialfile=f"copy_of_{os.path.basename(filename)}")
        if dest:
            shutil.copy2(filename, dest)
            messagebox.showinfo("Success", f"Copied!")
            log_action("copy", filename, True)
            refresh_file_tree()

    def rename_file():
        filename = file_entry.get().strip()
        if not filename or not os.path.exists(filename):
            messagebox.showwarning("Warning", "File not found!")
            return
        valid, msg = check_path(filename, "rename")
        if not valid:
            messagebox.showerror("Error", msg)
            return
        new_name = simpledialog.askstring("Rename", "Enter new name:", initialvalue=filename)
        if new_name and new_name != filename:
            try:
                os.rename(filename, new_name)
                file_entry.delete(0, tk.END)
                file_entry.insert(0, new_name)
                messagebox.showinfo("Success", "Renamed!")
                log_action("rename", filename, True, f"-> {new_name}")
                refresh_file_tree()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    buttons = [
        ("Create", create_file),
        ("Read", read_file),
        ("Save", save_file),
        ("Delete", delete_file),
        ("Copy", copy_file),
        ("Rename", rename_file)
    ]

    for i, (text, cmd) in enumerate(buttons):
        tk.Button(btn_frame, text=text, command=cmd, width=12,
                  bg="SystemButtonFace", fg="black",
                  font=("Arial", 9, "bold"), relief="raised", cursor="hand2").grid(
            row=i // 3, column=i % 3, padx=5, pady=5)

    explorer_tab = tk.Frame(notebook, bg="SystemButtonFace")
    notebook.add(explorer_tab, text="Explorer")

    nav_frame = tk.Frame(explorer_tab, bg="SystemButtonFace")
    nav_frame.pack(fill="x", padx=10, pady=10)

    tk.Label(nav_frame, text="Path:", bg="SystemButtonFace", font=("Arial", 10)).pack(side="left", padx=5)
    path_entry = tk.Entry(nav_frame, font=("Arial", 10))
    path_entry.pack(side="left", fill="x", expand=True, padx=5)
    path_entry.insert(0, os.getcwd())

    def navigate():
        path = path_entry.get().strip()
        if os.path.isdir(path):
            os.chdir(path)
            current_dir_var.set(os.getcwd())
            path_entry.delete(0, tk.END)
            path_entry.insert(0, os.getcwd())
            refresh_file_tree()
        else:
            messagebox.showerror("Error", "Invalid directory!")

    def go_up():
        os.chdir("..")
        current_dir_var.set(os.getcwd())
        path_entry.delete(0, tk.END)
        path_entry.insert(0, os.getcwd())
        refresh_file_tree()

    def go_home():
        os.chdir(Path.home())
        current_dir_var.set(os.getcwd())
        path_entry.delete(0, tk.END)
        path_entry.insert(0, os.getcwd())
        refresh_file_tree()

    def create_new_folder():
        folderName = simpledialog.askstring("Create Folder", "Enter folder name:")
        if folderName:
            folderPath = os.path.join(os.getcwd(), folderName)
            try:
                os.makedirs(folderPath)
                messagebox.showinfo("Success", f"Folder '{folderName}' created!")
                log_action("mkdir", folderPath, True)
                refresh_file_tree()
            except FileExistsError:
                messagebox.showerror("Error", "Already exists!")

    tk.Button(nav_frame, text="Go", command=navigate, bg="SystemButtonFace", fg="black", width=8).pack(side="left", padx=2)
    tk.Button(nav_frame, text="Up", command=go_up, bg="SystemButtonFace", fg="black", width=8).pack(side="left", padx=2)
    tk.Button(nav_frame, text="Home", command=go_home, bg="SystemButtonFace", fg="black", width=8).pack(side="left", padx=2)
    tk.Button(nav_frame, text="New Folder", command=create_new_folder, bg="SystemButtonFace", fg="black", width=12).pack(side="left", padx=2)

    tree_frame = tk.Frame(explorer_tab, bg="SystemButtonFace")
    tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

    tree = ttk.Treeview(tree_frame, columns=("Size", "Modified"), height=20)
    tree.heading("#0", text="Name")
    tree.heading("Size", text="Size")
    tree.heading("Modified", text="Modified")
    tree.column("#0", width=400)
    tree.column("Size", width=120)
    tree.column("Modified", width=200)

    sb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    tree.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")

    progress_var = tk.StringVar(value="")
    tk.Label(explorer_tab, textvariable=progress_var, bg="SystemButtonFace",
             fg="gray", font=("Arial", 9)).pack(pady=5)

    def refresh_file_tree():
        tree.delete(*tree.get_children())
        progress_var.set("Loading...")
        root.update_idletasks()

        items = sorted(os.listdir())

        for idx, item in enumerate(items):
            path = os.path.join(os.getcwd(), item)

            if os.path.isdir(path):
                prefix = "[LOCKED] " if is_protected_path(path) else ""
                progress_var.set(f"Loading... ({idx+1}/{len(items)})")
                root.update_idletasks()
                size = format_size(get_dir_size(path))
            else:
                prefix = ""
                size = format_size(os.path.getsize(path))

            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M")
            except OSError:
                mtime = "?"

            tree.insert("", "end", text=f"{prefix}{item}", values=(size, mtime))

        progress_var.set(f"{len(items)} items")

    def on_tree_double_click(event):
        sel = tree.selection()
        if not sel:
            return
        itemText = tree.item(sel[0])["text"]
        name = itemText.replace("[LOCKED] ", "")
        path = os.path.join(os.getcwd(), name)

        if os.path.isdir(path):
            if is_protected_path(path):
                messagebox.showwarning("Warning", "Protected system directory!")
                return
            print(f"Opening: {path}")
            os.chdir(path)
            current_dir_var.set(os.getcwd())
            path_entry.delete(0, tk.END)
            path_entry.insert(0, os.getcwd())
            refresh_file_tree()
        elif os.path.isfile(path):
            file_entry.delete(0, tk.END)
            file_entry.insert(0, path)
            notebook.select(0)

    tree.bind("<Double-1>", on_tree_double_click)

    def delete_selected():
        sel = tree.selection()
        if not sel:
            return
        itemText = tree.item(sel[0])["text"]
        name = itemText.replace("[LOCKED] ", "")
        path = os.path.join(os.getcwd(), name)

        valid, msg = check_path(path, "delete")
        if not valid:
            messagebox.showerror("Error", msg)
            return

        if messagebox.askyesno("Confirm", f"Move '{name}' to trash?"):
            if moveToTrash(path):
                messagebox.showinfo("Success", "Moved to trash!")
                log_action("delete", path, True)
                refresh_file_tree()

    ctx = tk.Menu(root, tearoff=0)
    ctx.add_command(label="Open", command=lambda: on_tree_double_click(None))
    ctx.add_command(label="Move to Trash", command=delete_selected)
    ctx.add_separator()
    ctx.add_command(label="Refresh", command=refresh_file_tree)
    tree.bind("<Button-3>", lambda e: ctx.post(e.x_root, e.y_root))

    trash_tab = tk.Frame(notebook, bg="SystemButtonFace")
    notebook.add(trash_tab, text="Trash")

    trash_frame = tk.LabelFrame(trash_tab, text="Recycle Bin", bg="SystemButtonFace",
                                fg="black", font=("Arial", 11, "bold"), padx=15, pady=15)
    trash_frame.pack(fill="both", expand=True, padx=10, pady=10)

    trash_tree = ttk.Treeview(trash_frame, columns=("Original Path", "Deleted At", "Size"), height=20)
    trash_tree.heading("#0", text="Name")
    trash_tree.heading("Original Path", text="Original Path")
    trash_tree.heading("Deleted At", text="Deleted At")
    trash_tree.heading("Size", text="Size")
    trash_tree.column("#0", width=250)
    trash_tree.column("Original Path", width=300)
    trash_tree.column("Deleted At", width=150)
    trash_tree.column("Size", width=100)
    trash_tree.pack(side="left", fill="both", expand=True)

    trash_sb = ttk.Scrollbar(trash_frame, orient="vertical", command=trash_tree.yview)
    trash_tree.configure(yscrollcommand=trash_sb.set)
    trash_sb.pack(side="right", fill="y")

    def refresh_trash():
        trash_tree.delete(*trash_tree.get_children())
        if not os.path.exists(TRASH_DIR):
            return
        for file in sorted(os.listdir(TRASH_DIR)):
            if file.endswith(".meta"):
                continue
            meta_file = os.path.join(TRASH_DIR, file + ".meta")
            orig, deleted_at, size = "?", "?", "?"
            if os.path.exists(meta_file):
                with open(meta_file, "r") as f:
                    meta = json.load(f)
                    orig = meta.get("original_path", "?")
                    deleted_at = meta.get("deleted_at", "?")
                    size = format_size(meta.get("size", 0))
            trash_tree.insert("", "end", text=file, values=(orig, deleted_at, size))

    def restore_file():
        sel = trash_tree.selection()
        if not sel:
            return
        name = trash_tree.item(sel[0])["text"]
        trashPath = os.path.join(TRASH_DIR, name)
        metaFile = trashPath + ".meta"
        orig = None

        if os.path.exists(metaFile):
            with open(metaFile, "r") as f:
                orig = json.load(f).get("original_path")

        if not orig:
            messagebox.showerror("Error", "Can't find original path!")
            return
        if os.path.exists(orig):
            messagebox.showerror("Error", "Already exists there!")
            return

        shutil.move(trashPath, orig)
        os.remove(metaFile)
        print(f"Restored: {orig}")
        messagebox.showinfo("Success", f"Restored!")
        log_action("restore", orig, True)
        refresh_trash()
        refresh_file_tree()

    def perm_delete():
        sel = trash_tree.selection()
        if not sel:
            return
        name = trash_tree.item(sel[0])["text"]
        trashPath = os.path.join(TRASH_DIR, name)
        metaFile = trashPath + ".meta"

        if not messagebox.askyesno("Confirm", f"Permanently delete '{name}'?"):
            return

        if os.path.isdir(trashPath):
            shutil.rmtree(trashPath)
        else:
            os.remove(trashPath)

        if os.path.exists(metaFile):
            os.remove(metaFile)

        print(f"Deleted: {name}")
        messagebox.showinfo("Success", "Deleted!")
        log_action("perm_delete", trashPath, True)
        refresh_trash()

    btn_row = tk.Frame(trash_tab, bg="SystemButtonFace")
    btn_row.pack(pady=5)
    tk.Button(btn_row, text="Restore", command=restore_file, bg="SystemButtonFace", fg="black", width=12).pack(side="left", padx=5)
    tk.Button(btn_row, text="Delete Permanently", command=perm_delete, bg="SystemButtonFace", fg="black", width=16).pack(side="left", padx=5)
    tk.Button(btn_row, text="Refresh", command=refresh_trash, bg="SystemButtonFace", fg="black", width=12).pack(side="left", padx=5)

    refresh_file_tree()
    refresh_trash()

    # stats tab
    stats_tab = tk.Frame(notebook, bg="SystemButtonFace")
    notebook.add(stats_tab, text="Stats")

    stats_controls = tk.Frame(stats_tab, bg="SystemButtonFace")
    stats_controls.pack(fill="x", padx=10, pady=8)

    tk.Label(stats_controls, text="Analyze:", bg="SystemButtonFace", font=("Arial", 10)).pack(side="left", padx=5)
    stats_path_entry = tk.Entry(stats_controls, font=("Arial", 10), width=45)
    stats_path_entry.pack(side="left", padx=5)
    stats_path_entry.insert(0, os.getcwd())

    chart_var = tk.StringVar(value="filetypes")
    charts = [
        ("File Types", "filetypes"),
        ("Folder Sizes", "folders"),
        ("Size Distribution", "sizedist"),
        ("Activity Log", "activity"),
    ]
    for label, val in charts:
        tk.Radiobutton(stats_controls, text=label, variable=chart_var, value=val,
                       bg="SystemButtonFace", font=("Arial", 9)).pack(side="left", padx=4)

    canvas_frame = tk.Frame(stats_tab, bg="SystemButtonFace")
    canvas_frame.pack(fill="both", expand=True, padx=10, pady=5)

    current_canvas = [None]

    def draw_filetypes(target_path, ax):
        ext_sizes = defaultdict(int)
        for f in os.scandir(target_path):
            if f.is_file():
                ext = os.path.splitext(f.name)[1].lower() or "(no ext)"
                try:
                    ext_sizes[ext] += f.stat().st_size
                except OSError:
                    pass
        if not ext_sizes:
            ax.text(0.5, 0.5, "No files found", ha="center", va="center", transform=ax.transAxes)
            return
        # keep top 8, group rest as "other"
        sorted_items = sorted(ext_sizes.items(), key=lambda x: x[1], reverse=True)
        top = sorted_items[:8]
        other_size = sum(v for _, v in sorted_items[8:])
        if other_size:
            top.append(("other", other_size))
        labels = [k for k, _ in top]
        sizes = [v for _, v in top]
        ax.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=140)
        ax.set_title("File Types by Size")

    def draw_folders(target_path, ax):
        folders = []
        for item in os.scandir(target_path):
            if item.is_dir():
                try:
                    size = get_dir_size(item.path)
                    folders.append((item.name, size))
                except OSError:
                    pass
        if not folders:
            ax.text(0.5, 0.5, "No subfolders", ha="center", va="center", transform=ax.transAxes)
            return
        folders.sort(key=lambda x: x[1], reverse=True)
        folders = folders[:12]
        names = [f[0][:18] for f in folders]
        sizes = [f[1] / (1024 * 1024) for f in folders]  # MB
        bars = ax.barh(names[::-1], sizes[::-1], color="#5b9bd5")
        ax.set_xlabel("Size (MB)")
        ax.set_title("Subfolder Sizes")
        for bar, size in zip(bars, sizes[::-1]):
            ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2,
                    f"{size:.1f}MB", va="center", fontsize=8)

    def draw_sizedist(target_path, ax):
        buckets = {"<1KB": 0, "1KB-100KB": 0, "100KB-1MB": 0, "1MB-50MB": 0, ">50MB": 0}
        for f in os.scandir(target_path):
            if f.is_file():
                try:
                    s = f.stat().st_size
                    if s < 1024:
                        buckets["<1KB"] += 1
                    elif s < 100 * 1024:
                        buckets["1KB-100KB"] += 1
                    elif s < 1024 * 1024:
                        buckets["100KB-1MB"] += 1
                    elif s < 50 * 1024 * 1024:
                        buckets["1MB-50MB"] += 1
                    else:
                        buckets[">50MB"] += 1
                except OSError:
                    pass
        colors = ["#70ad47", "#5b9bd5", "#ffc000", "#ed7d31", "#c00000"]
        ax.bar(buckets.keys(), buckets.values(), color=colors)
        ax.set_ylabel("Number of files")
        ax.set_title("File Size Distribution")
        for i, (k, v) in enumerate(buckets.items()):
            if v:
                ax.text(i, v + 0.1, str(v), ha="center", fontsize=9)

    def draw_activity(ax):
        if not os.path.exists(LOG_FILE):
            ax.text(0.5, 0.5, "No log file found", ha="center", va="center", transform=ax.transAxes)
            return
        action_counts = defaultdict(int)
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.split("|")
                    if len(parts) >= 2:
                        action = parts[1].strip().lower().rstrip()
                        action_counts[action] += 1
        except IOError:
            ax.text(0.5, 0.5, "Could not read log", ha="center", va="center", transform=ax.transAxes)
            return
        if not action_counts:
            ax.text(0.5, 0.5, "Log is empty", ha="center", va="center", transform=ax.transAxes)
            return
        actions = list(action_counts.keys())
        counts = list(action_counts.values())
        ax.barh(actions, counts, color="#5b9bd5")
        ax.set_xlabel("Count")
        ax.set_title("Actions from Log")

    def run_stats():
        target = stats_path_entry.get().strip()
        if not os.path.isdir(target) and chart_var.get() != "activity":
            messagebox.showerror("Error", "Invalid path!")
            return

        if current_canvas[0]:
            current_canvas[0].get_tk_widget().destroy()

        fig, ax = plt.subplots(figsize=(7, 4.5))
        fig.patch.set_facecolor("#f0f0f0")
        ax.set_facecolor("#f8f8f8")

        choice = chart_var.get()
        if choice == "filetypes":
            draw_filetypes(target, ax)
        elif choice == "folders":
            draw_folders(target, ax)
        elif choice == "sizedist":
            draw_sizedist(target, ax)
        elif choice == "activity":
            draw_activity(ax)

        plt.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        current_canvas[0] = canvas
        plt.close(fig)

    tk.Button(stats_controls, text="Run", command=run_stats,
              bg="SystemButtonFace", fg="black", width=8, relief="raised").pack(side="left", padx=6)

    root.mainloop()


if __name__ == "__main__":
    load_password()
    login_screen()