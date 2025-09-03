import os
import pytest
from fastapi.testclient import TestClient
from agentmx.ui.api import app

def test_api_requires_key(monkeypatch):
    monkeypatch.setenv("AGENTMX_API_KEY", "k")
    c = TestClient(app)
    r = c.get("/health", headers={"X-API-Key": "k"})
    assert r.status_code == 200
    r2 = c.get("/health")
    assert r2.status_code == 401
