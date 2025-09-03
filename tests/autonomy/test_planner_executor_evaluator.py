from agentmx.autonomy import planner, executor, evaluator
from agentmx.core.config import load_config

def test_bootstrap_demo_plans_and_scores(tmp_path, monkeypatch):
    cfg = load_config()
    res = executor.execute_steps(cfg, [{"action":"noop","args":{"seconds":0}}])
    assert "run_id" not in res
    steps, ver = planner.plan("bootstrap_demo", {})
    assert steps and ver.get("expect_artifacts") == ["notepad_output.txt","receipt.txt"]
