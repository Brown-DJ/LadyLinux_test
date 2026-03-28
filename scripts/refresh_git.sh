#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="/opt/ladylinux/app"
SERVICE_NAME="ladylinux-api"
LOG_DIR="/var/lib/ladylinux/logs"
LOG_FILE="$LOG_DIR/refresh_api.log"
BRANCH="${1:-main}"

ensure_logs() {
  mkdir -p "$LOG_DIR"
  chown -R ladylinux:ladylinux /var/lib/ladylinux || true
  chmod -R 775 "$LOG_DIR" || true
  touch "$LOG_FILE" || true
  chmod 664 "$LOG_FILE" || true

  # SAFE logging (no condition)
  exec >>"$LOG_FILE" 2>&1 || exec >/dev/null 2>&1
}

ensure_logs

echo "[refresh] starting branch=${BRANCH}"

# 🔥 THIS is the real fix
trap 'echo "[refresh] EXIT — forcing restart"; systemctl start "$SERVICE_NAME" >/dev/null 2>&1 || true' EXIT

sleep 2  # allow API request to finish cleanly

echo "[refresh] stopping service"
systemctl stop "$SERVICE_NAME" || true

echo "[refresh] pulling latest changes"
cd "$APP_ROOT"

git fetch --prune origin

if ! git show-ref --verify --quiet "refs/remotes/origin/$BRANCH"; then
  echo "[refresh][ERROR] branch origin/$BRANCH not found"
  exit 1
fi

git checkout -f "$BRANCH" >/dev/null 2>&1 || true
git reset --hard "origin/$BRANCH"

chown -R ladylinux:ladylinux "$APP_ROOT" || true

echo "[refresh] starting service"
systemctl start "$SERVICE_NAME"

# Clear trap if everything succeeded cleanly
trap - EXIT

echo "[refresh] refresh complete"