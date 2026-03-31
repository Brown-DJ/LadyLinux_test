#!/usr/bin/env bash
set -euo pipefail

echo "Launching LadyLinux..."

# Ensure Ollama is running
if ! systemctl is-active --quiet ollama 2>/dev/null && \
   ! systemctl is-active --quiet ladylinux-llm.service 2>/dev/null; then
    sudo systemctl start ollama 2>/dev/null || sudo systemctl start ladylinux-llm.service 2>/dev/null || true
fi

# Ensure API is running
if ! pgrep -f "uvicorn api_layer:app" >/dev/null 2>&1; then
    sudo systemctl start ladylinux-api.service 2>/dev/null || true
    sleep 3
fi

URL="http://localhost:8000"

# Open browser
if command -v chromium >/dev/null 2>&1; then
    chromium --app="$URL" --class=LadyLinuxApp &
elif command -v chromium-browser >/dev/null 2>&1; then
    chromium-browser --app="$URL" --class=LadyLinuxApp &
elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL" &
else
    echo "Please open your browser and visit: $URL"
fi
