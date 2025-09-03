import os
import json
from typing import Dict, Any

def evaluate(run_workdir: str, verification: Dict[str, Any]) -> Dict[str, Any]:
    score = 0.0
    details = {}
    try:
        arts_path = os.path.join(run_workdir, "artifacts.json")
        with open(arts_path, "r", encoding="utf-8") as f:
            arts = json.load(f)
    except Exception:
        arts = []
    expected = verification.get("expect_artifacts") or []
    found = set(os.path.basename(a.get("path","")) for a in arts)
    hit = sum(1 for name in expected if name in found)
    if expected:
        score = hit / float(len(expected))
    else:
        score = 1.0
    details["found"] = list(found)
    details["expected"] = expected
    return {"score": score, "details": details}
