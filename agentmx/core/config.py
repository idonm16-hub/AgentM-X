import os
import yaml
from dataclasses import dataclass
from typing import Any, Dict

CONFIG_PATHS = ["config.yaml", "config.yml", "config.example.yaml"]

@dataclass
class Config:
    raw: Dict[str, Any]

    def get(self, path: str, default=None):
        cur = self.raw
        for part in path.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return default
            cur = cur[part]
        return cur

def load_config() -> Config:
    for p in CONFIG_PATHS:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return Config(raw=data)
    return Config(raw={})
