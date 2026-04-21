# Context Routes
## Purpose
Expose weather and location context refresh endpoints for the UI and assistant.

## Key Responsibilities
- Serve the latest cached weather snapshot.
- Force an immediate weather refresh cycle.
- Clear and refresh the cached IP-derived location.

## Module Path
`api_layer/routes/context.py`

## Public Interface (functions / endpoints / events)
- `GET /api/context/weather`
- `POST /api/context/weather/refresh`
- `POST /api/context/location/refresh`

## Data Flow
`GET /api/context/weather` calls `weather_service.get_weather()` and wraps the in-memory snapshot in an `{ok, weather}` response. `POST /api/context/weather/refresh` calls `weather_service.force_refresh()` to perform the location, NWS grid, and forecast fetch cycle. `POST /api/context/location/refresh` calls `location_service.refresh_location()` to clear the disk cache and refetch geolocation.

## Connects To
- `api_layer/services/weather_service.py`
- `api_layer/services/location_service.py`
- [[Services/Weather Service]]

## Known Constraints / Gotchas
- Weather can return `ok=False` when no cached or fresh forecast is available.
- Refresh calls may perform live network I/O to IP geolocation providers and api.weather.gov.
- Location refresh is IP-based and may not represent the user's exact physical location.
