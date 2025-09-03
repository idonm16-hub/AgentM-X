import os
import uuid
import json
import threading
from typing import Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from agentmx.core.config import load_config
from agentmx.core.runner import AgentRunner

app = FastAPI()
cfg = load_config()
API_KEY_ENV = "AGENTMX_API_KEY"
RUNS = {}

def run_paths(run_id: Optional[str] = None):
    base = None
    if run_id:
        base = os.path.abspath(cfg.get("execution.working_dir", f".agentmx/work/{run_id}").format(run_id=run_id))
    return {
        "workdir": base,
        "status": os.path.join(base, "status.json") if base else None,
        "artifacts": os.path.join(base, "artifacts.json") if base else None,
        "audit": os.path.join(base, "audit.log") if base else None,
    }

@app.middleware("http")
async def api_key_guard(request: Request, call_next):
    require_key = cfg.get("approvals.api_key_required", True)
    if require_key:
        key = request.headers.get("X-API-Key")
        expected = os.environ.get(API_KEY_ENV)
        if not expected or key != expected:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    return await call_next(request)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/run")
async def run_task(payload: dict):
    task = payload.get("task")
    if not task:
        raise HTTPException(400, "task required")
    run_id = str(uuid.uuid4())
    runner = AgentRunner(cfg, run_id=run_id, net_enabled=True, allow_safety_edit=False)
    t = threading.Thread(target=runner.execute, args=(task,), kwargs={"timeout": 3600}, daemon=True)
    t.start()
    RUNS[run_id] = {"task": task, "workdir": runner.workdir}
    return JSONResponse({"accepted": True, "run_id": run_id, "task": task})

@app.get("/runs/{run_id}/status")
async def run_status(run_id: str):
    info = RUNS.get(run_id)
    if not info:
        raise HTTPException(404, "run not found")
    p = run_paths(run_id)
    try:
        with open(p["status"], "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {"status": "unknown", "run_id": run_id}
    return data

@app.get("/runs/{run_id}/logs")
async def run_logs(run_id: str):
    info = RUNS.get(run_id)
    if not info:
        raise HTTPException(404, "run not found")
    p = run_paths(run_id)
    try:
        with open(p["audit"], "r", encoding="utf-8") as f:
            lines = f.read()
        return PlainTextResponse(lines)
    except Exception:
        return PlainTextResponse("")

@app.get("/runs/{run_id}/artifacts")
async def run_artifacts(run_id: str):
    info = RUNS.get(run_id)
    if not info:
        raise HTTPException(404, "run not found")
    p = run_paths(run_id)
    try:
        with open(p["artifacts"], "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = []
    return {"artifacts": data}
