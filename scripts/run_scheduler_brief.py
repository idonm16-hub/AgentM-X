import threading
import time
from types import SimpleNamespace
from agentmx.cli import cmd_scheduler

def main():
    args = SimpleNamespace()
    t = threading.Thread(target=cmd_scheduler, args=(args,), daemon=True)
    t.start()
    time.sleep(4)

if __name__ == "__main__":
    main()
