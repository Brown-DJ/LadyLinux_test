# Installer
## Purpose
Document the main machine bootstrap script shipped in this repository.

## Key Responsibilities
- Perform pre-flight checks and package installation.
- Create the `ladylinux` service user and directory layout.
- Sync the repo into `/opt/ladylinux/app`.
- Build the Python virtual environment.
- Install Ollama, pull models, write systemd units, and start services.

## Module Path
`scripts/install_ladylinux.sh`

## Public Interface (functions / endpoints / events)
- `main()`
- `preflight()`
- `install_system_packages()`
- `create_user_and_dirs()`
- `sync_repo()`
- `build_venv()`
- `install_ollama_and_models()`
- `write_systemd_units()`
- `start_and_validate()`

## Data Flow
The script creates `/opt/ladylinux/{app,venv,models,containers}`, `/var/lib/ladylinux/{data,cache,logs}`, and `/etc/ladylinux/`. It creates the `ladylinux` system user with `/usr/sbin/nologin`, writes several sudoers fragments, clones or hard-resets the repo into `/opt/ladylinux/app`, builds the venv, installs Ollama, pulls `mistral` and `nomic-embed-text`, writes `ladylinux-api.service`, and starts the stack.

## Connects To
- `scripts/refresh_git.sh`
- `ladylinux-api.service`
- `llm_runtime.py`
- Ollama

## Known Constraints / Gotchas
- The current script does install systemd units and does pull models; that differs from the target outline in the prompt.
- It does not currently create `/var/lib/ladylinux/qdrant` even though RAG config defaults to that path.
- `sync_repo()` hard-resets and cleans an existing clone.
