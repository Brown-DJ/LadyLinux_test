"""
OAuth2 flow endpoints for Google integrations.
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from api_layer.services.google_auth_service import (
    _write_env_value,
    build_consent_url,
    exchange_code_for_tokens,
    is_authorized,
)

log = logging.getLogger("ladylinux.google_auth_router")
router = APIRouter(prefix="/api/google/oauth", tags=["google_auth"])


@router.get("/start")
async def oauth_start():
    """
    Redirect the browser to Google's consent screen.
    """
    try:
        url = build_consent_url()
        return RedirectResponse(url=url)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/callback")
async def oauth_callback(code: str | None = None, error: str | None = None):
    """
    Exchange Google's authorization callback code for tokens.
    """
    if error:
        log.warning("OAuth callback error: %s", error)
        return HTMLResponse(
            content=f"""
            <h2>Authorization failed</h2>
            <p>Google returned: <code>{error}</code></p>
            <p>Return to LadyLinux and try again.</p>
        """,
            status_code=400,
        )

    if not code:
        raise HTTPException(status_code=400, detail="No authorization code received")

    try:
        await exchange_code_for_tokens(code)
        return HTMLResponse(
            content="""
            <h2>LadyLinux authorized</h2>
            <p>Google Calendar and Gmail access granted.</p>
            <p>You can close this tab and return to LadyLinux.</p>
        """
        )
    except Exception as exc:  # noqa: BLE001
        log.error("Token exchange failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Token exchange failed: {exc}") from exc


@router.get("/status")
async def oauth_status():
    """
    Return whether Google OAuth has been completed.
    """
    return {"authorized": is_authorized()}


@router.post("/revoke")
async def oauth_revoke():
    """
    Clear stored Google OAuth tokens from the local env file.
    """
    for key in ("GOOGLE_ACCESS_TOKEN", "GOOGLE_REFRESH_TOKEN", "GOOGLE_TOKEN_EXPIRY"):
        _write_env_value(key, "REPLACE_ME")
        os.environ.pop(key, None)

    log.info("Google tokens revoked")
    return {"ok": True, "message": "Google authorization removed"}
