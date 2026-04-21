# Media Routes
## Purpose
Expose playerctl-backed media playback controls through HTTP endpoints.

## Key Responsibilities
- Read current media status and metadata.
- Play, pause, toggle, skip, go previous, and stop media.
- Set active player volume.
- Toggle shuffle and cycle repeat mode.
- Reuse audio sink listing for the media panel.

## Module Path
`api_layer/routes/media.py`

## Public Interface (functions / endpoints / events)
- `GET /api/media/status`
- `POST /api/media/play`
- `POST /api/media/pause`
- `POST /api/media/toggle`
- `POST /api/media/next`
- `POST /api/media/previous`
- `POST /api/media/stop`
- `POST /api/media/volume`
- `POST /api/media/shuffle`
- `POST /api/media/loop`
- `GET /api/media/sinks`

## Data Flow
Each media endpoint delegates to `api_layer.services.media_service`, except `GET /api/media/sinks`, which calls `audio_service.audio_sink_list()`. `POST /api/media/volume` validates a floating-point `level` payload and passes it to `media_volume_set()`. The service layer runs the underlying `playerctl` or `pactl` command and returns structured data.

## Connects To
- `api_layer/services/media_service.py`
- `api_layer/services/audio_service.py`
- [[Services/Media Service]]
- [[Services/Audio Service]]

## Known Constraints / Gotchas
- Volume level is a float from 0.0 to 1.0, not the 0-100 integer used by audio routes.
- Media commands require MPRIS support from the active desktop player.
- `GET /api/media/sinks` is audio-device data, not MPRIS player data.
