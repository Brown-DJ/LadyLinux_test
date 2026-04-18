"""Spotify Web API routes for LadyLinux."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

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
