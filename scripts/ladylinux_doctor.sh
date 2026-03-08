#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="/opt/ladylinux"
VENV_DIR="$APP_ROOT/venv"
SERVICE_USER="ladylinux"
SERVICE_NAME="ladylinux-api.service"

log() {
    echo "[LadyLinux Doctor] $1"
}

# ensure application directory
if [[ ! -d "$APP_ROOT" ]]; then
    log "Application directory missing. Recreating."
    mkdir -p "$APP_ROOT"
    chown "$SERVICE_USER:$SERVICE_USER" "$APP_ROOT"
fi

# ensure repository exists
if [[ ! -d "$APP_ROOT/.git" ]]; then
    log "Repository missing. Recloning."
    sudo -u "$SERVICE_USER" git clone https://github.com/Brown-DJ/LadyLinux_test.git "$APP_ROOT"
fi

# ensure venv exists
if [[ ! -d "$VENV_DIR" ]]; then
    log "Virtual environment missing. Rebuilding."
    sudo -u "$SERVICE_USER" python3 -m venv "$VENV_DIR"
fi

# ensure dependencies
log "Checking Python dependencies"
sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install -r "$APP_ROOT/requirements.txt"

# ensure permissions
log "Fixing ownership"
chown -R "$SERVICE_USER:$SERVICE_USER" "$APP_ROOT"

# ensure services exist
if ! systemctl list-unit-files | grep -q "$SERVICE_NAME"; then
    log "API service missing."
fi

log "Checking service status"

if ! systemctl is-active "$SERVICE_NAME" >/dev/null; then
    log "API service not running. Restarting."
    systemctl restart "$SERVICE_NAME"
fi

log "Environment verified."
