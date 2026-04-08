# System Provider
## Purpose
Collect lightweight live runtime snapshots of OS state on demand so prompts can include current processes, services, memory, disk, and network data without polling these values continuously.

## Key Responsibilities
- Sample up to 50 running processes with PID, user, status, and name.
- List all running systemd services via `systemctl`.
- Return network interface addresses via `psutil`.
- Return disk usage for `/` via `psutil`.
- Return RAM and swap usage via `psutil`.
- Tail arbitrary log files for supplementary context.
- Combine any subset of the above into a single `snapshot()` call keyed by topic name.

## Module Path
`core/rag/system_provider.py`

## Public Interface (functions / endpoints / events)
- `SystemProvider.get_processes() -> str`
- `SystemProvider.get_services() -> str`
- `SystemProvider.get_network() -> str`
- `SystemProvider.get_disk() -> str`
- `SystemProvider.get_memory() -> str`
- `SystemProvider.snapshot(topics: list[str]) -> dict[str, str]`
- `SystemProvider._tail(path: str, lines: int = 50) -> str`

## Data Flow
`api_layer/app.py` instantiates `SYSTEM_PROVIDER = SystemProvider()` once at module load. Inside `_build_live_state_block()`, after resolving the topic list from page defaults and query signals, it calls `SYSTEM_PROVIDER.snapshot(all_topics)`. Each returned string is appended as a `[LIVE <TOPIC>]` block in the prompt.

```
classify_semantic() / detect_live_topics() → topics list
+ _PAGE_DEFAULT_TOPICS[page_context]
→ SYSTEM_PROVIDER.snapshot(all_topics)
→ dict of {topic: formatted_string}
→ injected as [LIVE PROCESSES], [LIVE SERVICES], etc.
```

## Valid Topic Keys (for `snapshot()`)
| Key | Source | Output |
|---|---|---|
| `processes` | `psutil.process_iter` | PID / user / status / name table, capped at 50 rows |
| `services` | `systemctl list-units --state=running` | Raw systemctl output |
| `network` | `psutil.net_if_addrs()` | Interface / address table, capped at 20 rows |
| `disk` | `psutil.disk_usage("/")` | Total / used / free / percent for `/` |
| `memory` | `psutil.virtual_memory()` + `swap_memory()` | RAM and SWAP table |
| `logs` | `tail /var/log/syslog` | Last 50 lines |
| `auth` | `tail /var/log/auth.log` | Last 30 lines |

## Connects To
- `api_layer/app.py` (`SYSTEM_PROVIDER`, `_build_live_state_block()`)
- `core/command/intent_classifier.py` (topic key names must match `LIVE_STATE_SIGNALS`)
- `core/command/semantic_classifier.py` (topic key names must match `_VALID_TOPICS`)
- [[Core/Intent Classifier]]
- [[Core/Semantic Classifier]]

## Known Constraints / Gotchas
- `psutil` is a hard dependency — unlike `api_layer/services/system_service.py` which has a fallback, `SystemProvider` will raise `ImportError` if `psutil` is missing.
- Process list is capped at 50 rows intentionally — Mistral's context window on the CPU-only VM cannot handle a full `ps aux`.
- Network interfaces are capped at 20 rows and each interface shows at most 4 addresses.
- `snapshot()` silently skips unknown topic keys — callers that pass an unrecognised topic get no entry for it in the returned dict.
- `_tail()` has a 3-second timeout and returns an error string on failure — it never raises.
- Topic keys must stay in sync with `LIVE_STATE_SIGNALS` in `core/command/intent_classifier.py` and `_VALID_TOPICS` in `core/command/semantic_classifier.py`. Adding a new topic requires updating all three places.
