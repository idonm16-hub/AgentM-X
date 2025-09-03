import os
import sys
import time
import subprocess
from typing import Optional

IS_WINDOWS = os.name == "nt"

if IS_WINDOWS:
    from pywinauto.application import Application
    from pywinauto.keyboard import send_keys
else:
    Application = None
    send_keys = None

class NotepadSkill:
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self.app = None
        self.edit = None
        self.window = None

    def open(self):
        if not IS_WINDOWS:
            raise RuntimeError("NotepadSkill works only on Windows")
        try:
            self.app = Application(backend="uia").start("notepad.exe")
            self.window = self.app.window(title_re=".*Notepad")
            self.window.wait("visible", timeout=self.timeout)
            self.edit = self.window.child_window(control_type="Edit")
            self.edit.wait("ready", timeout=self.timeout)
        except Exception:
            raise

    def type_text(self, text: str):
        if not IS_WINDOWS:
            raise RuntimeError("NotepadSkill works only on Windows")
        if self.edit is None:
            raise RuntimeError("Notepad not opened")
        try:
            self.edit.type_keys(text, with_spaces=True, pause=0.02)
        except Exception:
            if send_keys:
                send_keys(text)

    def save_as(self, path: str):
        if not IS_WINDOWS:
            raise RuntimeError("NotepadSkill works only on Windows")
        if self.window is None:
            raise RuntimeError("Notepad not opened")
        try:
            send_keys("^s")
            time.sleep(0.5)
            dlg = self.app.window(title_re=".*Notepad")
            file_name = dlg.child_window(auto_id="1001", control_type="Edit")
            file_name.wait("exists", timeout=self.timeout)
            file_name.set_edit_text(path)
            save_btn = dlg.child_window(title="Save", control_type="Button")
            if not save_btn.exists():
                save_btn = dlg.child_window(title="Save", control_type="SplitButton")
            save_btn.wait("enabled", timeout=self.timeout)
            save_btn.click()
            time.sleep(0.5)
            if self.app.window(title_re="Confirm Save As").exists():
                self.app.window(title_re="Confirm Save As").child_window(title="Yes", control_type="Button").click()
        except Exception:
            raise

    def close(self):
        if not IS_WINDOWS:
            return
        if self.window is not None:
            try:
                self.window.close()
                time.sleep(0.2)
                if self.app.window(title_re="Notepad").exists():
                    try:
                        self.app.window(title_re="Notepad").child_window(title="Don't Save", control_type="Button").click()
                    except Exception:
                        pass
            except Exception:
                pass
