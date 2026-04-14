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
        {"name": item.get("name"), "uri": item.get("uri"), "id": item.get("id")}
        for item in items
    ]
    return {"ok": True, "results": results}


def spotify_play_uri(uri: str) -> dict[str, Any]:
    """
    Start playback of a Spotify URI.

    URI format: spotify:track:<id> | spotify:album:<id> | spotify:playlist:<id>
    """
    if not uri or not uri.startswith(
        ("spotify:track:", "spotify:album:", "spotify:playlist:")
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
        {"name": device["name"], "id": device["id"], "active": device["is_active"]}
        for device in response.json().get("devices", [])
    ]
    return {"ok": True, "devices": devices}


def spotify_now_playing() -> dict[str, Any]:
    """Get the currently playing track from Spotify Web API."""
    token = _get_access_token()
    if not token:
        return {"ok": False, "message": "Spotify not configured"}

    try:
        response = requests.get(
            f"{SPOTIFY_API_BASE}/me/player/currently-playing",
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
    track = data.get("item", {})
    return {
        "ok": True,
        "playing": data.get("is_playing", False),
        "title": track.get("name"),
        "artist": ", ".join(artist["name"] for artist in track.get("artists", [])),
        "album": track.get("album", {}).get("name"),
        "uri": track.get("uri"),
    }
