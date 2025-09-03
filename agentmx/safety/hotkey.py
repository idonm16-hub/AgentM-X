import os
import threading
import platform

IS_WINDOWS = platform.system() == "Windows"

class HotkeyStopper:
    def __init__(self, stop_path: str):
        self.stop_path = stop_path
        self._t = None

    def start(self):
        if not IS_WINDOWS:
            return
        try:
            import keyboard
        except Exception:
            return
        def loop():
            keyboard.add_hotkey("ctrl+alt+s", lambda: open(self.stop_path, "w").close())
            keyboard.wait()
        self._t = threading.Thread(target=loop, daemon=True)
        self._t.start()

    def stop(self):
        pass
