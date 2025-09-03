import os
import tempfile
import pytest
from agentmx.safety.runner import StopFileGuard

def test_stop_guard_triggers():
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "STOP")
        sg = StopFileGuard(path)
        with pytest.raises(StopFileGuard.Stopped):
            open(path,"w").close()
            sg.check()
