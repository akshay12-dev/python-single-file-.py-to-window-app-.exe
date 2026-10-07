import ast
import json
import os
import queue
import shlex
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_TITLE = "Python → EXE Builder"
CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".py2exe_builder.json")
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # hides console flashes on Windows
EXE_EXT = ".exe" if os.name == "nt" else ""

# import name -> pip package name (for friendlier suggestions)
PIP_NAMES = {
    "cv2": "opencv-python", "PIL": "pillow", "sklearn": "scikit-learn",
    "yaml": "pyyaml", "bs4": "beautifulsoup4", "win32com": "pywin32",
    "win32api": "pywin32", "dateutil": "python-dateutil", "serial": "pyserial",
    "docx": "python-docx", "fitz": "pymupdf", "Crypto": "pycryptodome",
}


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def find_python():
    """Return a real python interpreter (never pythonw, never a frozen exe)."""
    if getattr(sys, "frozen", False):
        for name in ("python", "py"):
            p = shutil.which(name)
            if p:
                return p
        return ""
    exe = sys.executable
    if os.path.basename(exe).lower() == "pythonw.exe":
        cand = os.path.join(os.path.dirname(exe), "python.exe")
        if os.path.isfile(cand):
            return cand
    return exe


def top_level_imports(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        tree = ast.parse(f.read(), path)
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                mods.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            mods.add(node.module.split(".")[0])
    return mods


def run_quiet(cmd, timeout=60):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout, creationflags=NO_WINDOW)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:  # noqa: BLE001
        return -1, str(e)


def classify(line):
    low = line.lower()
    if "error" in low or "traceback" in low or "failed" in low:
        return "error"
    if "warning" in low or "warn:" in low:
        return "warn"
    if "completed successfully" in low or "successfully installed" in low:
        return "ok"
    return "plain"


def diagnose(text):
    hints = []
    t = text.lower()
    if "no module named pyinstaller" in t:
        hints.append("PyInstaller is not installed for this interpreter → click 'Install / Update PyInstaller'.")
    if "permissionerror" in t or "access is denied" in t or "winerror 5" in t:
        hints.append("Permission denied → close any running copy of the EXE, close Explorer windows "
                     "showing the dist folder, and pause antivirus / exclude the output folder.")
    if "modulenotfounderror" in t or "no module named" in t:
        hints.append("A module is missing → use 'Scan imports', pip install what's missing in the SAME "
                     "interpreter, or add it under Advanced → Hidden imports.")
    if "unicodedecodeerror" in t or "unicodeencodeerror" in t:
        hints.append("Encoding problem → save your script as UTF-8 and avoid special characters in paths.")
    if "recursionerror" in t:
        hints.append("RecursionError → add  --additional-hooks-dir  or run with  sys.setrecursionlimit(5000)  in a .spec file.")
    if "unsupported python version" in t or "not supported" in t:
        hints.append("Your Python is probably newer than this PyInstaller → click 'Install / Update PyInstaller'.")
    if "icon" in t and ("error" in t or "invalid" in t):
        hints.append("Icon problem → use a real .ico file (not a renamed PNG).")
    return hints


def open_path(path):
    try:
        if os.name == "nt":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as e:  # noqa: BLE001
        messagebox.showerror("Open failed", str(e))


# ----------------------------------------------------------------------------
# Application
# ----------------------------------------------------------------------------
class App:
    def __init__(self, root):
        self.root = root
        root.title(APP_TITLE)
        root.geometry("900x780")
        root.minsize(780, 660)

        self.q = queue.Queue()
        self.proc = None
        self.running = False
        self.cancelled = False
        self.buf = []
        self.data = []            # list of (src, dest)
        self.last_exe = ""
        self.last_outdir = ""
        self.build_after_install = False

        self.script = tk.StringVar()
        self.name = tk.StringVar()
        self.outdir = tk.StringVar()
        self.icon = tk.StringVar()
        self.interp = tk.StringVar(value=find_python())
        self.onefile = tk.BooleanVar(value=True)
        self.windowed = tk.BooleanVar(value=False)
        self.clean = tk.BooleanVar(value=True)
        self.admin = tk.BooleanVar(value=False)
        self.hidden = tk.StringVar()
        self.extra = tk.StringVar()
        self.preview = tk.StringVar()
        self.status = tk.StringVar(value="Ready")

        self.load_settings()
        self.build_ui()
        for v in (self.script, self.name, self.outdir, self.icon, self.interp, self.onefile,
                  self.windowed, self.clean, self.admin, self.hidden, self.extra):
            v.trace_add("write", lambda *_: self.update_preview())
        self.update_preview()

        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.after(80, self.poll)
        root.after(300, lambda: self.start_check(silent=True))

    # ------------------------------------------------------------------ UI
    def build_ui(self):
        pad = {"padx": 8, "pady": 4}
        style = ttk.Style()
        try:
            style.theme_use("vista" if os.name == "nt" else "clam")
        except tk.TclError:
            pass
        style.configure("Build.TButton", font=("Segoe UI", 11, "bold"), padding=6)

        nb = ttk.Notebook(self.root)
        nb.pack(fill="x", padx=8, pady=(8, 0))

        # ---- Basic tab
        basic = ttk.Frame(nb)
        nb.add(basic, text="  Basic  ")
        basic.columnconfigure(1, weight=1)

        self._row_entry(basic, 0, "Python file", self.script, self.browse_script, "Browse…")
        self._row_entry(basic, 1, "App name", self.name, None, None, hint="blank = script name")
        self._row_entry(basic, 2, "Output folder", self.outdir, self.browse_outdir, "Browse…",
                        hint="blank = <script folder>\\dist")
        self._row_entry(basic, 3, "Icon (.ico)", self.icon, self.browse_icon, "Browse…")

        opts = ttk.LabelFrame(basic, text="Options")
        opts.grid(row=4, column=0, columnspan=3, sticky="ew", **pad)
        ttk.Checkbutton(opts, text="Single file (--onefile)", variable=self.onefile).grid(row=0, column=0, sticky="w", padx=8, pady=3)
        ttk.Checkbutton(opts, text="No console window (--windowed) – for GUI apps", variable=self.windowed).grid(row=0, column=1, sticky="w", padx=8, pady=3)
        ttk.Checkbutton(opts, text="Clean build cache (--clean)", variable=self.clean).grid(row=1, column=0, sticky="w", padx=8, pady=3)
        ttk.Checkbutton(opts, text="Request admin rights (--uac-admin)", variable=self.admin).grid(row=1, column=1, sticky="w", padx=8, pady=3)

        # ---- Advanced tab
        adv = ttk.Frame(nb)
        nb.add(adv, text="  Advanced  ")
        adv.columnconfigure(1, weight=1)

        self._row_entry(adv, 0, "Python interpreter", self.interp, self.browse_interp, "Browse…")
        self._row_entry(adv, 1, "Hidden imports", self.hidden, None, None, hint="comma separated")
        self._row_entry(adv, 2, "Extra PyInstaller args", self.extra, None, None, hint='e.g. --collect-all customtkinter')

        dframe = ttk.LabelFrame(adv, text="Extra data files / folders (--add-data)")
        dframe.grid(row=3, column=0, columnspan=3, sticky="ew", **pad)
        dframe.columnconfigure(0, weight=1)
        self.data_list = tk.Listbox(dframe, height=4)
        self.data_list.grid(row=0, column=0, rowspan=3, sticky="ew", padx=6, pady=6)
        ttk.Button(dframe, text="Add file…", command=self.add_data_file).grid(row=0, column=1, sticky="ew", padx=6, pady=(6, 2))
        ttk.Button(dframe, text="Add folder…", command=self.add_data_folder).grid(row=1, column=1, sticky="ew", padx=6, pady=2)
        ttk.Button(dframe, text="Remove", command=self.remove_data).grid(row=2, column=1, sticky="ew", padx=6, pady=(2, 6))
        ttk.Label(dframe, foreground="#666",
                  text="In your script, load bundled files via:  base = getattr(sys, '_MEIPASS', os.path.abspath('.'))"
                  ).grid(row=3, column=0, columnspan=2, sticky="w", padx=6, pady=(0, 6))

        # ---- Command preview
        pf = ttk.LabelFrame(self.root, text="Command preview")
        pf.pack(fill="x", padx=8, pady=6)
        pe = ttk.Entry(pf, textvariable=self.preview, state="readonly")
        pe.pack(side="left", fill="x", expand=True, padx=6, pady=6)
        ttk.Button(pf, text="Copy", width=7, command=self.copy_preview).pack(side="right", padx=6)

        # ---- Action buttons
        bar = ttk.Frame(self.root)
        bar.pack(fill="x", padx=8)
        self.btn_build = ttk.Button(bar, text="▶  Build EXE", style="Build.TButton", command=self.start_build)
        self.btn_build.pack(side="left", padx=(0, 6))
        self.btn_stop = ttk.Button(bar, text="■ Stop", command=self.stop, state="disabled")
        self.btn_stop.pack(side="left", padx=2)
        self.btn_check = ttk.Button(bar, text="Check setup", command=lambda: self.start_check(False))
        self.btn_check.pack(side="left", padx=2)
        self.btn_install = ttk.Button(bar, text="Install / Update PyInstaller", command=self.start_install)
        self.btn_install.pack(side="left", padx=2)
        self.btn_scan = ttk.Button(bar, text="Scan imports", command=self.start_scan)
        self.btn_scan.pack(side="left", padx=2)

        bar2 = ttk.Frame(self.root)
        bar2.pack(fill="x", padx=8, pady=(4, 0))
        self.btn_open = ttk.Button(bar2, text="Open output folder", command=self.open_output, state="disabled")
        self.btn_open.pack(side="left", padx=(0, 4))
        self.btn_run = ttk.Button(bar2, text="Run EXE", command=self.run_exe, state="disabled")
        self.btn_run.pack(side="left", padx=2)
        ttk.Button(bar2, text="Save log…", command=self.save_log).pack(side="right", padx=2)
        ttk.Button(bar2, text="Clear log", command=lambda: self.log.delete("1.0", tk.END)).pack(side="right", padx=2)

        self.progress = ttk.Progressbar(self.root, mode="indeterminate")
        self.progress.pack(fill="x", padx=8, pady=6)

        # ---- Log
        lf = ttk.Frame(self.root)
        lf.pack(fill="both", expand=True, padx=8, pady=(0, 4))
        self.log = tk.Text(lf, height=12, wrap="none", font=("Consolas", 9), bg="#1e1e1e", fg="#d4d4d4",
                           insertbackground="white")
        ys = ttk.Scrollbar(lf, orient="vertical", command=self.log.yview)
        xs = ttk.Scrollbar(lf, orient="horizontal", command=self.log.xview)
        self.log.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        ys.pack(side="right", fill="y")
        xs.pack(side="bottom", fill="x")
        self.log.pack(fill="both", expand=True)
        self.log.tag_config("plain", foreground="#d4d4d4")
        self.log.tag_config("info", foreground="#4fc1ff")
        self.log.tag_config("warn", foreground="#e5c07b")
        self.log.tag_config("error", foreground="#f48771")
        self.log.tag_config("ok", foreground="#6adf8b")

        ttk.Label(self.root, textvariable=self.status, relief="sunken", anchor="w").pack(fill="x", side="bottom")

        self.refresh_data_list()

    def _row_entry(self, parent, row, label, var, cmd, btn_text, hint=None):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=4)
        e = ttk.Entry(parent, textvariable=var)
        e.grid(row=row, column=1, sticky="ew", padx=4, pady=4)
        if cmd:
            ttk.Button(parent, text=btn_text, command=cmd, width=10).grid(row=row, column=2, padx=8)
        elif hint:
            ttk.Label(parent, text=hint, foreground="#888").grid(row=row, column=2, sticky="w", padx=8)

    # ------------------------------------------------------------- Browsing
    def browse_script(self):
        f = filedialog.askopenfilename(filetypes=[("Python files", "*.py *.pyw"), ("All files", "*.*")])
        if f:
            self.script.set(os.path.normpath(f))

    def browse_outdir(self):
        d = filedialog.askdirectory()
        if d:
            self.outdir.set(os.path.normpath(d))

    def browse_icon(self):
        f = filedialog.askopenfilename(filetypes=[("Icon", "*.ico"), ("All files", "*.*")])
        if f:
            self.icon.set(os.path.normpath(f))

    def browse_interp(self):
        f = filedialog.askopenfilename(title="Select python.exe")
        if f:
            self.interp.set(os.path.normpath(f))

    def add_data_file(self):
        for f in filedialog.askopenfilenames():
            self.data.append((os.path.normpath(f), "."))
        self.refresh_data_list()

    def add_data_folder(self):
        d = filedialog.askdirectory()
        if d:
            self.data.append((os.path.normpath(d), os.path.basename(os.path.normpath(d))))
            self.refresh_data_list()

    def remove_data(self):
        for i in reversed(self.data_list.curselection()):
            del self.data[i]
        self.refresh_data_list()

    def refresh_data_list(self):
        self.data_list.delete(0, tk.END)
        for s, d in self.data:
            self.data_list.insert(tk.END, f"{s}   →   {d}")
        self.update_preview()

    # --------------------------------------------------------- Build command
    def build_spec(self):
        script = self.script.get().strip().strip('"')
        if not script:
            raise ValueError("Select a Python file.")
        script = os.path.abspath(script)
        if not os.path.isfile(script):
            raise ValueError(f"File not found:\n{script}")
        cwd = os.path.dirname(script)
        stem = os.path.splitext(os.path.basename(script))[0]
        name = self.name.get().strip() or stem
        outdir = os.path.abspath(self.outdir.get().strip() or os.path.join(cwd, "dist"))
        py = self.interp.get().strip() or find_python()
        if not py:
            raise ValueError("No Python interpreter found. Set one under Advanced.")

        cmd = [py, "-m", "PyInstaller", "--noconfirm"]
        if self.clean.get():
            cmd.append("--clean")
        cmd.append("--onefile" if self.onefile.get() else "--onedir")
        cmd.append("--windowed" if self.windowed.get() else "--console")
        cmd += ["--name", name, "--distpath", outdir,
                "--workpath", os.path.join(cwd, "build"), "--specpath", cwd]

        icon = self.icon.get().strip().strip('"')
        if icon:
            if not os.path.isfile(icon):
                raise ValueError(f"Icon not found:\n{icon}")
            cmd += ["--icon", icon]
        if self.admin.get():
            cmd.append("--uac-admin")
        for h in self.hidden.get().replace(";", ",").replace(" ", ",").split(","):
            if h.strip():
                cmd += ["--hidden-import", h.strip()]
        for s, d in self.data:
            cmd += ["--add-data", f"{s}{os.pathsep}{d}"]
        extra = self.extra.get().strip()
        if extra:
            cmd += shlex.split(extra, posix=(os.name != "nt"))
        cmd.append(script)

        exe = os.path.join(outdir, name + EXE_EXT) if self.onefile.get() \
            else os.path.join(outdir, name, name + EXE_EXT)
        return cmd, cwd, exe, outdir

    def update_preview(self):
        try:
            cmd = self.build_spec()[0]
            self.preview.set(subprocess.list2cmdline(cmd))
        except ValueError as e:
            self.preview.set("(" + str(e).splitlines()[0] + ")")

    def copy_preview(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.preview.get())
        self.status.set("Command copied to clipboard")

    # ------------------------------------------------------------- Logging
    def write(self, text, tag="plain"):
        self.log.insert(tk.END, text, tag)
        self.log.see(tk.END)

    def say(self, text, tag="info"):
        self.q.put(("log", text, tag))

    def save_log(self):
        f = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text", "*.txt")])
        if f:
            with open(f, "w", encoding="utf-8") as fh:
                fh.write(self.log.get("1.0", tk.END))

    # ------------------------------------------------------ Process control
    def set_running(self, flag, status=None):
        self.running = flag
        st = "disabled" if flag else "normal"
        for b in (self.btn_build, self.btn_check, self.btn_install, self.btn_scan):
            b.config(state=st)
        self.btn_stop.config(state="normal" if flag else "disabled")
        if flag:
            self.progress.start(12)
        else:
            self.progress.stop()
        if status:
            self.status.set(status)

    def stream(self, cmd, cwd=None):
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
        self.proc = subprocess.Popen(
            cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding="utf-8", errors="replace", creationflags=NO_WINDOW, env=env)
        for line in self.proc.stdout:
            self.buf.append(line)
            self.q.put(("log", line, classify(line)))
        return self.proc.wait()

    def stop(self):
        self.cancelled = True
        p = self.proc
        if p and p.poll() is None:
            try:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)],
                                   capture_output=True, creationflags=NO_WINDOW)
                else:
                    p.terminate()
            except Exception:  # noqa: BLE001
                pass

    def begin(self, status):
        self.cancelled = False
        self.buf = []
        self.set_running(True, status)

    # --------------------------------------------------------------- Actions
    def start_build(self):
        try:
            cmd, cwd, exe, outdir = self.build_spec()
        except ValueError as e:
            messagebox.showerror("Cannot build", str(e))
            return
        self.log.delete("1.0", tk.END)
        self.begin("Building…")
        threading.Thread(target=self.build_worker, args=(cmd, cwd, exe, outdir), daemon=True).start()

    def build_worker(self, cmd, cwd, exe, outdir):
        ok = False
        t0 = time.time()
        try:
            py = cmd[0]
            rc, out = run_quiet([py, "-c", "import PyInstaller;print(PyInstaller.__version__)"], 30)
            if rc != 0:
                self.say("PyInstaller is not available for:\n  " + py + "\n", "error")
                self.q.put(("ask_install", None, None))
                return
            self.say(f"Python: {py}\nPyInstaller: {out.strip()}\n", "info")
            self.say("$ " + subprocess.list2cmdline(cmd) + "\n\n", "info")
            rc = self.stream(cmd, cwd)
            if self.cancelled:
                self.say("\nBuild cancelled.\n", "warn")
            elif rc == 0:
                if os.path.isfile(exe):
                    ok = True
                    self.say(f"\n✔ Done in {time.time() - t0:.1f}s\n  {exe}\n", "ok")
                else:
                    self.say("\n⚠ PyInstaller reported success but the EXE is missing:\n  " + exe +
                             "\n  Most likely your antivirus (e.g. Windows Defender) quarantined it.\n"
                             "  Add the output folder to its exclusions and build again.\n", "warn")
            else:
                self.say(f"\n✘ Build failed (exit code {rc})\n", "error")
                hints = diagnose("".join(self.buf))
                if hints:
                    self.say("\nLikely fixes:\n", "warn")
                    for h in hints:
                        self.say("  • " + h + "\n", "warn")
        except FileNotFoundError:
            self.say("\nInterpreter not found:\n  " + cmd[0] + "\nPick a valid python.exe under Advanced.\n", "error")
        except Exception as e:  # noqa: BLE001
            self.say(f"\nUnexpected error: {e}\n", "error")
        finally:
            self.q.put(("done", ("build", ok, exe, outdir), None))

    def start_check(self, silent=False):
        if self.running:
            return
        self.begin("Checking setup…")
        threading.Thread(target=self.check_worker, args=(silent,), daemon=True).start()

    def check_worker(self, silent):
        py = self.interp.get().strip() or find_python()
        try:
            rc, out = run_quiet([py, "-c",
                                 "import sys;print(sys.version.split()[0])"], 20)
            if rc != 0:
                self.say(f"✘ Interpreter problem: {py}\n{out}\n", "error")
                return
            pyv = out.strip()
            rc2, out2 = run_quiet([py, "-c", "import PyInstaller;print(PyInstaller.__version__)"], 30)
            if rc2 == 0:
                self.say(f"✔ Python {pyv}  |  PyInstaller {out2.strip()}  |  {py}\n", "ok")
            else:
                self.say(f"Python {pyv} found, but PyInstaller is NOT installed for it.\n"
                         "→ Click 'Install / Update PyInstaller'.\n", "warn")
        finally:
            self.q.put(("done", ("check", True, "", ""), None))

    def start_install(self):
        self.begin("Installing PyInstaller…")
        threading.Thread(target=self.install_worker, daemon=True).start()

    def install_worker(self):
        ok = False
        py = self.interp.get().strip() or find_python()
        cmd = [py, "-m", "pip", "install", "--upgrade", "pyinstaller"]
        try:
            self.say("$ " + subprocess.list2cmdline(cmd) + "\n\n", "info")
            rc = self.stream(cmd)
            ok = rc == 0 and not self.cancelled
            self.say("\n✔ PyInstaller ready.\n" if ok else f"\n✘ pip failed (exit code {rc}).\n",
                     "ok" if ok else "error")
        except Exception as e:  # noqa: BLE001
            self.say(f"\nInstall error: {e}\n", "error")
        finally:
            self.q.put(("done", ("install", ok, "", ""), None))

    def start_scan(self):
        try:
            script = os.path.abspath(self.script.get().strip().strip('"'))
            if not os.path.isfile(script):
                raise ValueError("Select a Python file first.")
        except ValueError as e:
            messagebox.showerror("Scan imports", str(e))
            return
        self.begin("Scanning imports…")
        threading.Thread(target=self.scan_worker, args=(script,), daemon=True).start()

    def scan_worker(self, script):
        py = self.interp.get().strip() or find_python()
        try:
            mods = top_level_imports(script)
            folder = os.path.dirname(script)
            local = {m for m in mods if os.path.isfile(os.path.join(folder, m + ".py"))
                     or os.path.isdir(os.path.join(folder, m))}
            cand = sorted(mods - local)
            code = ("import importlib.util as u,sys\n"
                    "for m in sys.argv[1:]:\n"
                    "    try:\n        f=u.find_spec(m)\n"
                    "    except Exception:\n        f=None\n"
                    "    if f is None: print(m)\n")
            rc, out = run_quiet([py, "-c", code, *cand], 60)
            missing = [m for m in out.split() if m] if rc == 0 else []
            self.say(f"Found {len(mods)} imported modules ({len(local)} local).\n", "info")
            if missing:
                self.say("Not installed for the selected interpreter (the EXE would break):\n", "warn")
                for m in missing:
                    self.say(f"  pip install {PIP_NAMES.get(m, m)}\n", "warn")
            else:
                self.say("✔ All imports can be resolved.\n", "ok")
        except SyntaxError as e:
            self.say(f"Syntax error in script – fix it before building: {e}\n", "error")
        except Exception as e:  # noqa: BLE001
            self.say(f"Scan failed: {e}\n", "error")
        finally:
            self.q.put(("done", ("scan", True, "", ""), None))

    # ---------------------------------------------------------- Post actions
    def open_output(self):
        if self.last_outdir and os.path.isdir(self.last_outdir):
            open_path(self.last_outdir)

    def run_exe(self):
        if self.last_exe and os.path.isfile(self.last_exe):
            try:
                subprocess.Popen([self.last_exe], cwd=os.path.dirname(self.last_exe))
            except Exception as e:  # noqa: BLE001
                messagebox.showerror("Run failed", str(e))

    # ------------------------------------------------------ Queue (UI thread)
    def poll(self):
        try:
            while True:
                kind, a, b = self.q.get_nowait()
                if kind == "log":
                    self.write(a, b)
                elif kind == "ask_install":
                    if messagebox.askyesno("PyInstaller missing",
                                           "PyInstaller isn't installed for this interpreter.\n\n"
                                           "Install it now and then build?"):
                        self.build_after_install = True
                elif kind == "done":
                    self.on_done(*a)
        except queue.Empty:
            pass
        self.root.after(80, self.poll)

    def on_done(self, action, ok, exe, outdir):
        self.proc = None
        self.set_running(False)
        if action == "build":
            if ok:
                self.last_exe, self.last_outdir = exe, outdir
                self.btn_open.config(state="normal")
                self.btn_run.config(state="normal")
                self.status.set("Build succeeded")
                self.save_settings()
                if messagebox.askyesno("Success", f"EXE created:\n{exe}\n\nOpen the output folder?"):
                    open_path(outdir)
            else:
                self.status.set("Build did not produce an EXE – see log")
                if self.build_after_install:
                    self.start_install()
                    return
        elif action == "install":
            self.status.set("PyInstaller ready" if ok else "Install failed")
            if ok and self.build_after_install:
                self.build_after_install = False
                self.start_build()
                return
            self.build_after_install = False
        else:
            self.status.set("Ready")

    # --------------------------------------------------------------- Settings
    def load_settings(self):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                s = json.load(f)
            self.onefile.set(s.get("onefile", True))
            self.windowed.set(s.get("windowed", False))
            self.clean.set(s.get("clean", True))
            self.admin.set(s.get("admin", False))
            if s.get("interp") and os.path.isfile(s["interp"]):
                self.interp.set(s["interp"])
        except Exception:  # noqa: BLE001
            pass

    def save_settings(self):
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump({"onefile": self.onefile.get(), "windowed": self.windowed.get(),
                           "clean": self.clean.get(), "admin": self.admin.get(),
                           "interp": self.interp.get()}, f, indent=2)
        except Exception:  # noqa: BLE001
            pass

    def on_close(self):
        if self.running:
            if not messagebox.askyesno("Quit", "A task is still running. Stop it and quit?"):
                return
            self.stop()
        self.save_settings()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
