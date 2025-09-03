import time
from agentmx.safety.runner import StopFileGuard
from agentmx.safety.audit import AuditLog

class Sandbox:
    def __init__(self, stop_guard: StopFileGuard, audit: AuditLog):
        self.stop_guard = stop_guard
        self.audit = audit

    def loop(self, seconds: float):
        end = time.time() + seconds
        while time.time() < end:
            self.stop_guard.check()
            time.sleep(0.2)
