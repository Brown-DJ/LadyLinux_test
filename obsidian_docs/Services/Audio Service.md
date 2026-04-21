# Audio Service
## Purpose
Control the desktop audio sink through `pactl` from the LadyLinux API process.

## Key Responsibilities
- Mute, unmute, and toggle mute on the default sink.
- Set default sink volume with a clamped 0-100 percentage.
- Read current volume and mute state.
- List available audio output sinks.
- Run commands as the desktop user.

## Module Path
`api_layer/services/audio_service.py`

## Public Interface (functions / endpoints / events)
- `audio_mute() -> dict`
- `audio_unmute() -> dict`
- `audio_toggle_mute() -> dict`
- `audio_volume_set(level: int) -> dict`
- `audio_volume_get() -> dict`
- `audio_sink_list() -> dict`

## Data Flow
Each public function builds a `pactl` command and passes it to `run_as_desktop_user()` from `_desktop_runner`. Setter functions return a simple success message based on the command result, while `audio_volume_get()` runs separate volume and mute commands and parses their stdout. `audio_sink_list()` parses `pactl list sinks short` into structured sink records.

## Connects To
- `api_layer/routes/audio.py`
- `api_layer/services/_desktop_runner.py`
- `core/tools/tool_registry.py`
- [[API/Audio Routes]]
- [[Core/Tool Router]]

## Known Constraints / Gotchas
- `pactl` must run in the desktop user's PulseAudio or PipeWire session, not only as the `ladylinux` service user.
- Volume above 100 percent is deliberately clamped to avoid distortion.
- Parsing depends on current `pactl` output shape.
