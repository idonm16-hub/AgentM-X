import os
import hashlib
import time
import subprocess
from typing import Dict, Any

GEN_DIR = os.path.join("agentmx", "skills", "generated")
TEST_DIR = os.path.join("tests", "generated")

class SkillFactory:
    def __init__(self, registry, max_new: int = 1):
        self.registry = registry
        self.max_new = max_new
        self._made = 0

    def _spec_header(self, run_id: str, spec: Dict[str, Any]) -> str:
        ts = int(time.time())
        spec_bytes = repr(sorted(spec.items())).encode("utf-8")
        spec_hash = hashlib.sha256(spec_bytes).hexdigest()[:12]
        return f"# generated at {ts} run_id={run_id} spec_hash={spec_hash}\n"

    def _write_generated_files(self, run_id: str, name: str) -> Dict[str, str]:
        os.makedirs(GEN_DIR, exist_ok=True)
        os.makedirs(TEST_DIR, exist_ok=True)
        class_name = "TextNormalizeSkill"
        skill_path = os.path.join(GEN_DIR, f"{name}.py")
        test_path = os.path.join(TEST_DIR, f"test_{name}.py")
        header = self._spec_header(run_id, {"skill": name})
        code = (
            f"{header}"
            f"class {class_name}:\n"
            f"    def run(self, path: str) -> str:\n"
            f"        import os\n"
            f"        p = os.path.abspath(path)\n"
            f"        with open(p, 'r', encoding='utf-8') as f:\n"
            f"            txt = f.read()\n"
            f"        norm = '\\n'.join(line.strip() for line in txt.splitlines()) + '\\n'\n"
            f"        out = p + '.norm.txt'\n"
            f"        with open(out, 'w', encoding='utf-8') as f:\n"
            f"            f.write(norm)\n"
            f"        return out\n"
        )
        test = (
            f"def test_{name}(tmp_path):\n"
            f"    p = tmp_path / 'a.txt'\n"
            f"    p.write_text(' a  \\n b ')\n"
            f"    from agentmx.skills.generated.{name} import {class_name}\n"
            f"    s = {class_name}()\n"
            f"    out = s.run(str(p))\n"
            f"    import pathlib\n"
            f"    assert pathlib.Path(out).read_text() == 'a\\nb\\n'\n"
        )
        with open(skill_path, "w", encoding="utf-8") as f:
            f.write(code)
        with open(test_path, "w", encoding="utf-8") as f:
            f.write(test)
        return {"skill": skill_path, "test": test_path, "class_name": class_name}

    def _register_in_registry(self, name: str, class_name: str):
        reg_path = os.path.join("agentmx", "skills", "registry.py")
        with open(reg_path, "r", encoding="utf-8") as f:
            src = f.read()
        func_sig = f"    def {name}(self):"
        if func_sig in src:
            return
        add = (
            f"\n    def {name}(self):\n"
            f"        from agentmx.skills.generated.{name} import {class_name}\n"
            f"        return {class_name}\n"
        )
        with open(reg_path, "a", encoding="utf-8") as f:
            f.write(add)

    def maybe_learn(self, run_id: str, threshold: float, score: float) -> Dict[str, Any]:
        if self._made >= self.max_new:
            return {"learned": False, "reason": "max_new_reached"}
        if score >= threshold:
            return {"learned": False, "reason": "threshold_met"}
        name = "text_normalize"
        paths = self._write_generated_files(run_id, name)
        try:
            r = subprocess.run(["uv", "run", "pytest", "-q", "-k", name], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=300)
            if r.returncode != 0:
                return {"learned": False, "reason": "pytest_failed", "output": r.stdout}
        except Exception as e:
            return {"learned": False, "reason": "pytest_error", "error": str(e)}
        self._register_in_registry(name, paths["class_name"])
        self._made += 1
        return {"learned": True, "name": name, "skill_path": paths["skill"], "test_path": paths["test"]}
