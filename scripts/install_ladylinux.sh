#!/usr/bin/env bash
# ==============================================================================
# LadyLinux Full System Installer
# Repo:    https://github.com/Brown-DJ/LadyLinux_test.git
# Branch:  main (override via BRANCH=develop ./install_ladylinux.sh)
#
# What this installer does:
#   1.  Pre-flight checks (root, OS, internet)
#   2.  Install system packages (git, python3, curl, dos2unix, chromium, avahi)
#   3.  Create service user & directories
#   4.  Set hostname to "ladylinux" (if currently "localhost")
#   5.  Clone / update the GitHub repository
#   6.  Create Python virtual environment
#   7.  Install Python requirements
#   8.  Fix permissions
#   9.  Install Ollama runtime + pull mistral & nomic-embed-text models
#   10. Write systemd units (ladylinux-api.service, ladylinux-llm.service)
#   11. Create desktop launcher (.desktop + launch_ladylinux.sh)
#   12. Enable & start services
#   13. Validate API is listening
#   14. Print access URLs
#
# What this installer does NOT do:
#   - Reinstall or modify the OS
#   - Delete existing model weights or application state
#   - Overwrite /etc/ladylinux/ladylinux.env if it already exists
#
# Usage:
#   sudo bash install_ladylinux.sh
#   sudo BRANCH=develop bash install_ladylinux.sh
#   sudo bash install_ladylinux.sh --dry-run
#   sudo bash install_ladylinux.sh --skip-models
#
# Exit codes:
#   0  success
#   1  generic failure
#   2  missing prerequisite / bad environment
# ==============================================================================

set -Eeuo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# Configuration  (edit here or export as environment variables before running)
# ─────────────────────────────────────────────────────────────────────────────

REPO_URL="https://github.com/Brown-DJ/LadyLinux_test.git"
BRANCH="${BRANCH:-main}"

APP_ROOT="/opt/ladylinux"
VENV_DIR="$APP_ROOT/venv"
ETC_DIR="/etc/ladylinux"
VAR_DIR="/var/lib/ladylinux"

SERVICE_USER="ladylinux"
SERVICE_NAME="ladylinux-api.service"
LLM_SERVICE_NAME="ladylinux-llm.service"

API_HOST="0.0.0.0"
API_PORT="8000"
OLLAMA_HOST="127.0.0.1:11434"
UVICORN_MODULE="api_layer:app"

DRY_RUN="false"
SKIP_MODELS="false"

# ─────────────────────────────────────────────────────────────────────────────
# Argument parsing
# ─────────────────────────────────────────────────────────────────────────────

usage() {
  cat <<EOF
LadyLinux Installer

Usage:
  sudo bash install_ladylinux.sh [options]

Options:
  --dry-run        Print actions without making any changes
  --skip-models    Skip downloading Ollama LLM model weights
  --branch <name>  Git branch to install (default: main)
  -h, --help       Show this help text

Environment overrides:
  BRANCH=<name>    Same as --branch
EOF
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --dry-run)       DRY_RUN="true";            shift ;;
      --skip-models)   SKIP_MODELS="true";        shift ;;
      --branch)        BRANCH="${2:-main}";        shift 2 ;;
      -h|--help)       usage; exit 0 ;;
      *)               die "Unknown argument: $1 (use --help)" 2 ;;
    esac
  done
}

# ─────────────────────────────────────────────────────────────────────────────
# Logging helpers
# ─────────────────────────────────────────────────────────────────────────────

BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
RESET="\033[0m"

log()  { printf "${GREEN}[install]${RESET} %s\n"        "$*"; }
warn() { printf "${YELLOW}[install][WARN]${RESET} %s\n" "$*" >&2; }
die()  { printf "${RED}[install][ERROR]${RESET} %s\n"   "$*" >&2; exit "${2:-1}"; }
step() { printf "\n${BOLD}══ %s ══${RESET}\n"           "$*"; }

run() {
  if [[ "$DRY_RUN" == "true" ]]; then
    log "DRY-RUN: $*"
  else
    "$@"
  fi
}

run_as_service() {
  if [[ "$DRY_RUN" == "true" ]]; then
    log "DRY-RUN (as $SERVICE_USER): $*"
  else
    sudo -u "$SERVICE_USER" -- "$@"
  fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Step 1 – Pre-flight checks
# ─────────────────────────────────────────────────────────────────────────────

preflight() {
  step "Pre-flight checks"

  # Root
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    die "This installer must be run as root. Use: sudo bash $0" 2
  fi

  # OS / package manager
  if ! command -v apt >/dev/null 2>&1; then
    warn "apt not detected. This installer targets Debian/Ubuntu."
    warn "Package installation may fail. Proceeding anyway."
  fi

  # Internet connectivity (lightweight check)
  if ! curl --silent --max-time 5 https://github.com >/dev/null 2>&1; then
    warn "Cannot reach github.com. Check your internet connection."
    warn "Continuing in case this is a transient failure."
  fi

  log "Pre-flight checks passed."
}

# ─────────────────────────────────────────────────────────────────────────────
# Step 2 – System packages
# ─────────────────────────────────────────────────────────────────────────────

install_system_packages() {
  step "Installing system packages"

  if [[ "$DRY_RUN" == "true" ]]; then
    log "DRY-RUN: would run apt update and install packages"
    return 0
  fi

  # Wait for dpkg lock to clear (handles cloud-init / unattended-upgrades)
  local waited=0
  while fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1; do
    if (( waited == 0 )); then log "Waiting for package manager lock to clear..."; fi
    sleep 3
    (( waited += 3 ))
    if (( waited > 120 )); then
      die "Package manager lock held for >2 min. Run: sudo lsof /var/lib/dpkg/lock-frontend" 2
    fi
  done

  apt-get update -y -qq

  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    git \
    curl \
    ca-certificates \
    build-essential \
    python3 \
    python3-venv \
    python3-pip \
    dos2unix \
    lsof \
    avahi-daemon \
    libnss-mdns \
    || die "System package installation failed."

  # Chromium – try apt first, snap as fallback
  if ! command -v chromium >/dev/null 2>&1 && ! command -v chromium-browser >/dev/null 2>&1; then
    log "Installing Chromium browser..."
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
      chromium-browser fonts-liberation libgtk-3-0 2>/dev/null \
    || snap install chromium 2>/dev/null \
    || warn "Chromium install failed. The desktop launcher will be unavailable."
  else
    log "Chromium already installed — skipping."
  fi

  # Enable mDNS so machine is reachable at ladylinux.local
  systemctl enable --now avahi-daemon 2>/dev/null || true

  log "System packages installed."
}

# ─────────────────────────────────────────────────────────────────────────────
# Step 3 – Service user
# ─────────────────────────────────────────────────────────────────────────────

ensure_service_user() {
  step "Service user"

  if id "$SERVICE_USER" >/dev/null 2>&1; then
    log "User '$SERVICE_USER' already exists — skipping creation."
    return 0
  fi

  log "Creating system user: $SERVICE_USER"
  run useradd \
    --system \
    --create-home \
    --home-dir "/home/$SERVICE_USER" \
    --shell /usr/sbin/nologin \
    "$SERVICE_USER"
}

# ─────────────────────────────────────────────────────────────────────────────
# Step 4 – Directory layout
# ─────────────────────────────────────────────────────────────────────────────

create_directories() {
  step "Creating directory layout"

  run mkdir -p \
    "$APP_ROOT"/{app,venv,models,containers} \
    "$VAR_DIR"/{data,cache,logs} \
    "$ETC_DIR"

  if [[ "$DRY_RUN" != "true" ]]; then
    chown -R "$SERVICE_USER:$SERVICE_USER" "$APP_ROOT" "$VAR_DIR"
    chmod 750 "$ETC_DIR"
  fi

  # Create a template env file if none exists
  if [[ ! -f "$ETC_DIR/ladylinux.env" ]]; then
    log "Writing template env file: $ETC_DIR/ladylinux.env"
    run bash -c "cat > '$ETC_DIR/ladylinux.env' <<'ENVEOF'
# LadyLinux environment configuration
# Lines beginning with # are comments.
# Uncomment and set values as needed.

# OLLAMA_HOST=127.0.0.1:11434
# API_PORT=8000
ENVEOF"
    run chmod 640 "$ETC_DIR/ladylinux.env"
  else
    log "Env file already exists — skipping: $ETC_DIR/ladylinux.env"
  fi

  log "Directory layout ready."
}

# ─────────────────────────────────────────────────────────────────────────────
# Step 5 – Hostname
# ─────────────────────────────────────────────────────────────────────────────

set_hostname() {
  step "Hostname"

  local current
  current="$(hostname 2>/dev/null || true)"

  if [[ "$current" == "localhost" || "$current" == "localhost.localdomain" ]]; then
    log "Current hostname is '$current' — setting to 'ladylinux'"
    run hostnamectl set-hostname ladylinux
  else
    log "Hostname is '$current' — leaving unchanged."
  fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Step 6 – Repository
# ─────────────────────────────────────────────────────────────────────────────

setup_repo() {
  step "Repository (branch: $BRANCH)"

  if [[ "$DRY_RUN" == "true" ]]; then
    log "DRY-RUN: would clone/sync $REPO_URL → $APP_ROOT"
    return 0
  fi

  # Configure git safe.directory so service user can operate on root-owned clone
  run_as_service git config --global --add safe.directory "$APP_ROOT" 2>/dev/null || true

  if [[ ! -d "$APP_ROOT/.git" ]]; then
    log "Cloning $REPO_URL into $APP_ROOT"
    run_as_service git clone "$REPO_URL" "$APP_ROOT"
    # Fix Windows line-endings in scripts after fresh clone
    find "$APP_ROOT" -type f -name "*.sh" -exec dos2unix --quiet {} + 2>/dev/null || true
    find "$APP_ROOT" -type f -name "*.py"  -exec dos2unix --quiet {} + 2>/dev/null || true
  else
    log "Repository already cloned — fetching latest changes."
  fi

  run_as_service git -C "$APP_ROOT" fetch --prune origin

  # Validate branch exists on remote before hard-resetting
  if ! run_as_service git -C "$APP_ROOT" show-ref --verify --quiet "refs/remotes/origin/$BRANCH"; then
    die "Branch '$BRANCH' not found on remote $REPO_URL" 2
  fi

  run_as_service git -C "$APP_ROOT" checkout -f "$BRANCH" 2>/dev/null || true
  run_as_service git -C "$APP_ROOT" reset --hard "origin/$BRANCH"
  run_as_service git -C "$APP_ROOT" clean -fd

  local commit
  commit="$(run_as_service git -C "$APP_ROOT" rev-parse --short HEAD)"
  log "Repository at commit $commit on branch $BRANCH."
}

# ─────────────────────────────────────────────────────────────────────────────
# Step 7 – Python virtual environment
# ─────────────────────────────────────────────────────────────────────────────

setup_venv() {
  step "Python virtual environment"

  if [[ "$DRY_RUN" == "true" ]]; then
    log "DRY-RUN: would create venv at $VENV_DIR"
    return 0
  fi

  # Pick the best available Python
  local py
  if   command -v python3.12 >/dev/null 2>&1; then py="python3.12"
  elif command -v python3.11 >/dev/null 2>&1; then py="python3.11"
  elif command -v python3    >/dev/null 2>&1; then py="python3"
  else die "No Python 3 interpreter found." 2
  fi
  log "Using Python: $py ($(command -v "$py"))"

  if [[ ! -d "$VENV_DIR" || ! -x "$VENV_DIR/bin/python" ]]; then
    log "Creating virtual environment at $VENV_DIR"
    rm -rf "$VENV_DIR"
    mkdir -p "$VENV_DIR"
    chown "$SERVICE_USER:$SERVICE_USER" "$VENV_DIR"
    run_as_service "$py" -m venv --system-site-packages "$VENV_DIR"
  else
    log "Virtual environment already exists — skipping creation."
  fi

  [[ -x "$VENV_DIR/bin/python" ]] || die "Virtual environment creation failed." 1
  log "Virtual environment ready."
}

# ─────────────────────────────────────────────────────────────────────────────
# Step 8 – Python requirements
# ─────────────────────────────────────────────────────────────────────────────

install_requirements() {
  step "Python requirements"

  if [[ "$DRY_RUN" == "true" ]]; then
    log "DRY-RUN: would install requirements into $VENV_DIR"
    return 0
  fi

  run_as_service "$VENV_DIR/bin/python" -m pip install --quiet --upgrade pip wheel setuptools

  if [[ -f "$APP_ROOT/requirements.txt" ]]; then
    log "Installing from requirements.txt"
    run_as_service "$VENV_DIR/bin/pip" install --quiet -r "$APP_ROOT/requirements.txt"
  else
    warn "requirements.txt not found — installing fallback runtime stack."
    run_as_service "$VENV_DIR/bin/pip" install --quiet \
      fastapi uvicorn requests jinja2 python-multipart
  fi

  log "Python requirements installed."
}

# ─────────────────────────────────────────────────────────────────────────────
# Step 9 – Permissions
# ─────────────────────────────────────────────────────────────────────────────

fix_permissions() {
  step "Permissions"

  run chown -R "$SERVICE_USER:$SERVICE_USER" "$APP_ROOT" "$VAR_DIR"

  # Make all shell scripts executable
  find "$APP_ROOT" -type f -name "*.sh" -exec chmod +x {} + 2>/dev/null || true

  log "Permissions set."
}

# ─────────────────────────────────────────────────────────────────────────────
# Step 10 – Ollama runtime
# ─────────────────────────────────────────────────────────────────────────────

install_ollama() {
  step "Ollama LLM runtime"

  if [[ "$DRY_RUN" == "true" ]]; then
    log "DRY-RUN: would install Ollama and pull mistral + nomic-embed-text"
    return 0
  fi

  if ! command -v ollama >/dev/null 2>&1; then
    log "Downloading and installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh \
      || die "Ollama installation failed." 1
  else
    log "Ollama already installed: $(ollama --version 2>/dev/null || echo 'version unknown')"
  fi

  log "Ollama installed."
}

pull_models() {
  step "Ollama model weights"

  if [[ "$SKIP_MODELS" == "true" ]]; then
    log "--skip-models flag set. Skipping model downloads."
    return 0
  fi

  if [[ "$DRY_RUN" == "true" ]]; then
    log "DRY-RUN: would pull mistral and nomic-embed-text models"
    return 0
  fi

  # Ensure the LLM service is running so 'ollama pull' can talk to the daemon
  systemctl daemon-reload 2>/dev/null || true
  systemctl enable "$LLM_SERVICE_NAME" 2>/dev/null || true
  systemctl restart "$LLM_SERVICE_NAME" || true

  log "Waiting for Ollama daemon to be ready..."
  local attempts=30
  while (( attempts > 0 )); do
    if curl --silent --fail --max-time 2 "http://$OLLAMA_HOST" >/dev/null 2>&1; then
      break
    fi
    sleep 2
    (( attempts-- ))
  done

  if ! curl --silent --fail --max-time 2 "http://$OLLAMA_HOST" >/dev/null 2>&1; then
    warn "Ollama daemon did not respond. Skipping model downloads."
    warn "Run manually after start: ollama pull mistral && ollama pull nomic-embed-text"
    return 0
  fi

  if ! ollama list 2>/dev/null | grep -q "^mistral"; then
    log "Pulling mistral model (this may take several minutes)..."
    ollama pull mistral || warn "mistral pull failed. Run manually: ollama pull mistral"
  else
    log "mistral model already present — skipping."
  fi

  if ! ollama list 2>/dev/null | grep -q "nomic-embed-text"; then
    log "Pulling nomic-embed-text embedding model..."
    ollama pull nomic-embed-text \
      || warn "nomic-embed-text pull failed. Run manually: ollama pull nomic-embed-text"
  else
    log "nomic-embed-text model already present — skipping."
  fi

  log "Model weights ready."
}

# ─────────────────────────────────────────────────────────────────────────────
# Step 11 – Systemd units
# ─────────────────────────────────────────────────────────────────────────────

write_llm_service() {
  local dest="/etc/systemd/system/$LLM_SERVICE_NAME"
  local src="$APP_ROOT/scripts/testbranchscripts/ladylinux-llm.service"

  # Prefer unit file shipped in repo if it exists
  if [[ -f "$src" ]]; then
    log "Installing LLM service unit from repo: $src"
    run install -m 0644 "$src" "$dest"
  else
    log "Writing LLM service unit: $dest"
    run bash -c "cat > '$dest' <<'UNITEOF'
[Unit]
Description=LadyLinux LLM Runtime (Ollama)
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/usr/bin/ollama serve
Restart=always
RestartSec=3
User=root
Environment=\"OLLAMA_HOST=$OLLAMA_HOST\"

StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
UNITEOF"
  fi
}

write_api_service() {
  local dest="/etc/systemd/system/$SERVICE_NAME"
  log "Writing API service unit: $dest"
  run bash -c "cat > '$dest' <<UNITEOF
[Unit]
Description=LadyLinux API
After=network-online.target $LLM_SERVICE_NAME
Wants=network-online.target
Requires=$LLM_SERVICE_NAME

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$APP_ROOT
EnvironmentFile=-$ETC_DIR/ladylinux.env
Environment=PYTHONUNBUFFERED=1

ExecStart=$VENV_DIR/bin/python -m uvicorn $UVICORN_MODULE --host $API_HOST --port $API_PORT

Restart=always
RestartSec=3

StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
UNITEOF"
}

install_services() {
  step "Systemd service units"

  if [[ "$DRY_RUN" == "true" ]]; then
    log "DRY-RUN: would write and enable $SERVICE_NAME and $LLM_SERVICE_NAME"
    return 0
  fi

  write_llm_service
  write_api_service

  systemctl daemon-reload

  systemctl enable "$LLM_SERVICE_NAME"
  systemctl enable "$SERVICE_NAME"

  log "Service units installed and enabled."
}

# ─────────────────────────────────────────────────────────────────────────────
# Step 12 – Desktop launcher
# ─────────────────────────────────────────────────────────────────────────────

setup_desktop_launcher() {
  step "Desktop launcher"

  if [[ "$DRY_RUN" == "true" ]]; then
    log "DRY-RUN: would create launch_ladylinux.sh and ladylinux.desktop"
    return 0
  fi

  # Launcher shell script
  local launcher="$APP_ROOT/launch_ladylinux.sh"
  cat > "$launcher" <<'LAUNCHEOF'
#!/usr/bin/env bash
APP_DIR="/opt/ladylinux"
PYTHON="$APP_DIR/venv/bin/python"
SCRIPT="$APP_DIR/scripts/testbranchscripts/start_ladylinux.py"
exec "$PYTHON" "$SCRIPT"
LAUNCHEOF
  chmod +x "$launcher"
  chown "$SERVICE_USER:$SERVICE_USER" "$launcher"

  # System-wide .desktop entry
  cat > /usr/share/applications/ladylinux.desktop <<'DESKEOF'
[Desktop Entry]
Name=Lady Linux
Comment=LadyLinux System Control Interface
Exec=/opt/ladylinux/launch_ladylinux.sh
Icon=utilities-terminal
Terminal=false
Type=Application
Categories=System;Utility;
StartupNotify=true
DESKEOF

  log "Desktop launcher created."
}

# ─────────────────────────────────────────────────────────────────────────────
# Step 13 – Start services
# ─────────────────────────────────────────────────────────────────────────────

start_services() {
  step "Starting services"

  if [[ "$DRY_RUN" == "true" ]]; then
    log "DRY-RUN: would start $LLM_SERVICE_NAME and $SERVICE_NAME"
    return 0
  fi

  log "Starting LLM service ($LLM_SERVICE_NAME)..."
  systemctl restart "$LLM_SERVICE_NAME" \
    || warn "LLM service failed to start. Check: journalctl -u $LLM_SERVICE_NAME -n 50"

  log "Starting API service ($SERVICE_NAME)..."
  systemctl restart "$SERVICE_NAME" \
    || warn "API service failed to start. Check: journalctl -u $SERVICE_NAME -n 50"
}

# ─────────────────────────────────────────────────────────────────────────────
# Step 14 – Validate & summarize
# ─────────────────────────────────────────────────────────────────────────────

validate_and_summarize() {
  step "Validation"

  if [[ "$DRY_RUN" == "true" ]]; then
    log "DRY-RUN: would wait for port $API_PORT to open"
    return 0
  fi

  log "Waiting for API to start on port $API_PORT..."
  local attempts=20
  local ready=0
  while (( attempts > 0 )); do
    if lsof -i :"$API_PORT" >/dev/null 2>&1; then
      ready=1
      break
    fi
    sleep 2
    (( attempts-- ))
  done

  if [[ "$ready" -ne 1 ]]; then
    warn "API port $API_PORT did not open within the timeout."
    warn "Inspect logs: journalctl -u $SERVICE_NAME -n 100 --no-pager"
  else
    log "API is listening on port $API_PORT."
  fi

  local host_ip
  host_ip="$(hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")"

  printf "\n"
  printf "${BOLD}╔══════════════════════════════════════════╗${RESET}\n"
  printf "${BOLD}║      LadyLinux Installation Complete     ║${RESET}\n"
  printf "${BOLD}╠══════════════════════════════════════════╣${RESET}\n"
  printf "${BOLD}║${RESET}  Branch : %-31s${BOLD}║${RESET}\n" "$BRANCH"
  printf "${BOLD}║${RESET}  App    : %-31s${BOLD}║${RESET}\n" "$APP_ROOT"
  printf "${BOLD}╠══════════════════════════════════════════╣${RESET}\n"
  printf "${BOLD}║${RESET}  ${GREEN}Desktop :${RESET} http://127.0.0.1:%-16s${BOLD}║${RESET}\n" "${API_PORT}"
  printf "${BOLD}║${RESET}  ${GREEN}Network :${RESET} http://%-23s${BOLD}║${RESET}\n" "${host_ip}:${API_PORT}"
  printf "${BOLD}║${RESET}  ${GREEN}mDNS    :${RESET} http://ladylinux.local:%-10s${BOLD}║${RESET}\n" "${API_PORT}"
  printf "${BOLD}╠══════════════════════════════════════════╣${RESET}\n"
  printf "${BOLD}║${RESET}  View API logs:                           ${BOLD}║${RESET}\n"
  printf "${BOLD}║${RESET}    journalctl -u ladylinux-api -f         ${BOLD}║${RESET}\n"
  printf "${BOLD}║${RESET}  Refresh from GitHub:                     ${BOLD}║${RESET}\n"
  printf "${BOLD}║${RESET}    sudo ./scripts/refresh_vm.sh $BRANCH   ${BOLD}║${RESET}\n"
  printf "${BOLD}╚══════════════════════════════════════════╝${RESET}\n"
  printf "\n"
}

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

main() {
  parse_args "$@"

  if [[ "$DRY_RUN" == "true" ]]; then
    warn "DRY-RUN mode enabled — no changes will be made."
  fi

  preflight
  install_system_packages
  ensure_service_user
  create_directories
  set_hostname
  setup_repo
  setup_venv
  install_requirements
  fix_permissions
  install_ollama
  write_llm_service 2>/dev/null || true  # first pass so daemon can start for model pulls
  systemctl daemon-reload 2>/dev/null || true
  systemctl enable "$LLM_SERVICE_NAME"  2>/dev/null || true
  systemctl restart "$LLM_SERVICE_NAME" 2>/dev/null || true
  pull_models
  install_services
  setup_desktop_launcher
  start_services
  validate_and_summarize
}

main "$@"