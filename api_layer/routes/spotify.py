"""Spotify Web API routes for LadyLinux."""

from __future__ import annotations

import base64
import os

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import requests

from api_layer.services import spotify_service

router = APIRouter(prefix="/api/spotify", tags=["spotify"])


class DeviceSelectPayload(BaseModel):
    """Caller sends: {"device_id": "<id>", "force_play": true}."""

    device_id: str
    force_play: bool = True


class SearchPayload(BaseModel):
    """POST body: {"query": "Kendrick Lamar", "type": "track"}."""

    query: str
    type: str = "track"
    search_type: str | None = None


class PlayUriPayload(BaseModel):
    """POST body: {"uri": "spotify:track:<id>"}."""

    uri: str


@router.get("/devices")
def get_devices() -> dict:
    """Return all available Spotify Connect devices for the authenticated user."""
    return spotify_service.spotify_get_devices()


@router.post("/device/select")
def select_device(payload: DeviceSelectPayload) -> dict:
    """Transfer Spotify playback to the specified device ID."""
    return spotify_service.spotify_transfer_device(
        device_id=payload.device_id,
        force_play=payload.force_play,
    )


@router.get("/now-playing")
def now_playing() -> dict:
    """Current track with active device context."""
    return spotify_service.spotify_now_playing()


@router.get("/playlists")
def get_playlists(limit: int = 20) -> dict:
    """Return the user's Spotify playlists for the launcher panel."""
    return spotify_service.spotify_get_playlists(limit=limit)


@router.get("/recently-played")
def recently_played(limit: int = 10) -> dict:
    """Return recently played tracks for the quick-access panel."""
    return spotify_service.spotify_get_recently_played(limit=limit)


@router.post("/search")
def search(payload: SearchPayload) -> dict:
    """Search Spotify and return top results."""
    return spotify_service.spotify_search(
        query=payload.query,
        search_type=payload.search_type or payload.type,
    )


@router.post("/play")
def play_uri(payload: PlayUriPayload) -> dict:
    """Start playback of a Spotify URI."""
    return spotify_service.spotify_play_uri(uri=payload.uri)


@router.get("/callback")
def spotify_oauth_callback(code: str | None = None, error: str | None = None) -> HTMLResponse:
    """
    One-time OAuth callback for Spotify initial setup.

    Exchanges Spotify's short-lived auth code for a refresh token and displays
    the env var line needed by the API service.
    """
    if error:
        return HTMLResponse(f"<pre>Spotify denied: {error}</pre>", status_code=400)

    if not code:
        return HTMLResponse(
            "<pre>No code in callback. Try the auth URL again.</pre>",
            status_code=400,
        )

    client_id = os.environ.get("SPOTIFY_CLIENT_ID", "")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET", "")
    redirect_uri = os.environ.get(
        "SPOTIFY_REDIRECT_URI",
        "http://127.0.0.1:8000/api/spotify/callback",
    )

    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    response = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        },
        timeout=10,
    )

    if not response.ok:
        return HTMLResponse(
            f"<pre>Token exchange failed ({response.status_code}):\n"
            f"{response.text}</pre>",
            status_code=502,
        )

    data = response.json()
    refresh_token = data.get("refresh_token", "NOT RETURNED - check scopes")

    return HTMLResponse(
        f"""
    <html><body style="font-family:monospace;padding:2rem;background:#111;color:#0f0">
    <h2 style="color:#fff">Spotify OAuth Complete</h2>
    <p>Add this line to <code>/etc/ladylinux/ladylinux.env</code>:</p>
    <pre style="background:#1a1a1a;padding:1rem;border-radius:6px;font-size:1.1rem;color:#0f0">SPOTIFY_REFRESH_TOKEN={refresh_token}</pre>
    <p style="color:#888">Then restart: <code>sudo systemctl restart ladylinux-api.service</code></p>
    </body></html>
    """
    )
