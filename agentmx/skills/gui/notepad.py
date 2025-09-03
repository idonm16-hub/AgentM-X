import os
import time
from typing import Optional

IS_WINDOWS = os.name == "nt"

if IS_WINDOWS:
    from pywinauto.application import Application
    from pywinauto.keyboard import send_keys
    try:
        import pyautogui
    except Exception:
        pyautogui = None
else:
    Application = None
    send_keys = None
    pyautogui = None

def desktop_default_path(filename: str = "agentmx-note.txt") -> str:
    if not IS_WINDOWS:
        raise RuntimeError("Desktop path resolution is Windows-only here")
    from pathlib import Path
    return str(Path.home() / "Desktop" / filename)

class NotepadSkill:
    def __init__(self, timeout: float = 10.0, stop_guard: Optional[object] = None):
        self.timeout = timeout
        self.app = None
        self.edit = None
        self.window = None
        self.stop_guard = stop_guard

    def _check_stop(self):
        if self.stop_guard:
            self.stop_guard.check()

    def open(self):
        if not IS_WINDOWS:
            raise RuntimeError("NotepadSkill works only on Windows")
        self._check_stop()
        self.app = Application(backend="uia").start("notepad.exe")
        self.window = self.app.window(title_re=".*Notepad")
        self.window.wait("visible", timeout=self.timeout)
        self._check_stop()
        self.edit = self.window.child_window(control_type="Edit")
        self.edit.wait("ready", timeout=self.timeout)

    def type_text(self, text: str):
        if not IS_WINDOWS:
            raise RuntimeError("NotepadSkill works only on Windows")
        if self.edit is None:
            raise RuntimeError("Notepad not opened")
        self._check_stop()
        try:
            self.edit.type_keys(text, with_spaces=True, pause=0.02)
        except Exception:
            if pyautogui:
                pyautogui.typewrite(text, interval=0.02)
            elif send_keys:
                send_keys(text)
        self._check_stop()

    def save_as(self, path: Optional[str] = None):
        if not IS_WINDOWS:
            raise RuntimeError("NotepadSkill works only on Windows")
        if self.window is None:
            raise RuntimeError("Notepad not opened")
        if not path:
            path = desktop_default_path()
        self._check_stop()
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
        self._check_stop()
        save_btn.click()
        time.sleep(0.5)
        if self.app.window(title_re="Confirm Save As").exists():
            self.app.window(title_re="Confirm Save As").child_window(title="Yes", control_type="Button").click()
        self._check_stop()
        return path

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
