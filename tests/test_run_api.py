import os
from fastapi.testclient import TestClient
from agentmx.ui.api import app

def test_run_endpoint_starts(monkeypatch):
    monkeypatch.setenv("AGENTMX_API_KEY", "k")
    c = TestClient(app)
    r = c.post("/run", headers={"X-API-Key": "k"}, json={"task": "hello"})
    assert r.status_code == 200
    data = r.json()
    assert data["accepted"] is True
    assert data["task"] == "hello"
    assert "run_id" in data
