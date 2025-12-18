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
