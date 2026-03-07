from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api_layer.services import service_manager

router = APIRouter(prefix="/api/system", tags=["services"])


@router.get("/services")
def list_services() -> dict:
    return service_manager.list_services()


@router.get("/service/{name}")
def get_service(name: str) -> dict:
    try:
        return service_manager.get_service(name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/services/failed")
def failed_services() -> dict:
    return service_manager.list_failed_services()


@router.post("/service/{name}/restart")
def restart_service(name: str) -> dict:
    try:
        return service_manager.restart_service(name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
