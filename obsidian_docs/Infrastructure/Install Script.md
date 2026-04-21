# Install Script
## Purpose
Bootstrap a LadyLinux host from a bare Linux Mint, Ubuntu, or Debian-derived system.

## Key Responsibilities
- Run preflight checks for root, OS detection, and internet access.
- Install system packages, Chromium, Ollama, and required models.
- Create the `ladylinux` service user, runtime directories, sudoers rules, and environment file.
- Clone or refresh the repo, build the Python virtual environment, and fix permissions.
- Write systemd units, launch script, desktop entry, start services, and validate the API port.

## Module Path
`scripts/install_ladylinux.sh`

## Public Interface (functions / endpoints / events)
- `sudo bash scripts/install_ladylinux.sh`
- `preflight()`
- `install_system_packages()`
- `install_chromium()`
- `create_user_and_dirs()`
- `sync_repo()`
- `build_venv()`
- `install_ollama_and_models()`
- `write_systemd_units()`
- `start_and_validate()`

## Data Flow
`main()` runs the installer steps in order, beginning with environment checks and package installation. It creates users, directories, sudoers files, and env templates, syncs `Brown-DJ/LadyLinux_test` into `/opt/ladylinux/app`, builds `/opt/ladylinux/venv`, pulls Ollama models, writes the API unit, starts services, and checks that port 8000 is listening. The script prints localhost, LAN, and mDNS URLs after validation.

## Connects To
- `ladylinux-api.service`
- `scripts/refresh_git.sh`
- [[Infrastructure/Systemd Service]]
- [[Infrastructure/Refresh Script]]

## Known Constraints / Gotchas
- Must be run as root.
- It creates `/var/lib/ladylinux`, `data`, `cache`, `logs`, and `obsidian_user`, but does not explicitly create `/var/lib/ladylinux/qdrant`.
- The repo sync path uses `git reset --hard` and `git clean -fd` inside `/opt/ladylinux/app`.
- The script guards against `starlette==1.0.0` by forcing `starlette==0.41.3` with compatible FastAPI when needed.
