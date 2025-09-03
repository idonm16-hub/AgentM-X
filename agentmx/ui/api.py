import os
import uuid
import threading
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from agentmx.core.config import load_config
from agentmx.core.runner import AgentRunner

app = FastAPI()
cfg = load_config()
API_KEY_ENV = "AGENTMX_API_KEY"
RUNS = {}

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
    RUNS[run_id] = {"task": task, "status": "running"}
    return JSONResponse({"accepted": True, "run_id": run_id, "task": task})
