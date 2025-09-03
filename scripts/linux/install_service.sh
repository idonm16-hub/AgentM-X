#!/usr/bin/env bash
set -euo pipefail
UNIT=${UNIT:-agentmx-scheduler.service}
HOME_DIR=${AGENTMX_HOME:-/home/ubuntu/AgentM-X}
sudo cp "$(dirname "$0")/$UNIT" /etc/systemd/system/$UNIT
sudo systemctl daemon-reload
sudo systemctl enable $UNIT
sudo systemctl start $UNIT
echo "Installed and started $UNIT with AGENTMX_HOME=$HOME_DIR"
