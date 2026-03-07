from __future__ import annotations

from fastapi import APIRouter

from api_layer.services import firewall_service

router = APIRouter(prefix="/api/firewall", tags=["firewall"])


@router.get("/status")
def get_firewall_status() -> dict:
    return firewall_service.firewall_status()


@router.get("/rules")
def get_firewall_rules() -> dict:
    return firewall_service.firewall_rules()
