import os
import time

class StopFileGuard:
    class Stopped(Exception):
        pass

    def __init__(self, stop_path: str):
        self.stop_path = stop_path

    def check(self):
        if os.path.exists(self.stop_path):
            raise StopFileGuard.Stopped()
