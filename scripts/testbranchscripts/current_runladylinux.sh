#!/usr/bin/env bash
set -euo pipefail

LLM_SERVICE="ladylinux-llm.service"
API_SERVICE="ladylinux-api.service"
API_URL="http://127.0.0.1:8000"

echo "Launching LadyLinux system..."

# --- Ensure dedicated LLM service is running ---
echo "Checking LLM runtime service..."
sudo systemctl daemon-reload
sudo systemctl enable "$LLM_SERVICE" >/dev/null 2>&1 || true
sudo systemctl restart "$LLM_SERVICE"
sudo systemctl --no-pager --full status "$LLM_SERVICE" || true

echo "Waiting for LLM runtime endpoint..."
llm_ready=0
for _ in $(seq 1 30); do
    if curl --silent --fail --max-time 2 "http://127.0.0.1:11434" >/dev/null 2>&1; then
        llm_ready=1
        break
    fi
    sleep 1
done
if [[ "$llm_ready" -ne 1 ]]; then
    echo "LLM runtime did not become ready in time."
    exit 1
fi

# --- Start FastAPI backend via systemd ---
echo "Restarting $API_SERVICE..."
sudo systemctl enable "$API_SERVICE" >/dev/null 2>&1 || true
sudo systemctl restart "$API_SERVICE"
sudo systemctl --no-pager --full status "$API_SERVICE" || true

echo "Waiting for API at $API_URL ..."
api_ready=0
for _ in $(seq 1 60); do
    if curl --silent --fail --max-time 2 "$API_URL" >/dev/null 2>&1; then
        api_ready=1
        break
    fi
    sleep 1
done
if [[ "$api_ready" -ne 1 ]]; then
    echo "API did not become ready in time."
    exit 1
fi

# --- Open web interface ---
echo "Opening web interface at $API_URL ..."
if command -v xdg-open > /dev/null; then
    xdg-open "$API_URL" >/dev/null 2>&1 &
else
    echo "Please open your browser and visit: $API_URL"
fi

echo "LadyLinux system launched successfully."
