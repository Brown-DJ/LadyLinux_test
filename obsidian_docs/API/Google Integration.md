# Google Integration
## Purpose
Expose OAuth, Calendar, Gmail, and Google Fit integration endpoints for external context panels.

## Key Responsibilities
- Start and complete Google OAuth flows.
- Report and revoke authorization status.
- Return Calendar summaries and today's events.
- Return Gmail unread and inbox metadata.
- Return Google Fit daily, weekly, and summary data.

## Module Path
`api_layer/routers/google_auth_router.py`

## Public Interface (functions / endpoints / events)
- `GET /api/google/oauth/start`
- `GET /api/google/oauth/callback`
- `GET /api/google/oauth/status`
- `POST /api/google/oauth/revoke`
- `GET /api/google/calendar/today`
- `GET /api/google/calendar/summary`
- `POST /api/google/calendar/refresh`
- `GET /api/google/gmail/inbox`
- `GET /api/google/gmail/unread`
- `POST /api/google/gmail/refresh`
- `GET /api/google/fit/today`
- `GET /api/google/fit/summary`
- `POST /api/google/fit/refresh`
- `GET /api/google/fit/week`
- `GET /api/google/health/oauth/start`
- `GET /api/google/health/oauth/callback`
- `GET /api/google/health/oauth/status`
- `POST /api/google/health/oauth/revoke`

## Data Flow
OAuth start routes call consent URL builders and redirect the browser to Google, while callback routes exchange authorization codes for tokens through the matching auth service. Calendar, Gmail, and Fit routes check authorization, read or invalidate `google_cache`, and delegate to their service modules for API data and summaries. Revoke routes write placeholder token values back to the environment store, remove process environment entries, and invalidate cached Fit data where needed.

## Connects To
- `api_layer/services/google_auth_service.py`
- `api_layer/services/google_calendar_service.py`
- `api_layer/services/google_gmail_service.py`
- `api_layer/services/google_fit_service.py`
- `api_layer/services/google_health_auth_service.py`
- [[API/Context Routes]]

## Known Constraints / Gotchas
- Calendar and Gmail use the general Google OAuth service; Fit uses the separate Google Health OAuth service.
- Unauthorized routes return HTTP 401 with setup guidance.
- Token revoke writes `REPLACE_ME` values through private `_write_env_value()` helpers.
- This is a combined doc for five router files, so the module path names only the first router.
