#!/usr/bin/env bash
set -Eeuo pipefail

log() {
  echo "[LadyLinux] $1"
}

ROOT_DIR="/opt/ladylinux"
APP_DIR="$ROOT_DIR/app"
SERVICE_USER="ladylinux"
BRANCH="${1:-main}"

if [[ ! -d "$APP_DIR/.git" ]]; then
  log "Git repository not found at $APP_DIR"
  exit 1
fi

cd "$APP_DIR"

log "Fetching branch $BRANCH"
sudo -u "$SERVICE_USER" git fetch origin
sudo -u "$SERVICE_USER" git checkout "$BRANCH"
sudo -u "$SERVICE_USER" git reset --hard "origin/$BRANCH"
sudo -u "$SERVICE_USER" git clean -fd

log "Git refresh complete."
