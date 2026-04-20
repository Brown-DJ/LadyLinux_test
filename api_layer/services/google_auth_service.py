"""
Shared OAuth2 auth layer for Google API integrations.

Handles consent URL generation, token exchange, token refresh, and env-file
persistence. Google service modules should import get_valid_token() from here.
"""

from __future__ import annotations

import logging
import os
import time
import urllib.parse

import httpx

log = logging.getLogger("ladylinux.google_auth")

_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_REVOKE_URL = "https://oauth2.googleapis.com/revoke"

_SCOPES = " ".join(
    [
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly",
    ]
)

_ENV_FILE = "/etc/ladylinux/ladylinux.env"


def _get_env(key: str) -> str:
    """Read a value from the process environment."""
    return os.environ.get(key, "").strip()


def _write_env_value(key: str, value: str) -> None:
    """
    Update a single key=value line in the live env file.

    Preserves comments and ordering where possible. Appends the key when it does
    not already exist.
    """
    safe_value = str(value).replace("\r", "").replace("\n", "")

    try:
        with open(_ENV_FILE, "r", encoding="utf-8") as fh:
            lines = fh.readlines()

        updated = False
        new_lines: list[str] = []
        for line in lines:
            if line.startswith(f"{key}="):
                new_lines.append(f"{key}={safe_value}\n")
                updated = True
            else:
                new_lines.append(line)

        if not updated:
            new_lines.append(f"{key}={safe_value}\n")

        with open(_ENV_FILE, "w", encoding="utf-8") as fh:
            fh.writelines(new_lines)

        log.info("Wrote %s to env file", key)

    except OSError as exc:
        log.error("Failed to write %s to env file: %s", key, exc)


def build_consent_url() -> str:
    """
    Generate the Google OAuth2 consent URL.
    """
    client_id = _get_env("GOOGLE_CLIENT_ID")
    redirect_uri = _get_env("GOOGLE_REDIRECT_URI")

    if not client_id or client_id == "REPLACE_ME":
        raise ValueError("GOOGLE_CLIENT_ID not set in ladylinux.env")

    if not redirect_uri or redirect_uri == "REPLACE_ME":
        raise ValueError("GOOGLE_REDIRECT_URI not set in ladylinux.env")

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": _SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    }

    return f"{_AUTH_URL}?{urllib.parse.urlencode(params)}"


async def exchange_code_for_tokens(code: str) -> dict:
    """
    Exchange an authorization code for access and refresh tokens.
    """
    client_id = _get_env("GOOGLE_CLIENT_ID")
    client_secret = _get_env("GOOGLE_CLIENT_SECRET")
    redirect_uri = _get_env("GOOGLE_REDIRECT_URI")

    payload = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(_TOKEN_URL, data=payload, timeout=15)
        response.raise_for_status()
        tokens = response.json()

    expiry = str(int(time.time()) + tokens.get("expires_in", 3600))

    _write_env_value("GOOGLE_ACCESS_TOKEN", tokens["access_token"])
    _write_env_value("GOOGLE_TOKEN_EXPIRY", expiry)

    if tokens.get("refresh_token"):
        _write_env_value("GOOGLE_REFRESH_TOKEN", tokens["refresh_token"])

    os.environ["GOOGLE_ACCESS_TOKEN"] = tokens["access_token"]
    os.environ["GOOGLE_TOKEN_EXPIRY"] = expiry
    if tokens.get("refresh_token"):
        os.environ["GOOGLE_REFRESH_TOKEN"] = tokens["refresh_token"]

    log.info("Google tokens exchanged and written to env file")
    return tokens


async def _refresh_access_token() -> str:
    """
    Use the stored refresh token to get a new access token.
    """
    client_id = _get_env("GOOGLE_CLIENT_ID")
    client_secret = _get_env("GOOGLE_CLIENT_SECRET")
    refresh_token = _get_env("GOOGLE_REFRESH_TOKEN")

    if not refresh_token or refresh_token == "REPLACE_ME":
        raise ValueError("GOOGLE_REFRESH_TOKEN not set; OAuth consent flow required")

    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(_TOKEN_URL, data=payload, timeout=15)
        response.raise_for_status()
        tokens = response.json()

    new_token = tokens["access_token"]
    new_expiry = str(int(time.time()) + tokens.get("expires_in", 3600))

    _write_env_value("GOOGLE_ACCESS_TOKEN", new_token)
    _write_env_value("GOOGLE_TOKEN_EXPIRY", new_expiry)
    os.environ["GOOGLE_ACCESS_TOKEN"] = new_token
    os.environ["GOOGLE_TOKEN_EXPIRY"] = new_expiry

    log.info("Google access token refreshed")
    return new_token


async def get_valid_token() -> str:
    """
    Return a valid Google access token, refreshing when expiry is near.
    """
    access_token = _get_env("GOOGLE_ACCESS_TOKEN")
    expiry_str = _get_env("GOOGLE_TOKEN_EXPIRY")

    if not access_token or access_token == "REPLACE_ME":
        raise ValueError("Google OAuth not authorized; visit /api/google/oauth/start")

    try:
        expiry = int(expiry_str)
        if time.time() >= expiry - 300:
            log.info("Access token expiring soon; refreshing")
            return await _refresh_access_token()
    except (ValueError, TypeError):
        return await _refresh_access_token()

    return access_token


def is_authorized() -> bool:
    """Return whether Google OAuth has been completed."""
    token = _get_env("GOOGLE_ACCESS_TOKEN")
    return bool(token and token != "REPLACE_ME")
