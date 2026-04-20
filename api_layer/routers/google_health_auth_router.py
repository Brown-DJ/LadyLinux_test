"""
OAuth2 flow endpoints for Google Health API.
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from api_layer.services.google_cache import invalidate
from api_layer.services.google_health_auth_service import (
    _write_env_value,
    build_health_consent_url,
    exchange_health_code_for_tokens,
    is_health_authorized,
)

log = logging.getLogger("ladylinux.google_health_auth_router")
router = APIRouter(prefix="/api/google/health/oauth", tags=["google_health_auth"])


@router.get("/start")
async def health_oauth_start():
    """
    Redirect browser to Google's consent screen for Health API.
    """
    try:
        url = build_health_consent_url()
        return RedirectResponse(url=url)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/callback")
async def health_oauth_callback(code: str | None = None, error: str | None = None):
    """
    Exchange Google's Health OAuth callback code for tokens.
    """
    if error:
        log.warning("Health OAuth callback error: %s", error)
        return HTMLResponse(
            content=f"""
            <h2>Health authorization failed</h2>
            <p>Google returned: <code>{error}</code></p>
            <p>Return to LadyLinux and try again.</p>
        """,
            status_code=400,
        )

    if not code:
        raise HTTPException(status_code=400, detail="No authorization code received")

    try:
        await exchange_health_code_for_tokens(code)
        return HTMLResponse(
            content="""
            <h2>Google Health authorized</h2>
            <p>Health and activity data access granted.</p>
            <p>You can close this tab and return to LadyLinux.</p>
        """
        )
    except Exception as exc:  # noqa: BLE001
        log.error("Health token exchange failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Token exchange failed: {exc}") from exc


@router.get("/status")
async def health_oauth_status():
    """
    Return whether Google Health OAuth has been completed.
    """
    return {"authorized": is_health_authorized()}


@router.post("/revoke")
async def health_oauth_revoke():
    """
    Clear stored Google Health tokens and cached Fit data.
    """
    for key in (
        "GOOGLE_HEALTH_ACCESS_TOKEN",
        "GOOGLE_HEALTH_REFRESH_TOKEN",
        "GOOGLE_HEALTH_TOKEN_EXPIRY",
    ):
        _write_env_value(key, "REPLACE_ME")
        os.environ.pop(key, None)

    invalidate("fit")
    log.info("Google Health tokens revoked")
    return {"ok": True, "message": "Google Health authorization removed"}
