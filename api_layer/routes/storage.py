from __future__ import annotations

from fastapi import APIRouter

from api_layer.services import storage_service

router = APIRouter(prefix="/api/storage", tags=["storage"])


@router.get("/summary")
def get_storage_summary() -> dict:
    return storage_service.storage_summary()


@router.get("/mounts")
def get_storage_mounts() -> dict:
    return storage_service.storage_mounts()


@router.get("/top-usage")
def get_storage_top_usage() -> dict:
    return storage_service.top_usage()
