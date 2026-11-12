# Python → EXE Builder

## Project Overview

Python → EXE Builder is a small desktop application (Tkinter) that turns a Python
script into a standalone executable using [PyInstaller](https://pyinstaller.org).
Instead of typing long command-line flags, you pick your script, tick the options
you need, and click **Build EXE**.

The application is intentionally a single file: **`py2exe_builder.py`**. It has no
third-party dependencies of its own — Tkinter ships with Python, and PyInstaller is
installed from inside the app when needed.

> The `_builder` suffix avoids confusion with the unrelated PyPI package named `py2exe`.

---

## Main Features

- Simple GUI for PyInstaller: browse, tick options, build.
- **Setup check** — confirms the selected Python interpreter and PyInstaller are available.
- **One-click install/update** of PyInstaller (and automatic build afterwards if it was missing).
- **Scan imports** — finds modules your script imports that are not installed for the
  selected interpreter, and suggests the matching `pip install` command.
- **Live command preview** — shows the exact PyInstaller command, with a Copy button.
- **Live, colour-coded log** — errors in red, warnings in yellow, success in green;
  the log can be saved to a file.
- **Stop button** — cancels a running build, including child processes on Windows.
- **Result check** — verifies the EXE really exists after the build.
- **Smart error hints** — recognises common failures and suggests likely fixes.
- **Open output folder** and **Run EXE** buttons after a successful build.
- Remembers your options between sessions.

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.8+ |
| GUI toolkit | Tkinter / ttk (standard library) |
| Build engine | [PyInstaller](https://pyinstaller.org) (invoked as a subprocess) |
| Concurrency | `threading` + `queue` for background work and UI updates |
| Persistence | A small JSON settings file in the user's home directory |
| Packaging of this app itself | Not required — it is a single `.py` file |

No external Python packages are required to *run* the app. PyInstaller is only
needed to build executables, and the app can install it for you.

---

## Project Folder Structure

```
python single file(.py) to window app(.exe)/
├── py2exe_builder.py     # the entire application
├── README.md             # this document
├── LICENSE               # public-domain dedication (The Unlicense)
└── tests/
    └── test_builder.py   # automated tests (optional)
```

When you build a target script, PyInstaller creates additional files next to that
script (see [Output Files and Folders](#output-files-and-folders)). Those are build
artifacts of your target project, not part of this app.

---

## Installation Requirements

| Item | Details |
|------|---------|
| Python | 3.8 or newer |
| Tkinter | Included with the standard Windows/macOS installers. On Linux: `sudo apt install python3-tk` |
| PyInstaller | Installed from inside the app, or manually: `python -m pip install pyinstaller` |
| OS | Windows (primary target). Also works on macOS/Linux, but see [Known Limitations](#known-limitations) |

---

## Installation Instructions

1. Install Python from <https://www.python.org/downloads/>. On Windows, tick
   **"Add Python to PATH"** during setup.
2. Place `py2exe_builder.py` in any folder.
3. (Optional) Install PyInstaller yourself:

   ```
   python -m pip install pyinstaller
   ```

   If you skip this step, the app offers to install it when you first build.

> **Note:** the PyPI project named `py2exe` is unrelated to this app. The
> `_builder` suffix keeps the filenames distinct and avoids module-shadowing
> confusion.

---

## How to Run the Project

```
python py2exe_builder.py
```

You can also double-click the file, or open it in IDLE and press **F5**.

---

## Running the Tests

The optional automated suite verifies the helper functions, command construction,
option parsing, and settings persistence. GUI tests create a hidden window and are
skipped automatically on headless machines.

```
python -m unittest discover -s tests -v
```

To also run the slow real PyInstaller build test (requires PyInstaller):

```
# PowerShell
$env:PY2EXE_E2E=1; python -m unittest discover -s tests -v
```

```
# cmd.exe
set PY2EXE_E2E=1 && python -m unittest discover -s tests -v
```

```
# macOS / Linux
PY2EXE_E2E=1 python -m unittest discover -s tests -v
```

---

## Usage Instructions

### Quick start

1. Run the app (see above).
2. Click **Browse…** next to *Python file* and choose your script.
3. Tick **No console window** if your script is a GUI app (Tkinter, PyQt, etc.).
4. Click **▶ Build EXE**.
5. When it finishes, click **Yes** to open the output folder. Your EXE is inside.

### Basic tab

| Field / option | What it does |
|----------------|--------------|
| **Python file** | The script you want to convert (`.py` or `.pyw`). |
| **App name** | Name of the EXE. Leave blank to use the script name. |
| **Output folder** | Where the EXE is placed. Leave blank for `<script folder>\dist`. A relative path is also resolved next to the script. |
| **Icon (.ico)** | Optional icon for the EXE. Must be a real `.ico` file. |
| **Single file** | One `.exe` file instead of a folder with many files. |
| **No console window** | Hides the black console window. Use for GUI programs. |
| **Clean build cache** | Deletes old build cache first. Fixes many odd build problems. |
| **Request admin rights** | The EXE asks for Administrator permission when launched (Windows only). |

### Advanced tab

| Field | What it does |
|-------|--------------|
| **Python interpreter** | Which `python.exe` runs PyInstaller. Defaults to the one running this app. Change it if your script's libraries live in a different Python or virtual environment. |
| **Hidden imports** | Modules PyInstaller fails to detect. Separate with commas, semicolons, or spaces (e.g. `pkg_a, pkg_b`). |
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

### Options explained

**Single file vs. folder**

- *Single file*: easiest to share, but starts a little slower (it unpacks itself to a
  temp folder on each launch) and is more often flagged by antivirus.
- *Folder (unchecked)*: starts faster and triggers fewer antivirus warnings, but you
  must distribute the whole folder.

**Console vs. windowed**

- Keep the console visible for command-line scripts and while debugging, since you
  can see error messages.
- Use windowed for finished GUI apps. If a windowed EXE closes instantly, rebuild
  with the console enabled to see the error.

---

## Bundling Data Files

If your program uses extra files (images, config, databases), add them on the
**Advanced** tab with **Add file…** or **Add folder…**. Then, in your script, locate
them with this pattern so it works both normally and inside the EXE:

```python
import os
import sys


def resource_path(relative):
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, relative)


logo = resource_path("logo.png")
```

Added files go to the root of the bundle (`.`). Added folders keep their folder name.

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

## Dependencies

- **Runtime (this app):** Python standard library only — `tkinter`, `subprocess`,
  `threading`, `queue`, `json`, `ast`, `shlex`, `shutil`, `os`, `sys`, `time`.
- **Build-time:** [PyInstaller](https://pypi.org/project/pyinstaller/). Install it with:

  ```
  python -m pip install pyinstaller
  ```

There is no `requirements.txt` for this app because it has no third-party runtime
dependencies. PyInstaller is managed by the app's **Install / Update PyInstaller**
button or by pip.

---

## Configuration

Your choices (single file, windowed, clean, admin, interpreter) are saved after a
successful build and when you close the app:

```
%USERPROFILE%\.py2exe_builder.json
```

On macOS/Linux this is `~/.py2exe_builder.json`. Delete this file to reset to defaults.

The file only stores UI options and the interpreter path; it contains no secrets.

---

## Important Notes

- The app is a front end for PyInstaller. The behaviour of the generated EXE
  depends on PyInstaller and on your script.
- **Antivirus false positives** are common for PyInstaller executables. Prefer folder
  mode, add an exclusion for the output folder, or sign the EXE.
- **Build for the same OS you run on.** PyInstaller does not cross-compile.
- If a build fails, read the log first — the app prints likely fixes underneath the
  error.
- Very large or unusual packages (some machine-learning or Qt libraries) may need
  extra options via **Hidden imports** or **Extra PyInstaller args**.
- **High-DPI / blurry windows:** the builder is DPI-aware and automatically adjusts
  its scaling and window size when Windows scaling changes or the window is moved to
  a monitor with a different DPI. If an **app you build** looks blurry on a high-DPI
  screen, add this to the top of that app's script before creating its window:

  ```python
  import ctypes
  try:
      ctypes.windll.shcore.SetProcessDpiAwareness(1)
  except Exception:
      pass
  ```

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
| Antivirus warning on the EXE | Common false positive for PyInstaller EXEs | Use folder mode, sign the EXE, or add an exclusion |
| Library works in IDLE but not in the EXE | The builder uses a different Python | Set the right `python.exe` under **Advanced → Python interpreter** |

---

## FAQ

**Do users of my EXE need Python installed?**

No. Python and your libraries are bundled inside.

**Can I build a Windows EXE on Mac or Linux?**

No. PyInstaller builds for the system it runs on. Build on Windows to get a `.exe`.

**Why is my EXE so large?**

It includes Python and every library your script imports. Using a clean virtual
environment with only the libraries you need keeps it smaller.

**Can I reuse the `.spec` file?**

Yes, from a terminal: `python -m PyInstaller your_script.spec`.

**Where do I see the exact command used?**

In the *Command preview* box. Copy it and run it in a terminal if you like.

---

## Known Limitations

- Builds only for the operating system you run it on (no cross-compiling).
- Very large or unusual packages may need extra PyInstaller options.
- Drag and drop of files is not supported; use **Browse…**.
- `--uac-admin` has no effect outside Windows.
- The app holds build output in memory for error diagnosis; extremely long builds are
  capped to the most recent output to keep memory usage bounded.
- The app is a front end for PyInstaller. Behaviour of the EXE itself depends on
  PyInstaller and your script.

---

## Future Improvements

- Remember the last script, icon, and data-file list between sessions.
- Add a cancellable per-step progress indication instead of an indeterminate bar.
- Optionally detect and offer to install missing imports directly.
- Add code signing guidance for distributed EXEs.
- Support drag-and-drop of the source script.

---

## License

This project is released into the **public domain** under
[The Unlicense](LICENSE). Anyone may use, copy, modify, sell, or distribute it for
any purpose, commercial or non-commercial, with no attribution required.

See [LICENSE](LICENSE) for the full text.
