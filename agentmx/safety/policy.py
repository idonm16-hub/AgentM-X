from typing import List

class SafetyPolicy:
    def __init__(self):
        self.deny = [
            "format",
            "cipher /w",
            "rm -rf",
            "diskpart",
            "reg delete HKLM\\SYSTEM",
            "shutdown /f",
        ]

    def is_denied(self, command: str) -> bool:
        c = (command or "").lower()
        return any(pat in c for pat in (s.lower() for s in self.deny))
