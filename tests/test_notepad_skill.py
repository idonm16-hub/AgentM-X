import os
import pytest

WIN = os.name == "nt"

pytestmark = pytest.mark.skipif(not WIN, reason="Notepad skill only runs on Windows")

def test_notepad_open_type_save(tmp_path):
    from agentmx.skills.gui.notepad import NotepadSkill
    text = "hello from agentmx"
    fpath = tmp_path / "note.txt"
    s = NotepadSkill()
    s.open()
    try:
        s.type_text(text)
        out = s.save_as(str(fpath))
    finally:
        s.close()
    assert out == str(fpath)
    assert fpath.exists()
    assert fpath.read_text(encoding="utf-8", errors="ignore").find("hello from agentmx") != -1
