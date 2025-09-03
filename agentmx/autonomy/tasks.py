import os
import sqlite3
import json
import time
from typing import Optional, Tuple, Dict, Any

DEFAULT_DB = ".agentmx/tasks.db"

def _ensure_dir(path: str):
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def connect(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = db_path or DEFAULT_DB
    _ensure_dir(path)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS tasks ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "type TEXT NOT NULL,"
        "payload TEXT NOT NULL,"
        "status TEXT NOT NULL DEFAULT 'queued',"
        "priority INTEGER NOT NULL DEFAULT 0,"
        "run_id TEXT,"
        "created_at REAL NOT NULL DEFAULT (strftime('%s','now'))"
        ");"
    )
    conn.commit()
    return conn

def enqueue(conn: sqlite3.Connection, ttype: str, payload: Dict[str, Any], priority: int = 0) -> int:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO tasks(type,payload,status,priority,created_at) VALUES(?,?,?,?,strftime('%s','now'))",
        (ttype, json.dumps(payload), "queued", priority),
    )
    conn.commit()
    return int(cur.lastrowid)

def next_task(conn: sqlite3.Connection) -> Optional[Tuple[int, str, Dict[str, Any]]]:
    cur = conn.cursor()
    cur.execute(
        "SELECT id, type, payload FROM tasks WHERE status='queued' ORDER BY priority DESC, created_at ASC LIMIT 1"
    )
    row = cur.fetchone()
    if not row:
        return None
    return int(row[0]), str(row[1]), json.loads(row[2])

def mark_running(conn: sqlite3.Connection, task_id: int, run_id: str):
    cur = conn.cursor()
    cur.execute("UPDATE tasks SET status='running', run_id=? WHERE id=?", (run_id, task_id))
    conn.commit()

def mark_status(conn: sqlite3.Connection, task_id: int, status: str):
    cur = conn.cursor()
    cur.execute("UPDATE tasks SET status=? WHERE id=?", (status, task_id))
    conn.commit()

def is_empty(conn: sqlite3.Connection) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT COUNT(1) FROM tasks")
    c = cur.fetchone()[0]
    return c == 0
