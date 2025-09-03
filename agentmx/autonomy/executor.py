import time
from typing import Dict, Any, List
from agentmx.core.runner import AgentRunner

def execute_steps(cfg, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
    results = {}
    for i, st in enumerate(steps):
        act = st.get("action")
        if act == "run_demo":
            r = AgentRunner(cfg, run_id=results.get("run_id") or __import__("uuid").uuid4().hex, net_enabled=True, allow_safety_edit=False)
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
