#!/usr/bin/env bash
set -Eeuo pipefail

# ==============================================================================
# LadyLinux Installer (patched)
# ==============================================================================

REPO_URL="https://github.com/Brown-DJ/LadyLinux_test.git"
BRANCH="${BRANCH:-main}"

APP_ROOT="/opt/ladylinux"
VENV_DIR="$APP_ROOT/venv"
LOG_DIR="$APP_ROOT/logs"
SCRIPTS_DIR="$APP_ROOT/scripts"

SERVICE_USER="ladylinux"
SERVICE_NAME="ladylinux-api.service"

API_HOST="0.0.0.0"
API_PORT="8000"
UVICORN_MODULE="api_layer:app"

log() {
    echo
    echo "[LadyLinux Install] $1"
    echo
}

require_root() {
    if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
        echo "Run with sudo."
        exit 1
    fi
}

detect_python() {
    if command -v python3.12 >/dev/null 2>&1; then
        echo python3.12
    else
        echo python3
    fi
}

install_system_packages() {
    log "Installing system dependencies"

    apt update -y
    apt install -y \
        git curl ca-certificates build-essential \
        python3 python3-venv python3-pip systemd
}

ensure_service_user() {
    if ! id "$SERVICE_USER" >/dev/null 2>&1; then
        log "Creating service user"
        useradd --system --home "$APP_ROOT" --shell /usr/sbin/nologin "$SERVICE_USER"
    fi
}

prepare_directories() {
    log "Preparing directories"

    mkdir -p "$APP_ROOT" "$LOG_DIR" "$SCRIPTS_DIR/archive/legacy"

    chown -R "$SERVICE_USER:$SERVICE_USER" "$APP_ROOT"
}
setup_repo() {

    log "Preparing repository"

    if [[ ! -d "$APP_ROOT/.git" ]]; then
        log "Cloning repository"
        rm -rf "$APP_ROOT"

        # run clone as service user
        sudo -u "$SERVICE_USER" git clone "$REPO_URL" "$APP_ROOT"
    fi

    cd "$APP_ROOT"

    # run ALL git commands as service user
    sudo -u "$SERVICE_USER" git fetch origin
    sudo -u "$SERVICE_USER" git checkout "$BRANCH"
    sudo -u "$SERVICE_USER" git reset --hard "origin/$BRANCH"

    # optional safety (won’t hurt, but should already be correct now)
    chown -R "$SERVICE_USER:$SERVICE_USER" "$APP_ROOT"
}

setup_venv() {
    log "Setting up virtual environment"

    PYTHON_BIN=$(detect_python)

    if [[ ! -d "$VENV_DIR" ]]; then
        sudo -u "$SERVICE_USER" $PYTHON_BIN -m venv "$VENV_DIR"
    fi

    sudo -u "$SERVICE_USER" "$VENV_DIR/bin/python" -m pip install --upgrade pip wheel setuptools
}

install_requirements() {
    log "Installing Python requirements"

    REQUIREMENTS_FILE="$APP_ROOT/requirements.txt"

    if [[ ! -f "$REQUIREMENTS_FILE" ]]; then
        echo "requirements.txt not found"
        exit 1
    fi

    sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install -r "$REQUIREMENTS_FILE"

    log "Verifying qdrant-client"
    sudo -u "$SERVICE_USER" "$VENV_DIR/bin/python" -c "import qdrant_client"
}

fix_permissions() {
    log "Fixing permissions"
    chown -R "$SERVICE_USER:$SERVICE_USER" "$APP_ROOT"

    if [[ -d "$SCRIPTS_DIR" ]]; then
        find "$SCRIPTS_DIR" -type f -name "*.sh" -exec chmod +x {} \;
    fi
}

create_service() {
    log "Creating systemd service"

    SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"

    cat > "$SERVICE_PATH" <<EOF
[Unit]
Description=LadyLinux API
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$APP_ROOT
Environment=PYTHONUNBUFFERED=1

ExecStart=$VENV_DIR/bin/uvicorn $UVICORN_MODULE --host $API_HOST --port $API_PORT

Restart=always
RestartSec=3

StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
}

start_service() {
    log "Starting service"
    systemctl restart "$SERVICE_NAME"
    systemctl --no-pager --full status "$SERVICE_NAME" || true
}

install_ollama() {
    if ! command -v ollama >/dev/null 2>&1; then
        log "Installing Ollama"
        curl -fsSL https://ollama.com/install.sh | sh
    fi

    systemctl enable --now ollama || true
    sleep 3

    if ! ollama list | grep -q "nomic-embed-text"; then
        ollama pull nomic-embed-text
    fi

    if ! ollama list | grep -q "^mistral"; then
        ollama pull mistral
    fi
}

main() {
    require_root

    install_system_packages
    ensure_service_user
    prepare_directories
    setup_repo
    setup_venv
    install_requirements
    fix_permissions
    create_service
    start_service
    install_ollama

    log "Installation complete"

    echo "API endpoint:"
    echo "http://127.0.0.1:$API_PORT"
    echo
    echo "Logs:"
    echo "journalctl -u $SERVICE_NAME -f"
}

main