import os
import sys
import uuid
import time
import argparse
from loguru import logger
from agentmx.core.config import load_config
from agentmx.core.runner import AgentRunner
from agentmx.autonomy import tasks as taskq
from agentmx.autonomy import planner as planner_mod
from agentmx.autonomy import executor as executor_mod
from agentmx.autonomy import evaluator as evaluator_mod
from agentmx.memory import store as mem

def cmd_run(args):
    cfg = load_config()
    run_id = str(uuid.uuid4())
    logger.info(f"Starting run {run_id} task='{args.task}'")
    runner = AgentRunner(cfg, run_id=run_id, net_enabled=(args.net=="on"), allow_safety_edit=(args.allow_safety_edit=="yes"))
    rc = runner.execute(args.task, timeout=args.timeout)
    sys.exit(0 if rc else 1)

def cmd_scheduler(args):
    cfg = load_config()
    conn = taskq.connect()
    if taskq.is_empty(conn):
        taskq.enqueue(conn, "bootstrap_demo", {})
    while True:
        nxt = taskq.next_task(conn)
        if not nxt:
            time.sleep(10)
            continue
        task_id, ttype, payload = nxt
        import uuid, time as _time, os, json
        run_id = uuid.uuid4().hex
        start_ts = _time.time()
        try:
            taskq.mark_running(conn, task_id, run_id)
            steps, verification = planner_mod.plan(ttype, payload)
            exec_res = executor_mod.execute_steps(cfg, steps, run_id=run_id)
            workdir = cfg.get("execution.working_dir", f".agentmx/work/{run_id}").format(run_id=run_id)
            eval_res = evaluator_mod.evaluate(workdir, verification)
            score = float(eval_res.get("score") or 0.0)
            default_thresh = float(cfg.get("autonomy.thresholds.default", 0.8))
            if ttype == "bootstrap_demo":
                threshold = float(cfg.get("autonomy.thresholds.bootstrap_demo", 1.0))
            else:
                threshold = default_thresh
            status = "success" if score >= threshold else "error"
            taskq.mark_status(conn, task_id, status)
            duration = max(0.0, _time.time() - start_ts)
            mconn = mem.connect()
            mem.record_run(mconn, run_id, status, duration, score)
            try:
                with open(os.path.join(workdir, "artifacts.json"), "r", encoding="utf-8") as f:
                    arts = json.load(f)
            except Exception:
                arts = []
            mem.record_artifacts(mconn, run_id, arts)
            from agentmx.skills.factory import SkillFactory
            from agentmx.skills.registry import SkillRegistry
            if status != "success":
                sf = SkillFactory(SkillRegistry(), max_new=1)
                learn_res = sf.maybe_learn(run_id, threshold, score)
                if learn_res.get("learned"):
                    mem.record_skill(mconn, learn_res["name"], learn_res["test_path"])
        except Exception:
            taskq.mark_status(conn, task_id, "error")
        time.sleep(10)

def main():
    parser = argparse.ArgumentParser(prog="agentmx", description="AgentM-X runner")
    sub = parser.add_subparsers(dest="cmd")

    runp = sub.add_parser("run")
    runp.add_argument("task", type=str)
    runp.add_argument("--timeout", type=int, default=3600)
    runp.add_argument("--net", choices=["on","off"], default="on")
    runp.add_argument("--allow-safety-edit", choices=["yes","no"], default="no")

    sub.add_parser("scheduler")

    args = parser.parse_args()
    if args.cmd == "run":
        cmd_run(args)
    elif args.cmd == "scheduler":
        cmd_scheduler(args)
    else:
        parser.print_help()
