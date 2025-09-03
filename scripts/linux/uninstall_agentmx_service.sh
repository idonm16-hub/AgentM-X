#!/usr/bin/env bash
set -euo pipefail
if systemctl is-enabled --quiet agentmx-scheduler.service; then
  sudo systemctl disable agentmx-scheduler.service || true
fi
if systemctl is-active --quiet agentmx-scheduler.service; then
  sudo systemctl stop agentmx-scheduler.service || true
fi
sudo rm -f /etc/systemd/system/agentmx-scheduler.service
sudo systemctl daemon-reload
echo "Uninstalled agentmx-scheduler.service"
