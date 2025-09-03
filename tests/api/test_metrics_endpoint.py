import os
from fastapi.testclient import TestClient
from agentmx.ui.api import app

def test_metrics_requires_key(monkeypatch):
    monkeypatch.setenv("AGENTMX_API_KEY", "k")
    c = TestClient(app)
    r = c.get("/metrics", headers={"X-API-Key":"k"})
    assert r.status_code == 200
    assert "success_7d" in r.json()
    r2 = c.get("/metrics")
    assert r2.status_code == 401
