import time
from typing import Dict, Any, List, Optional
from agentmx.core.runner import AgentRunner

def execute_steps(cfg, steps: List[Dict[str, Any]], run_id: Optional[str] = None) -> Dict[str, Any]:
    results = {}
    for i, st in enumerate(steps):
        act = st.get("action")
        if act == "run_demo":
            rid = run_id or results.get("run_id")
            if not rid:
                import uuid as _uuid
                rid = _uuid.uuid4().hex
            r = AgentRunner(cfg, run_id=rid, net_enabled=True, allow_safety_edit=False)
            results["run_id"] = r.run_id
            ok = r.execute("demo", timeout=3600)
            results[f"step_{i}"] = {"ok": ok, "workdir": r.workdir}
        elif act == "noop":
            seconds = int(st.get("args", {}).get("seconds", 1))
            time.sleep(seconds)
            results[f"step_{i}"] = {"ok": True}
        else:
            results[f"step_{i}"] = {"ok": False, "error": f"unknown action {act}"}
    return results
