from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from api_layer.services import log_service

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("/recent")
def get_recent_logs(lines: int = Query(default=100, ge=1, le=500)) -> dict:
    return log_service.recent_logs(lines=lines)


@router.get("/errors")
def get_error_logs(lines: int = Query(default=100, ge=1, le=500)) -> dict:
    return log_service.error_logs(lines=lines)


@router.get("/service/{name}")
def get_service_logs(name: str, lines: int = Query(default=100, ge=1, le=500)) -> dict:
    try:
        return log_service.service_logs(name=name, lines=lines)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
