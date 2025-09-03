import os
import sys
import uuid
import time
import argparse
import json
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

SCHED_DIR = ".agentmx"
SCHED_HEALTH = os.path.join(SCHED_DIR, "scheduler.json")
SCHED_LOG = os.path.join(SCHED_DIR, "scheduler.log")

def _rotate_log(path: str, max_bytes: int = 5 * 1024 * 1024, keep: int = 3):
    try:
        if not os.path.exists(path):
            return
        if os.path.getsize(path) < max_bytes:
            return
        for i in range(keep, 0, -1):
            src = f"{path}.{i}"
            dst = f"{path}.{i+1}"
            if os.path.exists(dst):
                try:
                    os.remove(dst)
                except Exception:
                    pass
            if os.path.exists(src):
                os.rename(src, dst)
        os.rename(path, f"{path}.1")
    except Exception:
        pass

def _append_sched_log(line: str):
    os.makedirs(SCHED_DIR, exist_ok=True)
    try:
        with open(SCHED_LOG, "a", encoding="utf-8") as f:
            f.write(line.rstrip() + "\n")
    except Exception:
        pass
    _rotate_log(SCHED_LOG)

def cmd_scheduler(args):
    cfg = load_config()
    poll_interval = int(cfg.get("autonomy.poll_interval", 10))
    conn = taskq.connect()
    if taskq.is_empty(conn):
        taskq.enqueue(conn, "bootstrap_demo", {})
    health = {"queue_depth": 0, "last_tick": None, "poll_interval": poll_interval, "last_success_ts": None, "last_error_count": 0}
    while True:
        try:
            health["last_tick"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            try:
                cur = taskq.connect()
                health["queue_depth"] = int(cur.execute("SELECT COUNT(1) FROM tasks WHERE status='queued'").fetchone()[0])
            except Exception:
                health["queue_depth"] = 0
            os.makedirs(SCHED_DIR, exist_ok=True)
            with open(SCHED_HEALTH, "w", encoding="utf-8") as f:
                json.dump(health, f)
            nxt = taskq.next_task(conn)
            if not nxt:
                _append_sched_log(f"{int(time.time())} idle queue_depth={health['queue_depth']}")
                time.sleep(poll_interval)
                continue
            task_id, ttype, payload = nxt
            run_id = uuid.uuid4().hex
            start_ts = time.time()
            _append_sched_log(f"{int(start_ts)} picked task_id={task_id} type={ttype} run_id={run_id}")
            try:
                taskq.mark_running(conn, task_id, run_id)
                steps, verification = planner_mod.plan(ttype, payload)
                executor_mod.execute_steps(cfg, steps, run_id=run_id)
                workdir = cfg.get("execution.working_dir", f".agentmx/work/{run_id}").format(run_id=run_id)
                eval_res = evaluator_mod.evaluate(workdir, verification)
                score = float(eval_res.get("score") or 0.0)
                default_thresh = float(cfg.get("autonomy.thresholds.default", 0.8))
                threshold = float(cfg.get("autonomy.thresholds.bootstrap_demo", 1.0)) if ttype == "bootstrap_demo" else default_thresh
                status = "completed" if score >= threshold else "failed"
                taskq.mark_status(conn, task_id, status)
                duration = max(0.0, time.time() - start_ts)
                mconn = mem.connect()
                mem.record_run(mconn, run_id, status, duration, score)
                try:
                    with open(os.path.join(workdir, "artifacts.json"), "r", encoding="utf-8") as f:
                        arts = json.load(f)
                except Exception:
                    arts = []
                mem.record_artifacts(mconn, run_id, arts)
                if status != "completed":
                    from agentmx.skills.factory import SkillFactory
                    from agentmx.skills.registry import SkillRegistry
                    sf = SkillFactory(SkillRegistry(), max_new=1)
                    learn_res = sf.maybe_learn(run_id, threshold, score)
                    if learn_res.get("learned"):
                        mem.record_skill(mconn, learn_res["name"], learn_res["test_path"])
                health["last_success_ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                with open(SCHED_HEALTH, "w", encoding="utf-8") as f:
                    json.dump(health, f)
                _append_sched_log(f"{int(time.time())} finished task_id={task_id} status={status} score={score:.3f} duration={duration:.3f}s")
            except Exception as e:
                health["last_error_count"] = int(health.get("last_error_count") or 0) + 1
                with open(SCHED_HEALTH, "w", encoding="utf-8") as f:
                    json.dump(health, f)
                _append_sched_log(f"{int(time.time())} error task_id={task_id} err={e}")
            time.sleep(poll_interval)
        except Exception as e:
            health["last_error_count"] = int(health.get("last_error_count") or 0) + 1
            try:
                with open(SCHED_HEALTH, "w", encoding="utf-8") as f:
                    json.dump(health, f)
            except Exception:
                pass
            _append_sched_log(f"{int(time.time())} loop_error err={e}")
            time.sleep(poll_interval)

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
