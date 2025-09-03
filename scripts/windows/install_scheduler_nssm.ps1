param(
  [string]$AgentHome = $env:AGENTMX_HOME
)
if (-not $AgentHome) { $AgentHome = "C:\AgentM-X" }
$nssm = "nssm.exe"
$svc = "AgentMX-Scheduler"
$cmd = "powershell.exe"
$args = "-NoProfile -Command `"cd $AgentHome; uv run python -m agentmx.cli scheduler`""
& $nssm install $svc $cmd $args
& $nssm set $svc AppDirectory $AgentHome
& $nssm set $svc Start SERVICE_AUTO_START
Write-Host "Installed service $svc at $AgentHome"
