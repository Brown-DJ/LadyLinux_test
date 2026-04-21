# Log Routes
## Purpose
Expose recent, service, journal, file, LadyLinux, and failed-ingest log views over HTTP.

## Key Responsibilities
- Return recent and error-focused logs.
- Fetch logs for a named service or journal unit.
- List and read allowed log files.
- Tail LadyLinux-specific logs.
- Combine failed RAG ingest files for debugging.

## Module Path
`api_layer/routes/logs.py`

## Public Interface (functions / endpoints / events)
- `GET /api/logs/recent`
- `GET /api/logs/errors`
- `GET /api/logs/service/{name}`
- `GET /api/logs/journal`
- `GET /api/logs/files`
- `GET /api/logs/file`
- `GET /api/logs/ladylinux`
- `GET /api/logs/failed-ingest`

## Data Flow
Most endpoints delegate directly to `api_layer.services.log_service` with a bounded `lines` query parameter. Service log validation errors and file read failures are converted to HTTP 400 responses. `GET /api/logs/failed-ingest` reads files from `/var/lib/ladylinux/rag_ingest/_failed`, tails each file, and returns a combined list without going through `log_service`.

## Connects To
- `api_layer/services/log_service.py`
- `core/memory/log_reader.py`
- [[Core/Memory Log Reader]]

## Known Constraints / Gotchas
- `lines` is constrained to 1-500 by FastAPI `Query`.
- Failed-ingest logs are read only from `/var/lib/ladylinux/rag_ingest/_failed`.
- File path safety is enforced in `log_service.read_log_file()`, not in the route body itself.
