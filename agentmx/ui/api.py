import os
import sys
import uuid
import json
import mimetypes
import threading
import asyncio
from typing import Optional
from loguru import logger
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse, FileResponse, StreamingResponse
from agentmx.core.config import load_config
from agentmx.core.runner import AgentRunner
from agentmx.memory import store as mem

app = FastAPI()
cfg = load_config()
API_KEY_ENV = "AGENTMX_API_KEY"
RUNS = {}
HOTKEY_THREAD = None

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

@app.on_event("startup")
async def _startup():
    global HOTKEY_THREAD
    stop_path = cfg.get("execution.kill_switch_file", ".agentmx/STOP")
    if sys.platform.startswith("win"):
        try:
            from agentmx.safety.hotkey import start_hotkey
            HOTKEY_THREAD = start_hotkey(stop_path)
            if not HOTKEY_THREAD:
                logger.warning("Windows hotkey not started: start_hotkey returned None")
        except Exception as e:
            HOTKEY_THREAD = None
            logger.warning(f"Windows hotkey not available: {e}")

@app.on_event("shutdown")
async def _shutdown():
    global HOTKEY_THREAD
    if HOTKEY_THREAD and hasattr(HOTKEY_THREAD, "stop"):
        try:
            HOTKEY_THREAD.stop()
        except Exception:
            pass

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

@app.get("/runs/{run_id}/logs/stream")
async def run_logs_stream(run_id: str, request: Request):
    if RUNS.get(run_id) is None:
        raise HTTPException(404, "run not found")
    async def _sse_gen():
        p = run_paths(run_id)
        path = p["audit"]
        pos = 0
        last_ping = 0.0
        try:
            with open(path, "r", encoding="utf-8") as f:
                f.seek(0, os.SEEK_END)
                pos = f.tell()
        except Exception:
            pos = 0
        while True:
            if await request.is_disconnected():
                break
            try:
                with open(path, "r", encoding="utf-8") as f:
                    f.seek(pos)
                    for line in f:
                        pos = f.tell()
                        yield f"data: {line.rstrip()}\n\n"
            except Exception:
                pass
            try:
                with open(p["status"], "r", encoding="utf-8") as sf:
                    st = (json.load(sf) or {}).get("status", "unknown")
            except Exception:
                st = "unknown"
            now = asyncio.get_event_loop().time()
            if now - last_ping >= 12.0:
                yield "event: ping\ndata: {}\n\n"
                last_ping = now
            if st in ("success", "stopped", "error"):
                break
            await asyncio.sleep(0.2)
    return StreamingResponse(_sse_gen(), media_type="text/event-stream")

@app.get("/metrics")
async def metrics():
    conn = mem.connect()
    return mem.metrics(conn)


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

@app.get("/runs/{run_id}/artifact/{name}")
async def run_artifact_download(run_id: str, name: str):
    info = RUNS.get(run_id)
    if not info:
        raise HTTPException(404, "run not found")
    if ".." in name or "/" in name or "\\" in name:
        raise HTTPException(400, "invalid artifact name")
    p = run_paths(run_id)
    try:
        with open(p["artifacts"], "r", encoding="utf-8") as f:
            arr = json.load(f)
    except Exception:
        arr = []
    target = None
    for a in arr:
        ap = a.get("path", "")
        if os.path.basename(ap) == name:
            target = ap
            break
    if not target or not os.path.exists(target):
        raise HTTPException(404, "artifact not found")
    ctype, _ = mimetypes.guess_type(target)
    return FileResponse(path=target, media_type=ctype or "application/octet-stream", filename=name)
