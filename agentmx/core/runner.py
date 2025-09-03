import os
import time
from loguru import logger
from typing import Optional
from agentmx.safety.runner import StopFileGuard
from agentmx.safety.policy import SafetyPolicy
from agentmx.safety.audit import AuditLog
from agentmx.exec.sandbox import Sandbox
from agentmx.skills.registry import SkillRegistry

class AgentRunner:
    def __init__(self, config, run_id: str, net_enabled: bool, allow_safety_edit: bool):
        self.config = config
        self.run_id = run_id
        self.net_enabled = net_enabled
        self.allow_safety_edit = allow_safety_edit
        self.workdir = os.path.abspath(self.config.get("execution.working_dir", f".agentmx/work/{run_id}").format(run_id=run_id))
        os.makedirs(self.workdir, exist_ok=True)
        self.stop_guard = StopFileGuard(self.config.get("execution.kill_switch_file", ".agentmx/STOP"))
        self.policy = SafetyPolicy()
        self.audit = AuditLog(self.workdir)
        self.sandbox = Sandbox(self.stop_guard, self.audit)
        self.skills = SkillRegistry(max_new=self.config.get("skills.max_new_skill_per_run", 1))

    def execute(self, task: str, timeout: int = 3600) -> bool:
        start = time.time()
        self.audit.record("run_start", {"task": task, "run_id": self.run_id})
        try:
            self.audit.record("plan", {"step": "initial", "task": task})
            while time.time() - start < min(3, timeout):
                self.stop_guard.check()
                time.sleep(0.2)
            self.audit.record("run_end", {"status": "success"})
            return True
        except StopFileGuard.Stopped:
            self.audit.record("run_end", {"status": "stopped"})
            return False
        except Exception as e:
            logger.exception(e)
            self.audit.record("run_end", {"status": "error", "error": str(e)})
            return False
