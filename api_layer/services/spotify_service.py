"""
Spotify Web API service for LadyLinux.

Requires:
  - SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET in /etc/ladylinux/ladylinux.env
  - SPOTIFY_REFRESH_TOKEN pre-generated via OAuth PKCE flow (one-time setup)
  - requests in requirements.txt

Token refresh is handled automatically before each API call.
"""

from __future__ import annotations

import os
import time
from typing import Any

import requests

_access_token: str | None = None
_token_expiry: float = 0.0

SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE = "https://api.spotify.com/v1"
_VALID_SEARCH_TYPES = {"track", "artist", "album", "playlist"}


def _get_access_token() -> str | None:
    """Return a valid access token, refreshing if expired."""
    global _access_token, _token_expiry

    if _access_token and time.time() < _token_expiry - 30:
        return _access_token

    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
    refresh_token = os.environ.get("SPOTIFY_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        return None

    try:
        response = requests.post(
            SPOTIFY_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=10,
        )
    except requests.RequestException:
        return None

    if not response.ok:
        return None

    try:
        data = response.json()
    except ValueError:
        return None

    token = data.get("access_token")
    if not token:
        return None

    _access_token = token
    _token_expiry = time.time() + int(data.get("expires_in", 3600))
    return _access_token


def _headers() -> dict[str, str]:
    """Build Authorization header for Spotify API requests."""
    token = _get_access_token()
    return {"Authorization": f"Bearer {token}"} if token else {}


def _error_message(response: requests.Response) -> str:
    """Return a compact Spotify error message."""
    try:
        data = response.json()
    except ValueError:
        return response.text
    error = data.get("error")
    if isinstance(error, dict):
        return str(error.get("message") or data)
    return str(data)


def spotify_search(query: str, search_type: str = "track") -> dict[str, Any]:
    """
    Search Spotify for a track, artist, album, or playlist.

    search_type: "track" | "artist" | "album" | "playlist"
    """
    if not query or not query.strip():
        return {"ok": False, "results": [], "message": "Query cannot be empty"}
    if search_type not in _VALID_SEARCH_TYPES:
        return {
            "ok": False,
            "results": [],
            "message": f"Unsupported Spotify search type: {search_type}",
        }

    token = _get_access_token()
    if not token:
        return {"ok": False, "results": [], "message": "Spotify not configured"}

    try:
        response = requests.get(
            f"{SPOTIFY_API_BASE}/search",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "q": query,
                "type": search_type,
                "limit": 5,
            },
            timeout=10,
        )
    except requests.RequestException as exc:
        return {"ok": False, "results": [], "message": str(exc)}

    if not response.ok:
        return {"ok": False, "results": [], "message": _error_message(response)}

    try:
        data = response.json()
    except ValueError:
        return {"ok": False, "results": [], "message": "Invalid Spotify response"}

    items = data.get(f"{search_type}s", {}).get("items", [])
    results = [
        {
            "name": item.get("name"),
            "uri": item.get("uri"),
            "id": item.get("id"),
            "thumb": (
                (item.get("album", {}).get("images") or item.get("images") or [{}])[-1]
                .get("url", "")
            ),
        }
        for item in items
        if item
    ]
    return {"ok": True, "results": results}


def spotify_play_uri(uri: str) -> dict[str, Any]:
    """
    Start playback of a Spotify URI.

    URI format: spotify:track:<id> | spotify:album:<id> |
                spotify:playlist:<id> | spotify:artist:<id>
    """
    if not uri or not uri.startswith(
        ("spotify:track:", "spotify:album:", "spotify:playlist:", "spotify:artist:")
    ):
        return {"ok": False, "message": "Unsupported Spotify URI"}

    token = _get_access_token()
    if not token:
        return {"ok": False, "message": "Spotify not configured"}

    payload = (
        {"uris": [uri]}
        if uri.startswith("spotify:track:")
        else {"context_uri": uri}
    )
    try:
        response = requests.put(
            f"{SPOTIFY_API_BASE}/me/player/play",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
            timeout=10,
        )
    except requests.RequestException as exc:
        return {"ok": False, "message": str(exc)}

    return {
        "ok": response.status_code in (200, 204),
        "message": "Playback started" if response.ok else _error_message(response),
    }


def spotify_player_action(action: str) -> dict[str, Any]:
    """
    Send a playback control command to Spotify.

    action: "play" | "pause" | "next" | "previous"
    """
    token = _get_access_token()
    if not token:
        return {"ok": False, "message": "Spotify not configured"}

    method_map = {
        "play": ("PUT", f"{SPOTIFY_API_BASE}/me/player/play"),
        "pause": ("PUT", f"{SPOTIFY_API_BASE}/me/player/pause"),
        "next": ("POST", f"{SPOTIFY_API_BASE}/me/player/next"),
        "previous": ("POST", f"{SPOTIFY_API_BASE}/me/player/previous"),
    }

    if action not in method_map:
        return {"ok": False, "message": f"Unknown action: {action}"}

    method, url = method_map[action]
    try:
        response = requests.request(
            method,
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
    except requests.RequestException as exc:
        return {"ok": False, "message": str(exc)}

    return {
        "ok": response.status_code in (200, 204),
        "message": "ok" if response.status_code in (200, 204) else _error_message(response),
    }


def spotify_get_devices() -> dict[str, Any]:
    """List available Spotify Connect devices."""
    token = _get_access_token()
    if not token:
        return {"ok": False, "message": "Spotify not configured"}

    try:
        response = requests.get(
            f"{SPOTIFY_API_BASE}/me/player/devices",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
    except requests.RequestException as exc:
        return {"ok": False, "message": str(exc)}

    if not response.ok:
        return {"ok": False, "message": _error_message(response)}

    devices = [
        {
            "name": device["name"],
            "id": device["id"],
            "active": device["is_active"],
            "type": device.get("type", ""),
        }
        for device in response.json().get("devices", [])
    ]
    return {"ok": True, "devices": devices}


def spotify_transfer_device(device_id: str, force_play: bool = True) -> dict[str, Any]:
    """
    Transfer Spotify playback to a different Connect device.

    device_id  : Spotify device ID string from spotify_get_devices
    force_play : if True, immediately resume playback on target device
                 False transfers but keeps current pause state

    Spotify returns 204 No Content on success.
    """
    if not device_id or not device_id.strip():
        return {"ok": False, "message": "device_id is required"}

    token = _get_access_token()
    if not token:
        return {"ok": False, "message": "Spotify not configured"}

    try:
        response = requests.put(
            f"{SPOTIFY_API_BASE}/me/player",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "device_ids": [device_id],
                "play": force_play,
            },
            timeout=10,
        )
    except requests.RequestException as exc:
        return {"ok": False, "message": str(exc)}

    return {
        "ok": response.status_code in (200, 204),
        "message": (
            "Playback transferred"
            if response.status_code in (200, 204)
            else _error_message(response)
        ),
    }


def spotify_now_playing() -> dict[str, Any]:
    """Get the currently playing track from Spotify Web API."""
    token = _get_access_token()
    if not token:
        return {"ok": False, "message": "Spotify not configured"}

    try:
        response = requests.get(
            f"{SPOTIFY_API_BASE}/me/player",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
    except requests.RequestException as exc:
        return {"ok": False, "message": str(exc)}

    if response.status_code == 204:
        return {"ok": True, "playing": False, "message": "Nothing playing"}
    if not response.ok:
        return {"ok": False, "message": _error_message(response)}

    try:
        data = response.json()
    except ValueError:
        return {"ok": False, "message": "Invalid Spotify response"}
    track = data.get("item") or {}
    album_data = track.get("album", {})
    images = album_data.get("images", [])

    def _pick_image(target_height: int) -> str:
        """Return the URL of the image closest to target_height, or empty."""
        if not images:
            return ""
        for image in images:
            if image.get("height", 0) >= target_height:
                return image.get("url", "")
        return images[-1].get("url", "")

    device = data.get("device", {})
    return {
        "ok": True,
        "playing": data.get("is_playing", False),
        "title": track.get("name"),
        "artist": ", ".join(
            artist.get("name", "") for artist in track.get("artists", [])
        ),
        "album": album_data.get("name"),
        "uri": track.get("uri"),
        "art_large": _pick_image(640),
        "art_medium": _pick_image(300),
        "art_thumb": _pick_image(64),
        "device_name": device.get("name", ""),
        "device_id": device.get("id", ""),
        "device_type": device.get("type", ""),
    }


def spotify_get_playlists(limit: int = 20) -> dict[str, Any]:
    """
    Fetch the current user's playlists.
    Requires scope: playlist-read-private, playlist-read-collaborative
    """
    token = _get_access_token()
    if not token:
        return {"ok": False, "playlists": [], "message": "Spotify not configured"}

    try:
        response = requests.get(
            f"{SPOTIFY_API_BASE}/me/playlists",
            headers={"Authorization": f"Bearer {token}"},
            params={"limit": min(limit, 50)},
            timeout=10,
        )
    except requests.RequestException as exc:
        return {"ok": False, "playlists": [], "message": str(exc)}

    if not response.ok:
        return {"ok": False, "playlists": [], "message": _error_message(response)}

    items = response.json().get("items", [])
    playlists = [
        {
            "name": item.get("name", ""),
            "uri": item.get("uri", ""),
            "id": item.get("id", ""),
            "track_count": item.get("tracks", {}).get("total", 0),
        }
        for item in items
        if item  # Spotify can return null items in the list
    ]
    return {"ok": True, "playlists": playlists}


def spotify_get_recently_played(limit: int = 10) -> dict[str, Any]:
    """
    Fetch the user's recently played tracks.
    Requires scope: user-read-recently-played
    """
    token = _get_access_token()
    if not token:
        return {"ok": False, "tracks": [], "message": "Spotify not configured"}

    try:
        response = requests.get(
            f"{SPOTIFY_API_BASE}/me/player/recently-played",
            headers={"Authorization": f"Bearer {token}"},
            params={"limit": min(limit, 50)},
            timeout=10,
        )
    except requests.RequestException as exc:
        return {"ok": False, "tracks": [], "message": str(exc)}

    if not response.ok:
        return {"ok": False, "tracks": [], "message": _error_message(response)}

    items = response.json().get("items", [])
    tracks = [
        {
            "title": item["track"]["name"],
            "artist": ", ".join(a["name"] for a in item["track"]["artists"]),
            "uri": item["track"]["uri"],
            "played_at": item["played_at"],
        }
        for item in items
        if item and item.get("track")
    ]

    return {"ok": True, "tracks": tracks}
