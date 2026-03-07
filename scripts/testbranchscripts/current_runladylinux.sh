#!/usr/bin/env bash
set -euo pipefail
set -x

# Updated for Line Endings
echo "Launching LadyLinux LLM system..."

# --- Ensure dedicated LLM service is running ---
echo "Checking LLM runtime service..."
sudo systemctl daemon-reload
if ! systemctl is-active --quiet ladylinux-llm.service; then
    echo "Starting ladylinux-llm.service..."
    sudo systemctl start ladylinux-llm.service
fi
sudo systemctl --no-pager --full status ladylinux-llm.service || true

# --- Start FastAPI backend via systemd ---
echo "Restarting ladylinux-api.service..."
sudo systemctl restart ladylinux-api.service
sudo systemctl --no-pager --full status ladylinux-api.service || true

# --- Open web interface ---
echo "Opening web interface at http://localhost:8000 ..."
if command -v xdg-open > /dev/null; then
    xdg-open http://localhost:8000 >/dev/null 2>&1 &
else
    echo "Please open your browser and visit: http://localhost:8000"
fi

echo "LadyLinux system launched successfully."
