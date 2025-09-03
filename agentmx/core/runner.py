import os
import json
import time
import sys
import hashlib
import mimetypes
from datetime import datetime, UTC
from loguru import logger
from typing import Optional
from agentmx.safety.runner import StopFileGuard
from agentmx.safety.policy import SafetyPolicy
from agentmx.safety.audit import AuditLog
from agentmx.exec.sandbox import Sandbox
from agentmx.skills.registry import SkillRegistry
from agentmx.memory import store as mem

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
            size = os.path.getsize(path_abs) if os.path.exists(path_abs) else 0
            sha256 = None
            if os.path.exists(path_abs):
                h = hashlib.sha256()
                with open(path_abs, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        h.update(chunk)
                sha256 = h.hexdigest()
            mime, _ = mimetypes.guess_type(path_abs)
            meta = {
                "path": path_abs,
                "type": kind,
                "size": size,
                "sha256": sha256,
                "mime": mime or "application/octet-stream",
                "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "name": os.path.basename(path_abs),
            }
            arr = self._read_json(self.artifacts_path, [])
            arr.append(meta)
            self._write_json(self.artifacts_path, arr)
            try:
                conn = mem.connect()
                mem.add_artifact(conn, self.run_id, {
                    "path": meta["path"],
                    "name": meta["name"],
                    "size": meta["size"],
                    "sha256": meta["sha256"],
                    "mime": meta["mime"],
                })
                mem.commit(conn)
            except Exception:
                pass
            return meta
        except Exception as e:
            logger.exception(e)
            return {"path": path, "type": kind, "error": str(e)}

    def execute(self, task: str, timeout: int = 3600) -> bool:
        start = time.time()
        self.audit.record("run_start", {"task": task, "run_id": self.run_id})
        try:
            try:
                conn = mem.connect()
                mem.record_run(conn, self.run_id, "running", 0.0, 0.0)
            except Exception:
                pass
            self.set_status("running", {"task": task})
            self.audit.record("plan", {"step": "initial", "task": task})
            if (task or "") == "demo":
                self.stop_guard.check()
                note_path = None
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                os.makedirs(desktop, exist_ok=True)
                note_path = os.path.join(desktop, "notepad_output.txt")
                if sys.platform.startswith("win"):
                    NoteCls = self.skills.notepad()
                    note = NoteCls()
                    note.open()
                    note.type_text("hello from agentmx")
                    note.save_as(note_path)
                    note.close()
                else:
                    with open(note_path, "w", encoding="utf-8") as f:
                        f.write("hello from agentmx")
                self.add_artifact(note_path, "note")
                self.stop_guard.check()
                BrowserCls = self.skills.browser_upload_receipt()
                br = BrowserCls(self.downloads_dir)
                res = br.run(note_path)
                self.add_artifact(res["path"], "receipt")
            else:
                while time.time() - start < min(3, timeout):
                    self.stop_guard.check()
                    time.sleep(0.2)
            self.audit.record("run_end", {"status": "completed"})
            try:
                conn = mem.connect()
                duration = max(0.0, time.time() - start)
                mem.record_run(conn, self.run_id, "completed", duration, 1.0)
            except Exception:
                pass
            self.set_status("completed")
            return True
        except StopFileGuard.Stopped:
            self.audit.record("run_end", {"status": "aborted"})
            try:
                conn = mem.connect()
                duration = max(0.0, time.time() - start)
                mem.record_run(conn, self.run_id, "aborted", duration, 0.0)
            except Exception:
                pass
            self.set_status("aborted")
            return False
        except Exception as e:
            logger.exception(e)
            self.audit.record("run_end", {"status": "failed", "error": str(e)})
            try:
                conn = mem.connect()
                duration = max(0.0, time.time() - start)
                mem.record_run(conn, self.run_id, "failed", duration, 0.0)
            except Exception:
                pass
            self.set_status("failed", {"error": str(e)})
            return False
