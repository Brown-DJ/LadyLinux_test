# Systemd Service
## Purpose
Document the systemd unit used to run the FastAPI application.

## Key Responsibilities
- Start Uvicorn for the LadyLinux API.
- Load environment variables from `/etc/ladylinux/ladylinux.env`.
- Declare ordering and restart policy.
- Restrict filesystem access while leaving LadyLinux state writable.

## Module Path
`ladylinux-api.service`

## Public Interface (functions / endpoints / events)
- `ExecStart=/opt/ladylinux/venv/bin/uvicorn api_layer:app ...`
- Unit name: `ladylinux-api.service`

## Data Flow
systemd starts the service after `network-online.target` and `ladylinux-llm.service`, changes into `/opt/ladylinux/app`, loads the optional env file, and launches Uvicorn with the configured host and port. Logs are written to the journal under `SyslogIdentifier=ladylinux-api`.

## Connects To
- `/etc/ladylinux/ladylinux.env`
- `/opt/ladylinux/app`
- `/opt/ladylinux/venv`
- `scripts/install_ladylinux.sh`
- `scripts/refresh_git.sh`

## Known Constraints / Gotchas
- The unit comments explicitly note a fixed `ExecStart` module path of `api_layer:app`.
- `ProtectHome=read-only` is used instead of `true` so git config remains readable for refresh flows.
- The repo also contains `ladylinux-llm.service`, but this note covers only `ladylinux-api.service`.
