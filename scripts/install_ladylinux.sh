#!/usr/bin/env bash
set -Eeuo pipefail

log() {
  echo "[LadyLinux] $1"
}

die() {
  echo "[LadyLinux][ERROR] $1"
  exit 1
}

#---------------- CONFIG ----------------#

ROOT_DIR="/opt/ladylinux"
APP_DIR="$ROOT_DIR/app"
VENV_DIR="$ROOT_DIR/venv"
LOG_DIR="$ROOT_DIR/logs"

SERVICE_USER="ladylinux"

REPO_URL="https://github.com/theCodingProfessor/LadyLinux"
BRANCH="brown-dj"   # 🔥 YOUR BRANCH

APP_MODULE="main:app"
PORT="8000"

#---------------- ROOT CHECK ----------------#

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  die "Run as root."
fi

#---------------- PACKAGES ----------------#

log "Installing system packages"
apt-get update
apt-get install -y python3 python3-venv python3-pip git curl

#---------------- DIRECTORIES ----------------#

log "Creating directories"
mkdir -p "$APP_DIR" "$VENV_DIR" "$LOG_DIR"

#---------------- USER ----------------#

if ! id "$SERVICE_USER" >/dev/null 2>&1; then
  log "Creating service user"
  useradd --system --home "$ROOT_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"
fi

chown -R "$SERVICE_USER:$SERVICE_USER" "$ROOT_DIR"

#---------------- GIT SETUP ----------------#

log "Setting git safe directory"
git config --global --add safe.directory "$APP_DIR"

if [[ -d "$APP_DIR/.git" ]]; then
  log "Updating existing repo"
  git -C "$APP_DIR" fetch origin
  git -C "$APP_DIR" checkout "$BRANCH"
  git -C "$APP_DIR" reset --hard "origin/$BRANCH"
else
  log "Cloning repo (branch: $BRANCH)"
  rm -rf "$APP_DIR"
  git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi

chown -R "$SERVICE_USER:$SERVICE_USER" "$APP_DIR"

#---------------- VENV ----------------#

log "Setting up virtual environment"

sudo -u "$SERVICE_USER" python3 -m venv "$VENV_DIR"

sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install --upgrade pip wheel setuptools

if [[ -f "$APP_DIR/requirements.txt" ]]; then
  log "Installing requirements"
  sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt"
else
  log "No requirements.txt found, installing uvicorn manually"
  sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install uvicorn fastapi
fi

#---------------- VERIFY ----------------#

[[ -d "$APP_DIR" ]] || die "App directory missing"
[[ -x "$VENV_DIR/bin/python" ]] || die "Venv failed"

log "Verification passed"

#---------------- OPTIONAL RUN ----------------#

log "Starting test server"

sudo -u "$SERVICE_USER" bash -c "
cd $APP_DIR
$VENV_DIR/bin/python -m uvicorn $APP_MODULE --host 0.0.0.0 --port $PORT
"