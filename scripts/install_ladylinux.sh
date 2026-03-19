#!/usr/bin/env bash
set -Eeuo pipefail

log() { echo "[LadyLinux] $1"; }
die() { echo "[LadyLinux][ERROR] $1"; exit 1; }

ROOT_DIR="/opt/ladylinux"
APP_DIR="$ROOT_DIR/app"
VENV_DIR="$ROOT_DIR/venv"

SERVICE_USER="ladylinux"

REPO_URL="https://github.com/Brown-DJ/LadyLinux_test.git"
BRANCH="main"

PORT="8000"

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  die "Run as root."
fi

log "Installing dependencies"
apt-get update
apt-get install -y python3 python3-venv python3-pip git

log "Creating directories"
mkdir -p "$APP_DIR" "$VENV_DIR"

if ! id "$SERVICE_USER" >/dev/null 2>&1; then
  useradd --system --home "$ROOT_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"
fi

chown -R "$SERVICE_USER:$SERVICE_USER" "$ROOT_DIR"

log "Fixing git safe directory"
git config --global --add safe.directory "$APP_DIR"

if [[ -d "$APP_DIR/.git" ]]; then
  log "Updating repo"
  git -C "$APP_DIR" fetch origin
  git -C "$APP_DIR" checkout "$BRANCH"
  git -C "$APP_DIR" reset --hard "origin/$BRANCH"
else
  log "Cloning repo"
  rm -rf "$APP_DIR"
  git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi

chown -R "$SERVICE_USER:$SERVICE_USER" "$APP_DIR"

# 🔥 AUTO-DETECT APP ROOT
if [[ -d "$APP_DIR/LadyLinux_myine" ]]; then
  RUN_DIR="$APP_DIR/LadyLinux_myine"
else
  RUN_DIR="$APP_DIR"
fi

# 🔥 AUTO-DETECT ENTRYPOINT
if [[ -f "$RUN_DIR/api_layer/app.py" ]]; then
  APP_MODULE="api_layer.app:app"
elif [[ -f "$RUN_DIR/api_layer.py" ]]; then
  APP_MODULE="api_layer:app"
else
  die "Could not find FastAPI entrypoint"
fi

log "Using app module: $APP_MODULE"
log "Run directory: $RUN_DIR"

log "Setting up venv"
sudo -u "$SERVICE_USER" python3 -m venv "$VENV_DIR"

sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install --upgrade pip wheel setuptools

REQ_FILE="$(find "$RUN_DIR" -maxdepth 2 -name requirements.txt | head -n 1 || true)"

if [[ -n "$REQ_FILE" ]]; then
  log "Installing requirements"
  sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install -r "$REQ_FILE"
else
  log "No requirements → installing FastAPI + Uvicorn"
  sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install fastapi uvicorn requests jinja2
fi

log "Starting server"

sudo -u "$SERVICE_USER" bash -c "
cd $RUN_DIR
$VENV_DIR/bin/python -m uvicorn $APP_MODULE --host 0.0.0.0 --port $PORT
"