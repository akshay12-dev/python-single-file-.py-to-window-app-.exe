import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import threading
import sys
import os
import queue


class ExeConverter:

    def __init__(self, root):
        self.root = root
        self.root.title("Python to EXE Converter")
        self.root.geometry("600x400")

        tk.Label(root, text="Python File").pack(pady=5)

        self.file_entry = tk.Entry(root, width=60)
        self.file_entry.pack()

        tk.Button(root, text="Browse", command=self.select_file).pack(pady=5)

        self.onefile = tk.BooleanVar(value=True)
        self.windowed = tk.BooleanVar(value=False)

        tk.Checkbutton(root, text="One File", variable=self.onefile).pack()
        tk.Checkbutton(root, text="No Console (Windowed)", variable=self.windowed).pack()

        self.convert_button = tk.Button(
            root,
            text="Convert to EXE",
            bg="green",
            fg="white",
            command=self.start_conversion
        )
        self.convert_button.pack(pady=10)

        self.log = tk.Text(root, height=12)
        self.log.pack(fill="both", expand=True)

        # Queue used to safely pass output lines from the worker thread
        # back to the main thread (Tkinter widgets aren't thread-safe).
        self.log_queue = queue.Queue()
        self.root.after(100, self.poll_log_queue)

    def select_file(self):
        file = filedialog.askopenfilename(
            filetypes=[("Python Files", "*.py")]
        )

        if file:
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, file)

    def start_conversion(self):
        py_file = self.file_entry.get().strip()

        if not py_file:
            messagebox.showerror("Error", "Select a Python file.")
            return

        if not os.path.isfile(py_file):
            messagebox.showerror("Error", f"File not found:\n{py_file}")
            return

        self.log.delete(1.0, tk.END)
        self.convert_button.config(state="disabled", text="Converting...")

        threading.Thread(target=self.convert, args=(py_file,), daemon=True).start()

    def convert(self, py_file):
        try:
            py_file = os.path.abspath(py_file)
            work_dir = os.path.dirname(py_file)

            # Use "python -m PyInstaller" instead of relying on a bare
            # "pyinstaller" command being on PATH. This uses the exact
            # same interpreter that's running this GUI, which is the
            # most reliable way to find a pip-installed PyInstaller —
            # especially important since IDLE's PATH environment can
            # differ from a normal terminal's.
            command = [sys.executable, "-m", "PyInstaller"]

            if self.onefile.get():
                command.append("--onefile")

            if self.windowed.get():
                command.append("--windowed")

            command.append(py_file)

            self.log_queue.put(f"Running: {' '.join(command)}\n")
            self.log_queue.put(f"Working directory: {work_dir}\n\n")

            process = subprocess.Popen(
                command,
                cwd=work_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            for line in process.stdout:
                self.log_queue.put(line)

            process.wait()

            if process.returncode == 0:
                self.log_queue.put("\nDone!\n")
                dist_path = os.path.join(work_dir, "dist")
                self.log_queue.put(("success", dist_path))
            else:
                self.log_queue.put(f"\nFailed! (exit code {process.returncode})\n")
                self.log_queue.put(("error", "PyInstaller exited with an error. See log above."))

        except FileNotFoundError:
            self.log_queue.put(
                "\nERROR: Could not find PyInstaller for this Python interpreter.\n"
                f"Interpreter: {sys.executable}\n\n"
                "Fix: install PyInstaller for this exact interpreter by running:\n"
                f'  "{sys.executable}" -m pip install pyinstaller\n'
            )
            self.log_queue.put(("error", "PyInstaller is not installed for this Python interpreter."))
        except Exception as e:
            self.log_queue.put(f"\nUnexpected error: {e}\n")
            self.log_queue.put(("error", str(e)))
        finally:
            self.log_queue.put(("done", None))

    def poll_log_queue(self):
        """Runs on the main thread; safely drains queued messages into the Text widget."""
        try:
            while True:
                item = self.log_queue.get_nowait()

                if isinstance(item, tuple):
                    kind, payload = item
                    if kind == "success":
                        self.convert_button.config(state="normal", text="Convert to EXE")
                        messagebox.showinfo(
                            "Success",
                            f"EXE created inside:\n{payload}"
                        )
                    elif kind == "error":
                        self.convert_button.config(state="normal", text="Convert to EXE")
                        messagebox.showerror("Conversion Failed", payload)
                    elif kind == "done":
                        self.convert_button.config(state="normal", text="Convert to EXE")
                else:
                    self.log.insert(tk.END, item)
                    self.log.see(tk.END)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.poll_log_queue)


if __name__ == "__main__":
    root = tk.Tk()
    app = ExeConverter(root)
    root.mainloop()
