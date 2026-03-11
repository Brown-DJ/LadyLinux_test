#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="/opt/ladylinux"
VENV_DIR="/opt/ladylinux/venv"
SERVICE="ladylinux-api.service"
LLM_SERVICE="ladylinux-llm.service"
SERVICE_USER="ladylinux"
API_PORT="8000"

BRANCH="${1:-main}"

log() { echo "[refresh] $*"; }
chown -R "$SERVICE_USER:$SERVICE_USER" "$APP_DIR" || true
require_root() {
 if [[ "$EUID" -ne 0 ]]; then
  echo "Run with sudo"
  exit 1
 fi
}

stop_services() {

 log "Stopping LadyLinux services"

 systemctl stop "$SERVICE" || true
 systemctl stop "$LLM_SERVICE" || true

 pkill -f "uvicorn api_layer:app" || true
}

sync_repo() {

 log "Updating repository"

 cd "$APP_DIR"

 sudo -u "$SERVICE_USER" git fetch origin
 sudo -u "$SERVICE_USER" git checkout "$BRANCH"
 sudo -u "$SERVICE_USER" git reset --hard "origin/$BRANCH"
 sudo -u "$SERVICE_USER" git clean -fd
}

repair_venv() {

 log "Checking Python environment"

 if [[ ! -f "$VENV_DIR/bin/python" ]]; then
  log "Broken or missing venv — rebuilding"

  # remove broken environment
  rm -rf "$VENV_DIR"

  # recreate directory with correct ownership
  mkdir -p "$VENV_DIR"
  chown -R "$SERVICE_USER:$SERVICE_USER" "$VENV_DIR"

  # create venv as service user
  sudo -u "$SERVICE_USER" python3 -m venv "$VENV_DIR"

 fi
}

install_dependencies() {

 log "Installing dependencies"

 "$VENV_DIR/bin/pip" install --upgrade pip wheel setuptools

 sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt"
}

restart_services() {

 log "Restarting Ollama runtime"

 systemctl restart "$LLM_SERVICE"

 log "Restarting API"

 systemctl restart "$SERVICE"
}

validate_api() {

 log "Checking API"

 sleep 3

 lsof -i :"$API_PORT" || {
  echo "API failed to start"
  exit 1
 }

 curl --silent http://127.0.0.1:$API_PORT >/dev/null || true
}

main() {

 require_root

 stop_services
 sync_repo
 repair_venv
 install_dependencies
 restart_services
 validate_api

 log "Refresh complete"
}

main "$@"
