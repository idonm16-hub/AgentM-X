import os
import json
import time
from fastapi.testclient import TestClient
from agentmx.ui.api import app

def test_runs_endpoints_lifecycle(monkeypatch):
    monkeypatch.setenv("AGENTMX_API_KEY", "k")
    c = TestClient(app)
    r = c.post("/run", headers={"X-API-Key": "k"}, json={"task": "demo"})
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    st = None
    for _ in range(150):
        s = c.get(f"/runs/{run_id}/status", headers={"X-API-Key": "k"})
        assert s.status_code == 200
        st = s.json().get("status")
        if st in ("success", "stopped", "error"):
            break
        time.sleep(0.05)
    assert st in ("success", "stopped", "error")
    lg = c.get(f"/runs/{run_id}/logs", headers={"X-API-Key": "k"})
    assert lg.status_code == 200
    art = c.get(f"/runs/{run_id}/artifacts", headers={"X-API-Key": "k"})
    assert art.status_code == 200
    data = art.json()
    assert "artifacts" in data
