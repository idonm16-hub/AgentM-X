[CmdletBinding()] param()

Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force

winget install -e --id Python.Python.3.11
pip install uv --upgrade

uv venv
uv sync
uv run playwright install --with-deps chromium

Write-Host "Bootstrap complete."
