from __future__ import annotations

from fastapi import APIRouter

from api_layer.services import location_service, weather_service

router = APIRouter(prefix="/api/context", tags=["context"])


@router.get("/weather")
def get_weather() -> dict:
    """Return the latest cached weather data."""
    data = weather_service.get_weather()
    if data:
        return {"ok": True, "weather": data}
    return {"ok": False, "weather": None, "error": "weather unavailable"}


@router.post("/weather/refresh")
def refresh_weather() -> dict:
    """Force a fresh location and weather fetch cycle."""
    result = weather_service.force_refresh()
    return {"ok": result is not None, "weather": result}


@router.post("/location/refresh")
def refresh_location() -> dict:
    """Clear the location cache and re-fetch from an IP geolocation provider."""
    location = location_service.refresh_location()
    return {"ok": location is not None, "location": location}
