import os
import json
from agentmx.autonomy import tasks as taskq

def test_queue_enqueue_next_mark(tmp_path, monkeypatch):
    db = tmp_path / "tasks.db"
    conn = taskq.connect(str(db))
    assert taskq.is_empty(conn) is True
    t1 = taskq.enqueue(conn, "bootstrap_demo", {})
    assert isinstance(t1, int)
    assert taskq.is_empty(conn) is False
    nxt = taskq.next_task(conn)
    assert nxt is not None
    tid, ttype, payload = nxt
    assert tid == t1
    assert ttype == "bootstrap_demo"
    assert payload == {}
    taskq.mark_status(conn, tid, "running")
    taskq.mark_status(conn, tid, "success")
