# Spotify Routes
## Purpose
Expose Spotify Web API features over FastAPI routes for the frontend and tools.

## Key Responsibilities
- Return device, playback, playlist, and recent track data.
- Transfer playback to a selected Spotify Connect device.
- Search Spotify and start playback by URI.
- Proxy playback control actions.
- Complete the one-time Spotify OAuth callback flow.

## Module Path
`api_layer/routes/spotify.py`

## Public Interface (functions / endpoints / events)
- `GET /api/spotify/devices`
- `POST /api/spotify/device/select`
- `GET /api/spotify/now-playing`
- `GET /api/spotify/playlists`
- `GET /api/spotify/recently-played`
- `POST /api/spotify/search`
- `POST /api/spotify/play`
- `POST /api/spotify/pause`
- `POST /api/spotify/next`
- `POST /api/spotify/previous`
- `GET /api/spotify/callback`

## Data Flow
The router receives JSON payloads or query parameters, validates them with Pydantic models where needed, and delegates to `api_layer.services.spotify_service`. Playback and search routes return the service response directly. The OAuth callback exchanges Spotify's authorization code with `requests.post()` and returns an HTML page containing the refresh token line for `/etc/ladylinux/ladylinux.env`.

## Connects To
- `api_layer/services/spotify_service.py`
- `core/tools/tool_registry.py`
- [[Services/Spotify Service]]
- [[Core/Tool Router]]

## Known Constraints / Gotchas
- The callback defaults `SPOTIFY_REDIRECT_URI` to `http://127.0.0.1:8000/api/spotify/callback`.
- OAuth setup requires `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET`.
- `POST /api/spotify/play` resumes playback only when the request body is omitted.
