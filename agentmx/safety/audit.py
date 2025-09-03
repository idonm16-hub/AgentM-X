import os
import json
import hashlib
from datetime import datetime, UTC
from typing import Optional

class AuditLog:
    def __init__(self, workdir: str):
        self.path = os.path.join(workdir, "audit.log")
        self.last_hash = "0"*64

    def record(self, event: str, data: dict):
        rec = {
            "ts": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "event": event,
            "data": data or {},
            "prev": self.last_hash,
        }
        payload = json.dumps(rec, sort_keys=True).encode()
        h = hashlib.sha256(payload).hexdigest()
        rec["hash"] = h
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        self.last_hash = h
