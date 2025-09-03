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
