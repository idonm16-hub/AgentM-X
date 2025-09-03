# AgentM-X

Autonomous, Self-Evolving Multi-Agent System for Windows (Full Host Control).

Quickstart:
- scripts/bootstrap.ps1
- uv venv && uv sync
- copy .env.example .env
- copy config.example.yaml config.yaml
- uv run playwright install --with-deps chromium
- uv run uvicorn agentmx.ui.api:app --host 127.0.0.1 --port 8937
- uv run agentmx run "Open Notepad, type text, save to Desktop, upload to dummy site"

API (localhost only, requires X-API-Key):
- POST /run {"task": "..."} -> {"accepted": true, "run_id": "..."}
- GET /runs/{id}/status -> {"status": "running|success|stopped|error", ...}
- GET /runs/{id}/logs -> text/plain audit log
- GET /runs/{id}/artifacts -> {"artifacts":[{"path","type","size","created_at"}]}
- Swagger: /docs

Artifacts & Workdir:
- Workdir: .agentmx/work/{run_id}
- Audit: audit.log (hash-chained)
- Status: status.json
- Artifacts: artifacts.json
- Browser downloads: .agentmx/work/{run_id}/browser

Safety:
- STOP kill-switch file: .agentmx/STOP (checked during run)
- Windows global hotkey (Ctrl+Alt+S) writes STOP file (if keyboard lib available)

## Windows GUI Skill: Notepad

Validate on Windows 11/Server 2022:
1) scripts/bootstrap.ps1
2) copy .env.example .env and set AGENTMX_API_KEY
3) uv run pytest -q  (Notepad test runs only on Windows)
4) Quick manual check:
   - python -c "from agentmx.skills.gui.notepad import NotepadSkill; s=NotepadSkill(); s.open(); s.type_text('hello from agentmx'); import pathlib; p=str(pathlib.Path.home()/ 'Desktop' / 'agentmx-note.txt'); s.save_as(p); s.close(); print(p)"
   - Verify the file exists and contains the text.
