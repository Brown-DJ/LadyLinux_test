# Weather Service
## Purpose
Fetch, cache, and serve local weather context from the National Weather Service.

## Key Responsibilities
- Return the latest in-memory weather snapshot without live I/O.
- Resolve IP-derived latitude and longitude to an NWS forecast grid URL.
- Cache NWS grid resolution for seven days.
- Store the last successful forecast to disk as a fallback.
- Run an optional background polling loop.

## Module Path
`api_layer/services/weather_service.py`

## Public Interface (functions / endpoints / events)
- `get_weather() -> dict | None`
- `start_polling(interval_seconds: int = 600) -> None`
- `force_refresh() -> dict | None`
- `get_location() -> dict | None`
- `refresh_location() -> dict | None`

## Data Flow
Routes call `weather_service.get_weather()` for the current in-memory snapshot or `force_refresh()` for an immediate refresh. Refreshing calls `location_service.get_location()`, resolves a forecast URL with `_resolve_grid()`, fetches the NWS forecast with `_fetch_forecast()`, normalizes the first forecast periods with `_normalize_forecast()`, writes the cache file, and updates `_current_weather`. Location lookups use `location_service`, which checks a 24-hour disk cache before trying `ipinfo.io` and `ipapi.co`.

## Connects To
- `api_layer/routes/context.py`
- `api_layer/services/location_service.py`
- `core/startup/weather_init.py`
- [[API/Context Routes]]
- [[RAG/Ingest API Data]]

## Known Constraints / Gotchas
- NWS data uses `https://api.weather.gov` and does not require an API key.
- Grid cache TTL is seven days; forecast cache is a fallback file, not a strict freshness guarantee.
- IP geolocation can be imprecise and depends on external providers.
- `start_polling()` is guarded so only one weather thread starts per process.
