#!/usr/bin/env bash
set -Eeuo pipefail

log() {
  echo "[LadyLinux] $1"
}

ROOT_DIR="/opt/ladylinux"
APP_DIR="$ROOT_DIR/app"
VENV_DIR="$ROOT_DIR/venv"
SCRIPTS_DIR="$ROOT_DIR/scripts"
LOG_DIR="$ROOT_DIR/logs"
SERVICE_USER="ladylinux"

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  log "Run as root."
  exit 1
fi

mkdir -p "$APP_DIR" "$VENV_DIR" "$SCRIPTS_DIR/archive/legacy" "$LOG_DIR"

if ! id "$SERVICE_USER" >/dev/null 2>&1; then
  useradd --system --home "$ROOT_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"
fi

chown -R "$SERVICE_USER:$SERVICE_USER" "$ROOT_DIR"

if [[ -f "$APP_DIR/requirements.txt" ]]; then
  sudo -u "$SERVICE_USER" python3 -m venv "$VENV_DIR"
  sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install --upgrade pip wheel setuptools
  sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt"
fi

find /opt/ladylinux/scripts -type f -name "*.sh" -exec chmod +x {} \;

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git update-index --chmod=+x scripts/*.sh || true
fi

log "Install complete."
