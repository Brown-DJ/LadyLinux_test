#!/usr/bin/env bash
set -Eeuo pipefail

log() {
  echo "[LadyLinux] $1"
}

ROOT_DIR="/opt/ladylinux"
APP_DIR="$ROOT_DIR/app"
SCRIPTS_DIR="$ROOT_DIR/scripts"
LOG_DIR="$ROOT_DIR/logs"
VENV_DIR="$ROOT_DIR/venv"
SERVICE_USER="ladylinux"
API_SERVICE="ladylinux-api.service"
LLM_SERVICE="ladylinux-llm.service"
API_PORT="${API_PORT:-8000}"
BRANCH="${1:-main}"

require_root() {
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    log "Run as root."
    exit 1
  fi
}

use_systemd() {
  command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files >/dev/null 2>&1
}

stop_runtime() {
  if use_systemd; then
    log "Stopping services."
    systemctl stop "$API_SERVICE" || true
    systemctl stop "$LLM_SERVICE" || true
  else
    log "Stopping fallback processes."
    pkill -f "uvicorn api_layer.app:app" || true
    pkill -f "llm_runtime.py" || true
  fi
}

ensure_layout() {
  mkdir -p "$ROOT_DIR" "$APP_DIR" "$SCRIPTS_DIR" "$LOG_DIR"
  if id "$SERVICE_USER" >/dev/null 2>&1; then
    chown -R "$SERVICE_USER:$SERVICE_USER" "$ROOT_DIR" || true
  fi
}

run_fix_bom() {
  if [[ -x "$SCRIPTS_DIR/fix_bom.sh" ]]; then
    log "Removing BOM from scripts and sources."
    "$SCRIPTS_DIR/fix_bom.sh"
  fi
}

sync_git() {
  if [[ ! -x "$SCRIPTS_DIR/refresh_git.sh" ]]; then
    log "Missing $SCRIPTS_DIR/refresh_git.sh"
    exit 1
  fi

  log "Configuring git safe.directory."
  sudo -u "$SERVICE_USER" git config --global --add safe.directory "$APP_DIR" || true

  log "Running git refresh for branch $BRANCH."
  "$SCRIPTS_DIR/refresh_git.sh" "$BRANCH"
}

deps_changed() {
  if [[ ! -f "$APP_DIR/requirements.txt" ]]; then
    log "requirements.txt not found in $APP_DIR"
    exit 1
  fi

  local new_fp old_fp
  new_fp="$(sha256sum "$APP_DIR/requirements.txt" | awk '{print $1}')"
  old_fp=""

  if [[ -f "$APP_DIR/.deps_fingerprint" ]]; then
    old_fp="$(awk '{print $1}' "$APP_DIR/.deps_fingerprint" 2>/dev/null || true)"
  fi

  if [[ ! -x "$VENV_DIR/bin/python" || "$new_fp" != "$old_fp" ]]; then
    return 0
  fi

  return 1
}

repair_venv() {
  log "Rebuilding virtual environment and dependencies."
  rm -rf "$VENV_DIR"
  sudo -u "$SERVICE_USER" python3 -m venv "$VENV_DIR"
  sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install --upgrade pip wheel setuptools
  sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt"

  sudo -u "$SERVICE_USER" bash -lc "cd '$APP_DIR' && sha256sum requirements.txt > .deps_fingerprint"
}

start_runtime() {
  if use_systemd; then
    log "Starting runtime via systemd."
    systemctl daemon-reload
    systemctl enable "$API_SERVICE" || true
    systemctl restart "$LLM_SERVICE" || true
    systemctl restart "$API_SERVICE"
  else
    log "Systemd unavailable; starting fallback uvicorn runtime."
    mkdir -p "$LOG_DIR"
    nohup "$VENV_DIR/bin/python" "$APP_DIR/llm_runtime.py" > "$LOG_DIR/llm_runtime.log" 2>&1 &
    nohup "$VENV_DIR/bin/python" -m uvicorn api_layer.app:app --host 0.0.0.0 --port "$API_PORT" > "$LOG_DIR/api.log" 2>&1 &
  fi
}

validate_runtime() {
  local url="http://127.0.0.1:$API_PORT"
  sleep 3

  if ! ss -ltn | awk '{print $4}' | grep -Eq "[:.]$API_PORT$"; then
    log "API port $API_PORT is not listening."
    exit 1
  fi

  curl -fsS "$url" >/dev/null || true
  log "Runtime validated on $url"
}

launch_ui() {
  local ui_url="http://127.0.0.1:$API_PORT"
  if command -v xdg-open >/dev/null 2>&1 && [[ -n "${DISPLAY:-}" ]]; then
    xdg-open "$ui_url" >/dev/null 2>&1 || true
  fi
  log "UI URL: $ui_url"
}

main() {
  require_root
  ensure_layout
  run_fix_bom
  stop_runtime
  sync_git

  if deps_changed; then
    repair_venv
  else
    log "Dependency fingerprint unchanged; venv rebuild skipped."
  fi

  start_runtime
  validate_runtime
  launch_ui
  log "Refresh complete."
}

main "$@"
