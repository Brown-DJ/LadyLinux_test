#!/usr/bin/env bash
# =============================================================================
# refresh_git.sh — LadyLinux git sync + service restart
#
# Usage:  sudo /opt/ladylinux/app/scripts/refresh_git.sh [branch]
#
# Called by: api_layer/routes/system.py  POST /api/system/github/refresh
# Called by: manual terminal invocation
#
# Design constraints:
#   - Must work when spawned as a fully detached subprocess (no TTY, no env)
#   - Must NOT use usermod — ladylinux has a locked password, PAM blocks it
#   - Must NOT use sudo -u — inherits parent restrictions in detached context
#   - All git/pip ops run as root; fix_permissions() realigns ownership after
#   - set -Eeuo pipefail: any unguarded failure exits immediately
# =============================================================================
set -Eeuo pipefail

# ── Force a complete known environment ────────────────────────────────────────
# When spawned from FastAPI via subprocess.Popen the inherited env is stripped.
# systemctl, git, lsof, curl etc. may not be on PATH without this.
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export HOME="/root"
export LANG="en_US.UTF-8"
export SYSTEMD_PAGER=""          # prevent systemctl from invoking a pager
export GIT_TERMINAL_PROMPT="0"   # prevent git from hanging on auth prompts

# ── Configuration — must match install_ladylinux.sh exactly ──────────────────
REPO_URL="https://github.com/Brown-DJ/LadyLinux_test.git"
BRANCH="${1:-main}"

APP_DIR="/opt/ladylinux/app"
VENV_DIR="/opt/ladylinux/venv"
SERVICE_USER="ladylinux"
SERVICE_GROUP="ladylinux"

API_SERVICE="ladylinux-api.service"
LLM_SERVICE="ollama.service"
API_PORT="8000"

# ── Logging helpers ───────────────────────────────────────────────────────────
log()  { echo "[refresh] $*"; }
warn() { echo "[refresh][WARN] $*" >&2; }
die()  { echo "[refresh][ERROR] $*" >&2; exit 1; }

# ── Root check ────────────────────────────────────────────────────────────────
require_root() {
    # Must be first — all operations below require root
    [[ "${EUID}" -eq 0 ]] || die "Run with sudo"
}

# ── Stop API service only — leave Ollama running ─────────────────────────────
# Stopping Ollama forces a slow model reload on restart, which causes the
# validate_api() health check to time out. Leave it running across git syncs.
stop_services() {
    log "Stopping API service"
    systemctl stop "${API_SERVICE}" || true

    # Belt-and-suspenders: kill any orphaned uvicorn process on the port
    pkill -f "uvicorn" 2>/dev/null || true

    # Give the port time to free before git ops begin
    sleep 2
}

# ── Git sync ──────────────────────────────────────────────────────────────────
# Runs as root. Ownership is corrected by fix_permissions() afterward.
# No usermod / sudo -u — ladylinux has a locked account; both fail in a
# detached process context spawned from FastAPI.
sync_repo() {
    log "Updating repository"

    # Register safe.directory for both root and the service user so git
    # doesn't refuse to operate on a directory owned by another user
    git config --global --add safe.directory "${APP_DIR}" 2>/dev/null || true

    cd "${APP_DIR}"

    # Ensure remote URL is correct — correct it silently if not
    local current_remote
    current_remote="$(git remote get-url origin 2>/dev/null || true)"
    if [[ "${current_remote}" != "${REPO_URL}" ]]; then
        log "Correcting remote origin → ${REPO_URL}"
        if git remote | grep -Fxq origin; then
            git remote set-url origin "${REPO_URL}"
        else
            git remote add origin "${REPO_URL}"
        fi
    fi

    git fetch --prune origin

    # Guard: abort before destructive reset if the branch doesn't exist
    git show-ref --verify --quiet "refs/remotes/origin/${BRANCH}" \
        || die "Branch '${BRANCH}' not found on remote. Aborting."

    git checkout -f "${BRANCH}" 2>/dev/null || true
    git reset --hard "origin/${BRANCH}"
    git clean -fd

    log "Repo now at: $(git rev-parse --short HEAD) (${BRANCH})"
}

# ── Venv check ────────────────────────────────────────────────────────────────
repair_venv() {
    log "Checking Python environment"

    # Only rebuild if venv is missing or broken — skip on normal syncs
    if [[ -f "${VENV_DIR}/bin/python" ]]; then
        return 0
    fi

    log "Venv missing or broken — rebuilding"
    rm -rf "${VENV_DIR}"
    mkdir -p "${VENV_DIR}"

    # Match installer's Python priority: 3.12 → 3.11 → 3
    local python_bin=""
    for candidate in python3.12 python3.11 python3; do
        if command -v "${candidate}" >/dev/null 2>&1; then
            python_bin="${candidate}"
            break
        fi
    done
    [[ -n "${python_bin}" ]] || die "No Python 3 interpreter found."

    "${python_bin}" -m venv "${VENV_DIR}"
}

# ── Dependencies ──────────────────────────────────────────────────────────────
install_dependencies() {
    log "Installing dependencies"

    "${VENV_DIR}/bin/pip" install --upgrade pip wheel setuptools --quiet

    if [[ -f "${APP_DIR}/requirements.txt" ]]; then
        "${VENV_DIR}/bin/pip" install -r "${APP_DIR}/requirements.txt" --quiet
    else
        warn "No requirements.txt — installing default runtime stack"
        "${VENV_DIR}/bin/pip" install \
            fastapi uvicorn requests jinja2 python-multipart pydantic --quiet
    fi
}

# ── Permissions ───────────────────────────────────────────────────────────────
fix_permissions() {
    log "Fixing ownership and permissions"

    # Realign ownership after git clean + potential venv rebuild
    chown -R "${SERVICE_USER}:${SERVICE_GROUP}" "${APP_DIR}"
    chown -R "${SERVICE_USER}:${SERVICE_GROUP}" "${VENV_DIR}"

    # Ensure runtime dirs exist and are owned correctly
    mkdir -p /var/lib/ladylinux
    chown -R "${SERVICE_USER}:${SERVICE_GROUP}" /var/lib/ladylinux 2>/dev/null || true

    # Normalize line endings + ensure all scripts are executable
    if command -v dos2unix >/dev/null 2>&1; then
        find "${APP_DIR}" -name "*.sh" -type f | while read -r f; do
            dos2unix "${f}" 2>/dev/null || true
            chmod +x "${f}"
        done
    else
        find "${APP_DIR}" -name "*.sh" -type f -exec chmod +x {} \;
    fi
}

# ── Service restart ───────────────────────────────────────────────────────────
restart_services() {
    log "Reloading systemd"
    systemctl daemon-reload

    # Ensure Ollama is up — it was left running but confirm it
    # Use start (not restart) so a healthy Ollama is never interrupted
    log "Ensuring ${LLM_SERVICE} is running"
    systemctl start "${LLM_SERVICE}" 2>/dev/null \
        || warn "Could not start ${LLM_SERVICE} — API may start without LLM"

    log "Restarting API service"
    systemctl restart "${API_SERVICE}" \
        || die "Failed to restart ${API_SERVICE}"
}

# ── Health check ──────────────────────────────────────────────────────────────
validate_api() {
    log "Waiting for API on port ${API_PORT}"
    sleep 3

    local attempts=15
    local ready=0

    while (( attempts > 0 )); do
        if lsof -i :"${API_PORT}" >/dev/null 2>&1 || \
           ss -tlnp 2>/dev/null | grep -q ":${API_PORT} "; then
            ready=1
            break
        fi
        sleep 1
        (( attempts-- ))
    done

    if [[ "${ready}" -ne 1 ]]; then
        # Warn and continue — don't exit 1, the service may still be starting
        warn "Port ${API_PORT} not listening after timeout."
        warn "  Check: journalctl -u ${API_SERVICE} -n 50 --no-pager"
        return 0
    fi

    log "Port ${API_PORT} is open."

    # HTTP sanity check — failure is non-fatal, service may still be booting
    curl --silent --fail --max-time 5 "http://127.0.0.1:${API_PORT}/" \
        >/dev/null 2>&1 \
        && log "HTTP health check: OK" \
        || warn "Port open but HTTP check failed — may still be starting."
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
    require_root

    # Ensure APP_DIR is accessible before any operation
    chown -R "${SERVICE_USER}:${SERVICE_GROUP}" "${APP_DIR}" 2>/dev/null || true

    stop_services
    sync_repo
    repair_venv
    install_dependencies
    fix_permissions
    restart_services
    validate_api

    local commit
    commit="$(git -C "${APP_DIR}" rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
    log "Refresh complete. Branch: ${BRANCH}  Commit: ${commit}"
}

main "$@"