import os
import sys
import uuid
import time
import argparse
from loguru import logger
from agentmx.core.config import load_config
from agentmx.core.runner import AgentRunner

def main():
    parser = argparse.ArgumentParser(prog="agentmx", description="AgentM-X runner")
    parser.add_argument("cmd", choices=["run"], help="command")
    parser.add_argument("task", nargs="?", help="task string")
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument("--net", choices=["on","off"], default="on")
    parser.add_argument("--allow-safety-edit", choices=["yes","no"], default="no")
    args = parser.parse_args()

    if args.cmd == "run":
        if not args.task:
            print("Task string required", file=sys.stderr)
            sys.exit(2)
        cfg = load_config()
        run_id = str(uuid.uuid4())
        logger.info(f"Starting run {run_id} task='{args.task}'")
        runner = AgentRunner(cfg, run_id=run_id, net_enabled=(args.net=="on"), allow_safety_edit=(args.allow_safety_edit=="yes"))
        rc = runner.execute(args.task, timeout=args.timeout)
        sys.exit(0 if rc else 1)

if __name__ == "__main__":
    main()
