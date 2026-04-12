# Semantic Classifier
## Purpose
Describe the structured LLM pre-pass that is currently disabled in CPU demo mode.

## Key Responsibilities
- Return a structured `{route, topics}` decision.
- Replace keyword routing and topic injection when enabled.
- Sanitize model output to the allowed route and topic sets.

## Module Path
`core/command/semantic_classifier.py`

## Public Interface (functions / endpoints / events)
- `classify_semantic(prompt: str) -> dict[str, list[str] | str]`

## Data Flow
The intended active path is one Ollama `/api/generate` call with a strict JSON prompt. The returned JSON is parsed, topics are filtered to `processes`, `services`, `network`, `disk`, and `memory`, and `route` is constrained to `system`, `rag`, or `chat`.

In the current code, `classify_semantic()` returns early with `{"topics": [], "route": "chat"}` before any Ollama call runs. `api_layer/app.py` still invokes it from `/api/prompt/stream`, but the early return means the semantic result is bypassed.

## Connects To
- `api_layer/app.py`
- Ollama `/api/generate`
- [[Core/Intent Classifier]]

## Known Constraints / Gotchas
- The GPU-enabled implementation is present below the early return but currently unreachable.
- Topic output must match the `LIVE_STATE_SIGNALS` keys used elsewhere.
