from __future__ import annotations

from fastapi import APIRouter

from api_layer.services import network_service

router = APIRouter(prefix="/api/network", tags=["network"])


@router.get("/status")
def get_network_status() -> dict:
    return network_service.network_status()


@router.get("/interfaces")
def get_network_interfaces() -> dict:
    return network_service.network_interfaces()


@router.get("/connections")
def get_network_connections() -> dict:
    return network_service.network_connections()
