#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE="$DIR/agentmx-scheduler.service"
sudo cp "$SERVICE" /etc/systemd/system/agentmx-scheduler.service
sudo systemctl daemon-reload
sudo systemctl enable agentmx-scheduler.service
sudo systemctl start agentmx-scheduler.service
echo "Installed and started agentmx-scheduler.service"
