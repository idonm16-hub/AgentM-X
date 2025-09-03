import os
import pytest

WIN = os.name == "nt"

pytestmark = pytest.mark.skipif(not WIN, reason="Notepad skill only runs on Windows")

def test_notepad_open_type_save(tmp_path):
    from agentmx.skills.gui.notepad import NotepadSkill
    fpath = tmp_path / "note.txt"
    s = NotepadSkill()
    s.open()
    try:
        s.type_text("hello from agentmx")
        s.save_as(str(fpath))
    finally:
        s.close()
    assert fpath.exists()
    assert fpath.stat().st_size > 0
