# Audio Routes
## Purpose
Expose pactl-backed audio controls through HTTP endpoints.

## Key Responsibilities
- Mute, unmute, and toggle mute on the default sink.
- Set and read default sink volume.
- List available audio sinks.

## Module Path
`api_layer/routes/audio.py`

## Public Interface (functions / endpoints / events)
- `POST /api/audio/mute`
- `POST /api/audio/unmute`
- `POST /api/audio/toggle-mute`
- `POST /api/audio/volume`
- `GET /api/audio/volume`
- `GET /api/audio/sinks`

## Data Flow
The router maps each HTTP endpoint directly to `api_layer.services.audio_service`. `POST /api/audio/volume` validates a `VolumeRequest` body with a `level` integer and passes it to `audio_volume_set()`. All other endpoints delegate without additional transformation and return the service dictionary directly.

## Connects To
- `api_layer/services/audio_service.py`
- [[Services/Audio Service]]

## Known Constraints / Gotchas
- Volume request level is expected to be 0-100; the service clamps values before calling `pactl`.
- Actual audio control depends on desktop-session access through `_desktop_runner`.
- Endpoint responses reflect subprocess launch or parsing results, not frontend playback state.
