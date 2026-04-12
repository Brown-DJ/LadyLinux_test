# Screen Agent
## Purpose
Poll the desktop session for active window and open terminal state, writing structured JSON that the API reads on every prompt to give Mistral context about what the user is currently doing on screen.

## Key Responsibilities
- Detect the active window title and PID using `xdotool` (X11) or `wmctrl` (fallback).
- Enumerate open terminal processes and their current working directories.
- Write a structured JSON snapshot atomically to a shared state file every 3 seconds.
- Run as the logged-in desktop user, not the `ladylinux` service account.

## Module Path
`core/screen/screen_agent.py`

## Public Interface (functions / endpoints / events)
- `collect_screen_state() -> dict`
- `get_active_window_x11() -> dict`
- `get_active_window_wmctrl() -> dict`
- `get_open_terminals() -> list[dict]`
- `get_focused_app_name(pid) -> str | None`
- `write_state(state: dict) -> None`
- `main()` — polling loop, entry point
- Output file: `/var/lib/ladylinux/data/screen_state.json`

## Data Flow
The agent runs as a systemd user service (`ladylinux-screen-agent.service`) under the desktop session. It polls every `POLL_INTERVAL = 3` seconds, calls `collect_screen_state()`, and writes the result atomically via a `.tmp` rename. `api_layer/app.py` reads this file in `_read_screen_state()` on every prompt, checks if the file is stale (older than 30 seconds), and if fresh injects an `[LIVE SCREEN]` block into the live state prompt.

```
screen_agent (desktop user, 3s loop)
→ collect_screen_state()
→ write /var/lib/ladylinux/data/screen_state.json (0644)

api_layer/app.py (_read_screen_state, every prompt)
→ check file age < 30s
→ parse active_window + open_terminals
→ inject as [LIVE SCREEN] block into _build_live_state_block()
```

## Output Schema
```json
{
  "ts": "2026-04-06T20:00:00+00:00",
  "active_window": {
    "title": "LadyLinux — Chromium",
    "pid": 12345,
    "app": "chromium",
    "detection_method": "xdotool"
  },
  "open_terminals": [
    {"pid": 1234, "name": "bash", "cwd": "/opt/ladylinux/app"}
  ],
  "display": {
    "x11": true,
    "wayland": false
  }
}
```

## Systemd Unit
`scripts/ladylinux-screen-agent.service` — install to `~/.config/systemd/user/` and enable with:
```bash
systemctl --user enable --now ladylinux-screen-agent
```
Runs from the venv so `psutil` is available. Inherits `$DISPLAY` / `$WAYLAND_DISPLAY` from the desktop session.

## Connects To
- `api_layer/app.py` (`_read_screen_state()`, `_SCREEN_STATE_FILE`)
- `scripts/ladylinux-screen-agent.service`
- `scripts/install_ladylinux.sh` (installs `xdotool`, `wmctrl` as system packages)

## Known Constraints / Gotchas
- Requires X11 or XWayland. Pure Wayland without XWayland will return `title: null` from both detection methods.
- The agent must run as the desktop user — not `ladylinux` service account — to have access to `$DISPLAY`.
- `_read_screen_state()` in `app.py` silently returns `None` if the file is missing, stale (>30s), or unreadable. The prompt continues without screen context.
- Open terminals are capped at 10 entries in `get_open_terminals()` and 5 in `_read_screen_state()` to avoid bloating the prompt.
- File is written with `chmod 0644` so the `ladylinux` service account can read it even though the agent writes it as a different user.
- The agent is not started by the installer — it must be manually enabled per desktop user session.
