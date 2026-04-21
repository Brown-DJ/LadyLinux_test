# Spotify Service
## Purpose
Wrap Spotify Web API playback, search, device, playlist, and OAuth token operations for LadyLinux.

## Key Responsibilities
- Refresh and cache Spotify access tokens from environment credentials.
- Search tracks, artists, albums, and playlists.
- Start playback by query, URI, or target Connect device.
- Read now-playing, playlist, recently played, and device data.
- Return consistent `{ok, ...}` response envelopes.

## Module Path
`api_layer/services/spotify_service.py`

## Public Interface (functions / endpoints / events)
- `spotify_search(query: str, search_type: str = "track") -> dict[str, Any]`
- `spotify_play_uri(uri: str) -> dict[str, Any]`
- `spotify_play(query: str, search_type: str = "auto") -> dict[str, Any]`
- `spotify_player_action(action: str) -> dict[str, Any]`
- `spotify_get_devices() -> dict[str, Any]`
- `spotify_transfer_device(device_id: str, force_play: bool = True) -> dict[str, Any]`
- `spotify_play_on_device(device_name: str) -> dict[str, Any]`
- `spotify_now_playing() -> dict[str, Any]`
- `spotify_get_playlists(limit: int = 20) -> dict[str, Any]`
- `spotify_get_recently_played(limit: int = 10) -> dict[str, Any]`

## Data Flow
Public functions call `_get_access_token()` before contacting the Spotify Web API; that helper reads `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, and `SPOTIFY_REFRESH_TOKEN`, refreshes expired tokens, and caches the access token in memory. Search and playback calls use `requests` against `SPOTIFY_API_BASE`, normalize Spotify responses into dictionaries, and return `ok=False` instead of raising on missing credentials or API failures. `spotify_play()` may call `_infer_search_order()`, `spotify_search()`, and then `spotify_play_uri()` to resolve a natural language request into playback.

## Connects To
- `api_layer/routes/spotify.py`
- `core/tools/tool_registry.py`
- [[API/Spotify Routes]]
- [[Core/Tool Router]]

## Known Constraints / Gotchas
- Requires `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, and `SPOTIFY_REFRESH_TOKEN`.
- Spotify Connect playback control requires a Spotify Premium account and an available active device.
- `_infer_search_order()` is heuristic and query-based; explicit `search_type` bypasses the automatic order.
- Network and API errors are returned as `{ok: False, message: ...}`.
