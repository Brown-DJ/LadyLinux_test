# Media Service
## Purpose
Control MPRIS-compatible desktop media players through `playerctl`.

## Key Responsibilities
- Play, pause, toggle, skip, rewind, and stop active media.
- Read playback status and track metadata.
- Set player volume between 0.0 and 1.0.
- Toggle shuffle and cycle loop mode.
- Run media commands as the desktop user.

## Module Path
`api_layer/services/media_service.py`

## Public Interface (functions / endpoints / events)
- `media_play() -> dict`
- `media_pause() -> dict`
- `media_toggle() -> dict`
- `media_next() -> dict`
- `media_prev() -> dict`
- `media_stop() -> dict`
- `media_status() -> dict`
- `media_volume_set(level: float) -> dict`
- `media_shuffle_toggle() -> dict`
- `media_loop_cycle() -> dict`

## Data Flow
Control functions call `run_as_desktop_user()` with direct `playerctl` commands and convert the result into response dictionaries. `media_status()` first checks `playerctl status`, then uses one tab-delimited `playerctl metadata --format` call plus `playerctl position` to build the playback snapshot. Volume, shuffle, and loop helpers read or clamp state before sending the corresponding `playerctl` command.

## Connects To
- `api_layer/routes/media.py`
- `api_layer/services/_desktop_runner.py`
- `core/tools/tool_registry.py`
- [[API/Media Routes]]
- [[Core/Tool Router]]

## Known Constraints / Gotchas
- `playerctl` requires access to the desktop user's D-Bus session.
- The current service does not implement an in-process TTL cache; `media_status()` runs subprocess calls on each request.
- Not every MPRIS player supports shuffle, loop, volume, or complete metadata.
