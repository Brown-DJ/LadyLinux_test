"""HTTP routes for media playback control via playerctl."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from api_layer.services import audio_service, media_service

router = APIRouter(prefix="/api/media", tags=["media"])


class VolumePayload(BaseModel):
    """Expects JSON body: {"level": 0.75}."""

    level: float


@router.get("/status")
def get_status() -> dict:
    return media_service.media_status()


@router.post("/play")
def play() -> dict:
    return media_service.media_play()


@router.post("/pause")
def pause() -> dict:
    return media_service.media_pause()


@router.post("/toggle")
def toggle() -> dict:
    return media_service.media_toggle()


@router.post("/next")
def next_track() -> dict:
    return media_service.media_next()


@router.post("/previous")
def prev_track() -> dict:
    return media_service.media_prev()


@router.post("/stop")
def stop() -> dict:
    return media_service.media_stop()


@router.post("/volume")
def set_volume(payload: VolumePayload) -> dict:
    return media_service.media_volume_set(payload.level)


@router.post("/shuffle")
def shuffle() -> dict:
    return media_service.media_shuffle_toggle()


@router.post("/loop")
def loop() -> dict:
    return media_service.media_loop_cycle()


@router.get("/sinks")
def list_sinks() -> dict:
    return audio_service.audio_sink_list()
