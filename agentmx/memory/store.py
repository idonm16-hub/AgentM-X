import os
import sqlite3
import json
from typing import Optional, Dict, Any, List, Tuple

DEFAULT_DB = ".agentmx/memory/runs.sqlite"

def _ensure_dir(path: str):
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def connect(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = db_path or DEFAULT_DB
    _ensure_dir(path)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, status TEXT, duration REAL, score REAL, created_at REAL)")
    conn.execute("CREATE TABLE IF NOT EXISTS artifacts (run_id TEXT, name TEXT, size INTEGER, sha256 TEXT, mime TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS skills_learned (name TEXT, test_path TEXT, created_at REAL)")
    conn.commit()
    return conn

def record_run(conn: sqlite3.Connection, run_id: str, status: str, duration: float, score: float):
    conn.execute("INSERT OR REPLACE INTO runs(id,status,duration,score,created_at) VALUES(?,?,?,?,strftime('%s','now'))", (run_id, status, duration, score))
    conn.commit()

def record_artifacts(conn: sqlite3.Connection, run_id: str, artifacts):
    cur = conn.cursor()
    for a in artifacts or []:
        cur.execute("INSERT INTO artifacts(run_id,name,size,sha256,mime) VALUES(?,?,?,?,?)",
                    (run_id, os.path.basename(a.get('path','')), int(a.get('size') or 0), a.get('sha256'), a.get('mime')))
    conn.commit()

def record_skill(conn: sqlite3.Connection, name: str, test_path: str):
    conn.execute("INSERT INTO skills_learned(name,test_path,created_at) VALUES(?,?,strftime('%s','now'))", (name, test_path))
    conn.commit()

def _score_histogram(rows: List[Tuple[float]]) -> Dict[str, int]:
    buckets = {"0-0.2":0, "0.2-0.4":0, "0.4-0.6":0, "0.6-0.8":0, "0.8-1.0":0, "1.0":0}
    for (s,) in rows:
        if s is None:
            continue
        if s == 1.0:
            buckets["1.0"] += 1
        elif s < 0.2:
            buckets["0-0.2"] += 1
        elif s < 0.4:
            buckets["0.2-0.4"] += 1
        elif s < 0.6:
            buckets["0.4-0.6"] += 1
        elif s < 0.8:
            buckets["0.6-0.8"] += 1
        else:
            buckets["0.8-1.0"] += 1
    return buckets

def metrics(conn: sqlite3.Connection) -> Dict[str, Any]:
    cur = conn.cursor()
    cur.execute("SELECT COUNT(1) FROM runs WHERE status='success' AND created_at>=strftime('%s','now','-7 days')")
    s7 = cur.fetchone()[0]
    cur.execute("SELECT COUNT(1) FROM runs WHERE status='success' AND created_at>=strftime('%s','now','-30 days')")
    s30 = cur.fetchone()[0]
    cur.execute("SELECT AVG(duration) FROM runs WHERE duration IS NOT NULL")
    avg_dur = cur.fetchone()[0] or 0
    cur.execute("SELECT name,test_path,created_at FROM skills_learned ORDER BY created_at DESC LIMIT 10")
    skills = [{"name": r[0], "test_path": r[1], "created_at": r[2]} for r in cur.fetchall()]
    cur.execute("SELECT score FROM runs ORDER BY created_at DESC LIMIT 1000")
    score_rows = cur.fetchall()
    hist = _score_histogram(score_rows)
    return {"success_7d": s7, "success_30d": s30, "avg_duration": avg_dur, "recent_skills": skills, "score_histogram": hist}
