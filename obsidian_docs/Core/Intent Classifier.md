# Intent Classifier
## Purpose
Describe the keyword-based live-topic detector used as the non-semantic fallback.

## Key Responsibilities
- Maintain the `LIVE_STATE_SIGNALS` keyword map.
- Detect which live-state topic blocks to inject into prompts.
- Provide a zero-LLM fallback when the semantic classifier is disabled or unavailable.

## Module Path
`core/command/intent_classifier.py`

## Public Interface (functions / endpoints / events)
- `LIVE_STATE_SIGNALS`
- `detect_live_topics(query: str) -> list[str]`

## Data Flow
`detect_live_topics()` lowercases the query and returns every topic whose keyword list contains at least one substring match. `api_layer/app.py` uses that result in `_build_live_state_block()` when no precomputed semantic topics are supplied.

The five live-state topics are:
- `processes`
- `services`
- `network`
- `disk`
- `memory`

## Connects To
- `api_layer/app.py`
- `core/rag/system_provider.py`

## Known Constraints / Gotchas
- This is a substring matcher, so broad words like `service` or `network` can trigger topic injection easily.
- Non-streaming callers depend on this path because `/ask_rag` does not run the semantic pre-pass.
