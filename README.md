# File Manager

![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python&logoColor=white)
![tkinter](https://img.shields.io/badge/GUI-tkinter-informational)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-working-brightgreen)

A simple file manager built with Python and tkinter. Started as a school project, ended up adding encryption, a trash system and some charts.

---

## Features

- Create, read, save, delete, copy and rename files
- Browse folders with a tree view
- Trash system — files can be restored
- Login screen with lockout after 3 failed attempts
- Encrypted password storage using Fernet
- Logs all actions to `file_manager.log`
- Stats tab with charts (needs matplotlib)

---

## Requirements

```bash
pip install cryptography matplotlib
```

Python 3.x

---

## How to run

```bash
python file_manager.py
```

> Default password is `admin123`

---

## File structure

```
project/
├── file_manager.py
├── file_manager.log       ← auto-created
├── password.cfg           ← auto-created
├── login_attempts.json    ← auto-created
├── .key                   ← auto-created (don't delete!)
└── .trash/                ← deleted files go here
```

---

## Notes

- Protected system paths (`/System`, `/Windows` etc.) can't be modified
- Don't delete `.key` — you'll lose access to the password
- Account locks for **5 minutes** after 3 wrong attempts
- The Stats tab crashes if matplotlib isn't installed

---

## Known issues

- Folder size calculation freezes the UI on large directories
- No search yet
- Can't change password from the UI