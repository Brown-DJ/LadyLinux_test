#!/usr/bin/env bash
#===============================================================================
# LadyLinux Installer
# File: install_ladylinux.sh
#
# Purpose:
#   Install and prepare a LadyLinux deployment on a fresh Debian/Ubuntu/Linux
#   Mint style machine.
#
# What this script does:
#   - Validates root access
#   - Installs required OS packages
#   - Creates a dedicated service user/group
#   - Creates required directories under /opt, /var, /etc
#   - Clones OR updates the repo
#   - Marks the repo as a safe Git directory
#   - Creates a Python virtual environment
#   - Installs Python dependencies
#   - Creates an environment file template
#   - Optionally creates a systemd service
#   - Optionally enables/starts the service
#
# What this script does NOT do:
#   - Install the Linux distro itself
#   - Download model weights
#   - Configure reverse proxy / TLS
#   - Force-delete existing persistent app data
#
# Example usage:
#   sudo bash install_ladylinux.sh --clone
#   sudo bash install_ladylinux.sh --clone --branch main --install-service --enable-service --start-service
#===============================================================================

set -Eeuo pipefail

#----------------------------- Defaults ----------------------------------------

DO_CLONE="false"
DO_UPDATE="true"
INSTALL_PACKAGES="true"
INSTALL_SERVICE="false"
ENABLE_SERVICE="false"
START_SERVICE="false"
DO_USER="true"
DRY_RUN="false"

REPO_URL="https://github.com/theCodingProfessor/LadyLinux"
BRANCH="main"

SERVICE_USER="ladylinux"
SERVICE_GROUP="ladylinux"
SERVICE_NAME="ladylinux-api"

BASE_DIR="/opt/ladylinux"
APP_DIR="$BASE_DIR/app"
VENV_DIR="$BASE_DIR/venv"
MODELS_DIR="$BASE_DIR/models"
CONTAINERS_DIR="$BASE_DIR/containers"

ETC_DIR="/etc/ladylinux"
ENV_FILE="$ETC_DIR/ladylinux.env"

VAR_DIR="/var/lib/ladylinux"
DATA_DIR="$VAR_DIR/data"
CACHE_DIR="$VAR_DIR/cache"
LOGS_DIR="$VAR_DIR/logs"

SYSTEMD_UNIT="/etc/systemd/system/${SERVICE_NAME}.service"

APP_MODULE="main:app"
APP_HOST="0.0.0.0"
APP_PORT="8000"

APT_PACKAGES=(
  git
  curl
  ca-certificates
  python3
  python3-venv
  python3-pip
)

#------------------------------ Logging ----------------------------------------

log()  { printf "[install] %s\n" "$*"; }
warn() { printf "[install][WARN] %s\n" "$*" >&2; }
die()  { printf "[install][ERROR] %s\n" "$*" >&2; exit "${2:-1}"; }

#------------------------------ Helpers ----------------------------------------

run() {
  if [[ "$DRY_RUN" == "true" ]]; then
    log "DRY-RUN: $*"
  else
    "$@"
  fi
}

require_root() {
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    die "Please run this script as root with sudo." 2
  fi
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1" 2
}

usage() {
  cat <<EOF
LadyLinux full installer

Usage:
  sudo bash install_ladylinux.sh [options]

Options:
  --clone                   Clone repo if missing
  --no-update               Do not update existing repo
  --repo <url>              Repo URL (default: $REPO_URL)
  --branch <name>           Git branch (default: $BRANCH)
  --no-user                 Do not create service user/group
  --no-packages             Skip apt package install
  --install-service         Create a systemd service
  --enable-service          Enable systemd service at boot
  --start-service           Start systemd service after install
  --app-module <module>     Uvicorn app module (default: $APP_MODULE)
  --host <host>             Bind host (default: $APP_HOST)
  --port <port>             Bind port (default: $APP_PORT)
  --dry-run                 Print actions without changing anything
  -h, --help                Show help

Examples:
  sudo bash install_ladylinux.sh --clone
  sudo bash install_ladylinux.sh --clone --install-service --enable-service --start-service
  sudo bash install_ladylinux.sh --clone --branch darrius --app-module app.main:app
EOF
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --clone) DO_CLONE="true"; shift ;;
      --no-update) DO_UPDATE="false"; shift ;;
      --repo)
        REPO_URL="${2:-}"
        [[ -n "$REPO_URL" ]] || die "--repo requires a value" 2
        shift 2
        ;;
      --branch)
        BRANCH="${2:-}"
        [[ -n "$BRANCH" ]] || die "--branch requires a value" 2
        shift 2
        ;;
      --no-user) DO_USER="false"; shift ;;
      --no-packages) INSTALL_PACKAGES="false"; shift ;;
      --install-service) INSTALL_SERVICE="true"; shift ;;
      --enable-service) ENABLE_SERVICE="true"; shift ;;
      --start-service) START_SERVICE="true"; shift ;;
      --app-module)
        APP_MODULE="${2:-}"
        [[ -n "$APP_MODULE" ]] || die "--app-module requires a value" 2
        shift 2
        ;;
      --host)
        APP_HOST="${2:-}"
        [[ -n "$APP_HOST" ]] || die "--host requires a value" 2
        shift 2
        ;;
      --port)
        APP_PORT="${2:-}"
        [[ -n "$APP_PORT" ]] || die "--port requires a value" 2
        shift 2
        ;;
      --dry-run) DRY_RUN="true"; shift ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        die "Unknown argument: $1" 2
        ;;
    esac
  done
}

mkdir_safe() {
  local dir="$1"
  if [[ -d "$dir" ]]; then
    log "Directory exists: $dir"
  else
    log "Creating directory: $dir"
    run mkdir -p "$dir"
  fi
}

touch_safe() {
  local file="$1"
  if [[ -f "$file" ]]; then
    log "File exists: $file"
  else
    log "Creating file: $file"
    run install -m 0640 /dev/null "$file"
  fi
}

apt_install_packages() {
  if [[ "$INSTALL_PACKAGES" != "true" ]]; then
    log "Skipping apt package installation."
    return 0
  fi

  require_cmd apt-get

  log "Updating apt package index"
  run apt-get update

  log "Installing required packages"
  run apt-get install -y "${APT_PACKAGES[@]}"
}

ensure_group_user() {
  if [[ "$DO_USER" != "true" ]]; then
    log "Skipping user/group creation."
    return 0
  fi

  if getent group "$SERVICE_GROUP" >/dev/null 2>&1; then
    log "Group exists: $SERVICE_GROUP"
  else
    log "Creating group: $SERVICE_GROUP"
    run groupadd --system "$SERVICE_GROUP"
  fi

  if id "$SERVICE_USER" >/dev/null 2>&1; then
    log "User exists: $SERVICE_USER"
  else
    log "Creating service user: $SERVICE_USER"
    run useradd \
      --system \
      --gid "$SERVICE_GROUP" \
      --home-dir "$BASE_DIR" \
      --create-home \
      --shell /usr/sbin/nologin \
      "$SERVICE_USER"
  fi
}

create_directories() {
  mkdir_safe "$BASE_DIR"
  mkdir_safe "$APP_DIR"
  mkdir_safe "$VENV_DIR"
  mkdir_safe "$MODELS_DIR"
  mkdir_safe "$CONTAINERS_DIR"

  mkdir_safe "$VAR_DIR"
  mkdir_safe "$DATA_DIR"
  mkdir_safe "$CACHE_DIR"
  mkdir_safe "$LOGS_DIR"

  mkdir_safe "$ETC_DIR"
}

set_permissions() {
  log "Applying directory permissions"

  if id "$SERVICE_USER" >/dev/null 2>&1; then
    run chown -R "$SERVICE_USER:$SERVICE_GROUP" "$BASE_DIR"
    run chown -R "$SERVICE_USER:$SERVICE_GROUP" "$VAR_DIR"
    run chown -R root:"$SERVICE_GROUP" "$ETC_DIR"
  else
    run chown -R root:root "$ETC_DIR"
  fi

  run chmod 0755 "$BASE_DIR"
  run chmod 0755 "$APP_DIR" || true
  run chmod 0755 "$VENV_DIR" || true
  run chmod 0750 "$MODELS_DIR" || true
  run chmod 0755 "$CONTAINERS_DIR" || true

  run chmod 0755 "$VAR_DIR"
  run chmod 0750 "$DATA_DIR" "$CACHE_DIR" "$LOGS_DIR" || true
  run chmod 0750 "$ETC_DIR"
}

create_env_file() {
  if [[ -f "$ENV_FILE" ]]; then
    log "Env file already exists: $ENV_FILE"
    return 0
  fi

  log "Creating env file: $ENV_FILE"

  if [[ "$DRY_RUN" == "true" ]]; then
    log "DRY-RUN: would write env template to $ENV_FILE"
    return 0
  fi

  cat > "$ENV_FILE" <<EOF
# LadyLinux environment configuration
LADYLINUX_ENV=dev
LADYLINUX_HOST=$APP_HOST
LADYLINUX_PORT=$APP_PORT
LADYLINUX_MODELS_DIR=$MODELS_DIR
LADYLINUX_STATE_DIR=$DATA_DIR
LADYLINUX_CACHE_DIR=$CACHE_DIR
LADYLINUX_LOGS_DIR=$LOGS_DIR
EOF

  if getent group "$SERVICE_GROUP" >/dev/null 2>&1; then
    chown root:"$SERVICE_GROUP" "$ENV_FILE"
  else
    chown root:root "$ENV_FILE"
  fi

  chmod 0640 "$ENV_FILE"
}

clone_or_update_repo() {
  require_cmd git

  if [[ -d "$APP_DIR/.git" ]]; then
    log "Existing git repo detected in $APP_DIR"

    if [[ "$DO_UPDATE" == "true" ]]; then
      log "Updating existing repository"
      run git -C "$APP_DIR" config --global --add safe.directory "$APP_DIR"
      run git -C "$APP_DIR" fetch origin
      run git -C "$APP_DIR" checkout "$BRANCH"
      run git -C "$APP_DIR" reset --hard "origin/$BRANCH"
    else
      log "Skipping repo update (--no-update set)"
    fi
  else
    if [[ "$DO_CLONE" != "true" ]]; then
      warn "Repo missing and --clone not set. App install will not complete."
      return 0
    fi

    if [[ -d "$APP_DIR" && -n "$(ls -A "$APP_DIR" 2>/dev/null || true)" ]]; then
      die "$APP_DIR exists and is not empty, but is not a git repo. Refusing to overwrite." 1
    fi

    log "Cloning repository into $APP_DIR"
    run rm -rf "$APP_DIR"
    run git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
    run git config --global --add safe.directory "$APP_DIR"
  fi

  if id "$SERVICE_USER" >/dev/null 2>&1; then
    run chown -R "$SERVICE_USER:$SERVICE_GROUP" "$APP_DIR"
  fi
}

find_requirements_file() {
  if [[ -f "$APP_DIR/requirements.txt" ]]; then
    printf "%s\n" "$APP_DIR/requirements.txt"
    return 0
  fi

  local found=""
  found="$(find "$APP_DIR" -maxdepth 3 -type f -name "requirements.txt" 2>/dev/null | head -n 1 || true)"

  if [[ -n "$found" ]]; then
    printf "%s\n" "$found"
    return 0
  fi

  return 1
}

setup_python_env() {
  require_cmd python3

  if [[ ! -d "$APP_DIR" ]]; then
    die "App directory does not exist: $APP_DIR" 1
  fi

  log "Creating virtual environment"

  if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    run python3 -m venv "$VENV_DIR"
  else
    log "Virtual environment already exists: $VENV_DIR"
  fi

  log "Upgrading pip/setuptools/wheel"
  run "$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel

  local req_file=""
  if req_file="$(find_requirements_file)"; then
    log "Installing Python requirements from: $req_file"
    run "$VENV_DIR/bin/pip" install -r "$req_file"
  else
    warn "No requirements.txt found under $APP_DIR"
  fi

  log "Ensuring uvicorn is installed"
  run "$VENV_DIR/bin/pip" install uvicorn

  if id "$SERVICE_USER" >/dev/null 2>&1; then
    run chown -R "$SERVICE_USER:$SERVICE_GROUP" "$VENV_DIR"
  fi
}

write_systemd_service() {
  if [[ "$INSTALL_SERVICE" != "true" ]]; then
    log "Skipping systemd unit creation."
    return 0
  fi

  require_cmd systemctl

  log "Writing systemd unit: $SYSTEMD_UNIT"

  if [[ "$DRY_RUN" == "true" ]]; then
    log "DRY-RUN: would write systemd service file"
    return 0
  fi

  cat > "$SYSTEMD_UNIT" <<EOF
[Unit]
Description=LadyLinux API Service
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$APP_DIR
EnvironmentFile=$ENV_FILE
ExecStart=$VENV_DIR/bin/python -m uvicorn $APP_MODULE --host $APP_HOST --port $APP_PORT
Restart=always
RestartSec=3
StandardOutput=append:$LOGS_DIR/service.log
StandardError=append:$LOGS_DIR/service-error.log

[Install]
WantedBy=multi-user.target
EOF

  chmod 0644 "$SYSTEMD_UNIT"
  run systemctl daemon-reload
}

enable_systemd_service() {
  if [[ "$ENABLE_SERVICE" == "true" && "$INSTALL_SERVICE" == "true" ]]; then
    log "Enabling systemd service: $SERVICE_NAME"
    run systemctl enable "$SERVICE_NAME"
  fi
}

start_systemd_service() {
  if [[ "$START_SERVICE" == "true" && "$INSTALL_SERVICE" == "true" ]]; then
    log "Starting systemd service: $SERVICE_NAME"
    run systemctl restart "$SERVICE_NAME"
  fi
}

verify_install() {
  log "Verifying installation"

  [[ -d "$BASE_DIR" ]] || die "Missing base dir: $BASE_DIR"
  [[ -d "$APP_DIR" ]] || die "Missing app dir: $APP_DIR"
  [[ -x "$VENV_DIR/bin/python" ]] || die "Missing venv python: $VENV_DIR/bin/python"
  [[ -f "$ENV_FILE" ]] || die "Missing env file: $ENV_FILE"

  if [[ "$INSTALL_SERVICE" == "true" ]]; then
    [[ -f "$SYSTEMD_UNIT" ]] || die "Missing systemd unit: $SYSTEMD_UNIT"
  fi

  log "Verification passed"
}

print_summary() {
  log "---------------- Summary ----------------"
  log "Repo URL:         $REPO_URL"
  log "Branch:           $BRANCH"
  log "Base dir:         $BASE_DIR"
  log "App dir:          $APP_DIR"
  log "Venv dir:         $VENV_DIR"
  log "Models dir:       $MODELS_DIR"
  log "Config file:      $ENV_FILE"
  log "Data dir:         $DATA_DIR"
  log "Cache dir:        $CACHE_DIR"
  log "Logs dir:         $LOGS_DIR"
  log "Service user:     $SERVICE_USER"
  log "App module:       $APP_MODULE"
  log "Host:             $APP_HOST"
  log "Port:             $APP_PORT"
  log "Install service:  $INSTALL_SERVICE"
  log "Enable service:   $ENABLE_SERVICE"
  log "Start service:    $START_SERVICE"
  log "Dry run:          $DRY_RUN"
  log "----------------------------------------"
}

main() {
  parse_args "$@"
  require_root

  require_cmd mkdir
  require_cmd chmod
  require_cmd chown
  require_cmd install
  require_cmd find

  log "Beginning LadyLinux installation"

  apt_install_packages
  ensure_group_user
  create_directories
  set_permissions
  create_env_file
  clone_or_update_repo
  setup_python_env
  write_systemd_service
  enable_systemd_service
  start_systemd_service
  verify_install
  print_summary

  log "LadyLinux install complete."
}

main "$@"