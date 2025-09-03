from typing import Dict, Any, List, Tuple

def plan(task_type: str, payload: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if task_type == "bootstrap_demo":
        steps = [
            {"action": "run_demo", "args": {}}
        ]
        verification = {"expect_artifacts": ["notepad_output.txt", "receipt.txt"]}
        return steps, verification
    return [{"action": "noop", "args": {"seconds": 1}}], {"expect_artifacts": []}
