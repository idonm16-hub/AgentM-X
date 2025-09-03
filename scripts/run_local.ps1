$env:AGENTMX_API_KEY = (Get-Content .env | Select-String 'AGENTMX_API_KEY' | % { $_.ToString().Split('=')[1].Trim() })
uv run uvicorn agentmx.ui.api:app --host 127.0.0.1 --port 8937
