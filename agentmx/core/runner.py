import os
import json
import time
from datetime import datetime
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
        self.downloads_dir = os.path.abspath(self.config.get("browser.downloads_dir", f".agentmx/work/{run_id}/browser").format(run_id=run_id))
        os.makedirs(self.downloads_dir, exist_ok=True)
        self.status_path = os.path.join(self.workdir, "status.json")
        self.artifacts_path = os.path.join(self.workdir, "artifacts.json")
        self._write_json(self.status_path, {"status": "initialized", "run_id": self.run_id})
        self._write_json(self.artifacts_path, [])
        self.stop_guard = StopFileGuard(self.config.get("execution.kill_switch_file", ".agentmx/STOP"))
        self.policy = SafetyPolicy()
        self.audit = AuditLog(self.workdir)
        self.sandbox = Sandbox(self.stop_guard, self.audit)
        self.skills = SkillRegistry(max_new=self.config.get("skills.max_new_skill_per_run", 1))

    def _write_json(self, path: str, obj):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f)

    def _read_json(self, path: str, default):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default

    def set_status(self, status: str, extra: Optional[dict] = None):
        data = {"status": status, "run_id": self.run_id}
        if extra:
            data.update(extra)
        self._write_json(self.status_path, data)

    def add_artifact(self, path: str, kind: str = "file"):
        try:
            path_abs = os.path.abspath(path)
            meta = {
                "path": path_abs,
                "type": kind,
                "size": os.path.getsize(path_abs) if os.path.exists(path_abs) else 0,
                "created_at": datetime.utcnow().isoformat() + "Z",
            }
            arr = self._read_json(self.artifacts_path, [])
            arr.append(meta)
            self._write_json(self.artifacts_path, arr)
            return meta
        except Exception as e:
            logger.exception(e)
            return {"path": path, "type": kind, "error": str(e)}

    def execute(self, task: str, timeout: int = 3600) -> bool:
        start = time.time()
        self.audit.record("run_start", {"task": task, "run_id": self.run_id})
        self.set_status("running", {"task": task})
        try:
            self.audit.record("plan", {"step": "initial", "task": task})
            while time.time() - start < min(3, timeout):
                self.stop_guard.check()
                time.sleep(0.2)
            self.audit.record("run_end", {"status": "success"})
            self.set_status("success")
            return True
        except StopFileGuard.Stopped:
            self.audit.record("run_end", {"status": "stopped"})
            self.set_status("stopped")
            return False
        except Exception as e:
            logger.exception(e)
            self.audit.record("run_end", {"status": "error", "error": str(e)})
            self.set_status("error", {"error": str(e)})
            return False
