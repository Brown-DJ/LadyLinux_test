from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from api_layer.services import log_service

router = APIRouter(prefix="/api/logs", tags=["logs"])

_FAILED_INGEST_DIR = "/var/lib/ladylinux/rag_ingest/_failed"


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


@router.get("/journal")
def get_journal_logs(
    unit: Optional[str] = Query(default=None),
    lines: int = Query(default=100, ge=1, le=500),
) -> dict:
    return log_service.journal_logs(unit=unit, lines=lines)


@router.get("/files")
def get_log_files() -> dict:
    return log_service.list_log_files()


@router.get("/file")
def get_log_file(
    path: str = Query(...),
    lines: int = Query(default=100, ge=1, le=500),
) -> dict:
    result = log_service.read_log_file(path=path, lines=lines)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("stderr", "Failed to read file"))
    return result


@router.get("/ladylinux")
def get_ladylinux_logs(lines: int = Query(default=200, ge=1, le=500)) -> dict:
    return log_service.ladylinux_logs(lines=lines)


@router.get("/failed-ingest")
def get_failed_ingest_log(lines: int = Query(default=200, ge=1, le=500)) -> dict:
    """
    Return a combined tail of all files in the failed ingest directory.
    """
    safe_lines = max(1, min(lines, 500))

    try:
        failed_files = sorted(
            fname
            for fname in os.listdir(_FAILED_INGEST_DIR)
            if os.path.isfile(os.path.join(_FAILED_INGEST_DIR, fname))
        )
    except FileNotFoundError:
        return {
            "ok": True,
            "lines": ["[No failed ingest files found]"],
            "stdout": "",
            "stderr": "",
            "returncode": 0,
        }
    except PermissionError as exc:
        return {
            "ok": False,
            "lines": [],
            "stdout": "",
            "stderr": str(exc),
            "returncode": 1,
        }

    if not failed_files:
        return {
            "ok": True,
            "lines": ["[_failed directory is empty - no ingestion failures]"],
            "stdout": "",
            "stderr": "",
            "returncode": 0,
        }

    combined: list[str] = []
    for fname in failed_files:
        path = os.path.join(_FAILED_INGEST_DIR, fname)
        combined.append(f"-- {fname} --")
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                combined.extend(fh.read().splitlines()[-safe_lines:])
        except OSError as exc:
            combined.append(f"[Could not read {fname}: {exc}]")
        combined.append("")

    return {
        "ok": True,
        "lines": combined,
        "stdout": "",
        "stderr": "",
        "returncode": 0,
        "file_count": len(failed_files),
    }
