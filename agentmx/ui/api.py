import os
import sys
import uuid
import json
import mimetypes
import threading
import asyncio
import datetime
from typing import Optional
from loguru import logger
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse, FileResponse, StreamingResponse
from agentmx.core.config import load_config
from agentmx.core.runner import AgentRunner
from agentmx.memory import store as mem

app = FastAPI()
cfg = load_config()
def _iso(ts):
    try:
        if ts is None:
            return None
        if isinstance(ts, (int, float)):
            return datetime.datetime.utcfromtimestamp(ts).isoformat() + "Z"
        if isinstance(ts, str):
            return ts
    except Exception:
        pass
    return None

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

@app.get("/scheduler/health")
async def scheduler_health():
    path = os.path.join(".agentmx", "scheduler.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    return {
        "queue_depth": int(data.get("queue_depth")) if data.get("queue_depth") is not None else 0,
        "last_tick": data.get("last_tick"),
        "poll_interval_sec": int(data.get("poll_interval")) if data.get("poll_interval") is not None else None,
        "last_success_ts": data.get("last_success_ts"),
        "last_error_count": int(data.get("last_error_count")) if data.get("last_error_count") is not None else 0,
    }

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
    conn = mem.connect()
    try:
        mem.begin(conn)
        mem.upsert_run(conn, run_id, "running", 0.0, 0.0)
        mem.commit(conn)
    except Exception:
        mem.rollback(conn)
    return JSONResponse({"accepted": True, "run_id": run_id, "task": task})

@app.get("/runs/{run_id}/status")
async def run_status(run_id: str):
    conn = mem.connect()
    row = mem.get_run(conn, run_id)
    if not row:
        raise HTTPException(404, "run not found")
    return {"run_id": row["id"], "status": row["status"], "score": row.get("score"), "duration": row.get("duration"), "created_at": _iso(row.get("created_at"))}

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
    conn = mem.connect()
    row = mem.get_run(conn, run_id)
    if not row:
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
                cur = mem.get_run(mem.connect(), run_id)
                st = (cur or {}).get("status") or "unknown"
            except Exception:
                st = "unknown"
            now = asyncio.get_event_loop().time()
            if now - last_ping >= 12.0:
                yield "event: ping\ndata: {}\n\n"
                last_ping = now
            if st in ("completed", "aborted", "failed"):
                break
            await asyncio.sleep(0.2)
    return StreamingResponse(_sse_gen(), media_type="text/event-stream")
@app.get("/runs")
async def list_runs(limit: int = 50, offset: int = 0):
    conn = mem.connect()
    runs = mem.list_runs(conn, limit=limit, offset=offset)
    for r in runs:
        r["created_at"] = _iso(r.get("created_at"))
    return {"runs": runs}

@app.get("/runs/latest")
async def latest_run():
    conn = mem.connect()
    row = mem.latest_run(conn)
    if not row:
        return {"run": None}
    row["created_at"] = _iso(row.get("created_at"))
    return {"run": row}

@app.get("/runs/{run_id}")
async def run_detail(run_id: str):
    conn = mem.connect()
    row = mem.get_run(conn, run_id)
    if not row:
        raise HTTPException(404, "run not found")
    row["created_at"] = _iso(row.get("created_at"))
    arts = mem.list_artifacts(conn, run_id)
    for a in arts:
        a["created_at"] = _iso(a.get("created_at"))
    row["artifacts"] = arts
    return row



@app.get("/metrics")
async def metrics():
    conn = mem.connect()
    return mem.metrics(conn)


@app.get("/runs/{run_id}/artifacts")
async def run_artifacts(run_id: str):
    conn = mem.connect()
    if not mem.get_run(conn, run_id):
        raise HTTPException(404, "run not found")
    arts = mem.list_artifacts(conn, run_id)
    return {"artifacts": [
        {"name": a.get("name"), "size": a.get("size"), "sha256": a.get("sha256"), "mime": a.get("mime"), "path": a.get("path"), "created_at": _iso(a.get("created_at"))}
        for a in arts
    ]}

@app.get("/runs/{run_id}/artifact/{name}")
async def run_artifact_download(run_id: str, name: str):
    if ".." in name or "/" in name or "\\" in name:
        raise HTTPException(400, "invalid artifact name")
    conn = mem.connect()
    if not mem.get_run(conn, run_id):
        raise HTTPException(404, "run not found")
    arts = mem.list_artifacts(conn, run_id)
    target = None
    for a in arts:
        ap = a.get("path", "")
        if a.get("name") == name or os.path.basename(ap) == name:
            target = ap
            break
    if not target or not os.path.exists(target):
        raise HTTPException(404, "artifact not found")
    ctype, _ = mimetypes.guess_type(target)
    return FileResponse(path=target, media_type=ctype or "application/octet-stream", filename=name)
