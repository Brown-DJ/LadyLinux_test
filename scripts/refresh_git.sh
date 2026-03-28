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

  # Fix: use >> redirect directly instead of exec — exec exits on failure
  # under set -e when the file descriptor can't be opened cleanly as root.
  # All subsequent echo/git output goes to the log via tee or direct append.
}

ensure_logs

# Fix: redirect entire script output to log after ensure_logs succeeds.
# Using a subshell wrapper avoids exec's silent-exit-on-failure behavior.
{

echo "[refresh] starting branch=${BRANCH}"

trap 'echo "[refresh] EXIT — forcing restart"; systemctl start "$SERVICE_NAME" >/dev/null 2>&1 || true' EXIT

sleep 2  # allow API request to finish cleanly

echo "[refresh] stopping service"
systemctl stop "$SERVICE_NAME" || true

echo "[refresh] pulling latest changes"

# Fix: add safe.directory so git accepts the ladylinux-owned repo when
# refresh_git.sh runs as root via sudo. Without this, git refuses entirely.
git config --global --add safe.directory "$APP_ROOT" 2>/dev/null || true

cd "$APP_ROOT" || {
  echo "[refresh][ERROR] failed to cd into $APP_ROOT"
  exit 1
}

echo "[debug] user=$(whoami)"
echo "[debug] pwd=$(pwd)"
echo "[debug] repo status:"
git status || true

git fetch --prune origin

if ! git show-ref --verify --quiet "refs/remotes/origin/$BRANCH"; then
  echo "[refresh][ERROR] branch origin/$BRANCH not found"
  exit 1
fi

git checkout -f "$BRANCH"
git reset --hard "origin/$BRANCH"

chown -R ladylinux:ladylinux "$APP_ROOT" || true

echo "[refresh] starting service"
systemctl start "$SERVICE_NAME"

echo "[refresh] commit: $(git rev-parse --short HEAD)"

trap - EXIT

echo "[refresh] refresh complete"

} >> "$LOG_FILE" 2>&1  # all output from the block goes to log; no exec needed
