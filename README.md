# Python → EXE Builder

A desktop app (Tkinter) that turns a Python script into a standalone executable using [PyInstaller](https://pyinstaller.org). No command line needed: pick your script, choose options, click **Build EXE**.

The main file is `py2exe_builder.py`.

---

## Table of Contents

1. [Features](#features)
2. [Requirements](#requirements)
3. [Installation](#installation)
4. [Quick Start](#quick-start)
5. [Using the App](#using-the-app)
6. [Options Explained](#options-explained)
7. [Output Files and Folders](#output-files-and-folders)
8. [Bundling Data Files](#bundling-data-files)
9. [Troubleshooting](#troubleshooting)
10. [FAQ](#faq)
11. [Settings File](#settings-file)
12. [Limitations](#limitations)

---

## Features

- Simple GUI for PyInstaller: browse, tick options, build.
- **Setup check**: confirms the Python interpreter and PyInstaller are available.
- **One-click install/update** of PyInstaller (with automatic build afterwards if it was missing).
- **Scan imports**: finds modules your script needs that are not installed, and suggests the `pip install` command.
- **Live command preview**: shows the exact PyInstaller command, with a Copy button.
- **Live, colour-coded log**: errors in red, warnings in yellow, success in green. Can be saved to a file.
- **Stop button**: cancels a running build, including child processes.
- **Result check**: verifies the EXE really exists after the build.
- **Smart error hints**: recognises common failures and tells you the likely fix.
- **Open output folder** and **Run EXE** buttons after a successful build.
- Remembers your options between sessions.

---

## Requirements

| Item | Details |
|------|---------|
| Python | 3.8 or newer |
| Tkinter | Included with the standard Windows/macOS installers. On Linux: `sudo apt install python3-tk` |
| PyInstaller | Installed from inside the app, or manually: `python -m pip install pyinstaller` |
| OS | Windows (primary target). Also works on macOS/Linux, but see [Limitations](#limitations) |

---

## Installation

1. Install Python from <https://www.python.org/downloads/>. On Windows, tick **"Add Python to PATH"** during setup.
2. Put `py2exe_builder.py` in any folder.
3. (Optional) Install PyInstaller yourself:
   ```
   python -m pip install pyinstaller
   ```
   If you skip this step, the app offers to install it for you.

> **Important:** do not rename the file to `py2exe.py`. That name clashes with a real Python package called `py2exe`.

---

## Quick Start

1. Run the app:
   ```
   python py2exe_builder.py
   ```
   (or double-click it, or open it in IDLE and press F5)
2. Click **Browse…** next to *Python file* and choose your script.
3. Tick **No console window** if your script is a GUI app (Tkinter, PyQt, etc.).
4. Click **▶ Build EXE**.
5. When it finishes, click **Yes** to open the output folder. Your EXE is inside.

---

## Using the App

### Basic tab

| Field / option | What it does |
|----------------|--------------|
| **Python file** | The script you want to convert (`.py` or `.pyw`). |
| **App name** | Name of the EXE. Leave blank to use the script name. |
| **Output folder** | Where the EXE is placed. Leave blank for `<script folder>\dist`. |
| **Icon (.ico)** | Optional icon for the EXE. Must be a real `.ico` file. |
| **Single file** | One `.exe` file instead of a folder with many files. |
| **No console window** | Hides the black console window. Use for GUI programs. |
| **Clean build cache** | Deletes old build cache first. Fixes many odd build problems. |
| **Request admin rights** | The EXE asks for Administrator permission when launched (Windows). |

### Advanced tab

| Field | What it does |
|-------|--------------|
| **Python interpreter** | Which `python.exe` runs PyInstaller. Defaults to the one running this app. Change it if your script's libraries live in a different Python or virtual environment. |
| **Hidden imports** | Modules PyInstaller fails to detect, comma separated (e.g. `pkg_a, pkg_b`). |
| **Extra PyInstaller args** | Any other PyInstaller flag, e.g. `--collect-all customtkinter`. |
| **Data files / folders** | Files or folders to bundle inside the EXE (images, JSON, sounds, …). |

### Buttons

| Button | Action |
|--------|--------|
| **▶ Build EXE** | Starts the build. |
| **■ Stop** | Cancels the current task. |
| **Check setup** | Shows Python version, PyInstaller version and interpreter path. |
| **Install / Update PyInstaller** | Runs `pip install --upgrade pyinstaller` for the selected interpreter. |
| **Scan imports** | Lists imports that are not installed for the selected interpreter. |
| **Open output folder** | Opens the folder containing the last built EXE. |
| **Run EXE** | Launches the last built EXE so you can test it. |
| **Save log… / Clear log** | Saves or clears the log window. |

---

## Options Explained

**Single file vs. folder**
- *Single file*: easiest to share, but starts a little slower (it unpacks itself to a temp folder on each launch) and is more often flagged by antivirus.
- *Folder (unchecked)*: starts faster and triggers fewer antivirus warnings, but you must distribute the whole folder.

**Console vs. windowed**
- Keep the console visible for command-line scripts and while debugging, since you can see error messages.
- Use windowed for finished GUI apps. If a windowed EXE closes instantly, rebuild with the console enabled to see the error.

---

## Output Files and Folders

After building, next to your script you will find:

```
your_script_folder/
├── your_script.py
├── your_script.spec      ← PyInstaller build recipe (can be reused)
├── build/                ← temporary build files (safe to delete)
└── dist/                 ← your finished EXE is here
    └── your_script.exe       (single file mode)
    └── your_script/          (folder mode)
        └── your_script.exe
```

If you chose a custom *Output folder*, the EXE goes there instead of `dist`.

---

## Bundling Data Files

If your program uses extra files (images, config, databases), add them on the **Advanced** tab with **Add file…** or **Add folder…**. Then, in your script, locate them with this pattern so it works both normally and inside the EXE:

```python
import os, sys

def resource_path(relative):
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, relative)

logo = resource_path("logo.png")
```

Added files go to the root of the bundle (`.`). Added folders keep their folder name.

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---------|--------------|-----|
| "PyInstaller is not available" | Not installed for the selected Python | Click **Install / Update PyInstaller** |
| Build says success but no EXE | Antivirus deleted it | Add the output folder to antivirus exclusions, rebuild |
| `PermissionError` / "Access is denied" | The old EXE is still running or locked | Close it, close Explorer windows on `dist`, pause antivirus |
| `ModuleNotFoundError` in the log | A library isn't installed for that interpreter | Click **Scan imports**, install what's missing, or add under *Hidden imports* |
| EXE builds, but crashes when run | Missing hidden import or data file | Build with the console enabled to read the error; add the missing import/data |
| EXE opens then instantly closes | Windowed mode hides the error | Rebuild without *No console window* |
| Unsupported Python version message | Python newer than your PyInstaller | Click **Install / Update PyInstaller** |
| Icon error | File isn't a valid `.ico` | Convert the image to a proper `.ico` |
| Antivirus warning on the EXE | Common false positive for PyInstaller EXEs | Use folder mode, or sign the EXE, or add an exclusion |
| Library works in IDLE but not in the EXE | The builder uses a different Python | Set the right `python.exe` under **Advanced → Python interpreter** |

---

## FAQ

**Do users of my EXE need Python installed?**
No. Python and your libraries are bundled inside.

**Can I build a Windows EXE on Mac or Linux?**
No. PyInstaller builds for the system it runs on. Build on Windows to get a `.exe`.

**Why is my EXE so large?**
It includes Python and every library your script imports. Using a clean virtual environment with only the libraries you need keeps it smaller.

**Can I reuse the `.spec` file?**
Yes, from a terminal: `python -m PyInstaller your_script.spec`.

**Where do I see the exact command used?**
In the *Command preview* box. Copy it and run it in a terminal if you like.

---

## Settings File

Your choices (single file, windowed, clean, admin, interpreter) are saved after a successful build and when you close the app:

```
%USERPROFILE%\.py2exe_builder.json
```

Delete this file to reset to defaults.

---

## Limitations

- Builds only for the operating system you run it on (no cross-compiling).
- Very large or unusual packages (e.g. some machine learning or Qt libraries) may need extra PyInstaller options. Use *Hidden imports* or *Extra PyInstaller args*.
- Drag and drop of files is not supported; use **Browse…**.
- The app is a front end for PyInstaller. Behaviour of the EXE itself depends on PyInstaller and your script.
