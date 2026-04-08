# LLM Runtime
## Purpose
Verify that the required Ollama model is available before the first inference call, and cache that verification so subsequent requests pay no overhead.

## Key Responsibilities
- Check Ollama's `/api/tags` endpoint once at startup (with a 30-second delay) to confirm `mistral` is loaded.
- Cache the result so all subsequent `ensure_model()` calls are no-ops.
- Fail silently if Ollama is unreachable — let the downstream inference call fail naturally rather than blocking startup.

## Module Path
`llm_runtime.py`

## Public Interface (functions / endpoints / events)
- `ensure_model() -> None`
- `MODEL_NAME = "mistral"`
- `OLLAMA_BASE_URL = "http://127.0.0.1:11434"`

## Data Flow
`api_layer/app.py` registers a startup hook (`init_rag()`) that spawns a background thread to call `ensure_model()` after a 30-second delay — enough time for Ollama to finish loading the model after service start. All streaming and generation functions (`_ollama_stream()`, `_ollama_stream_chat()`, `/api/chat`) also call `ensure_model()` directly before making inference requests.

```
@app.on_event("startup") → init_rag()
→ threading.Thread(target=preload, delay=30s)
→ ensure_model()
→ GET http://127.0.0.1:11434/api/tags
→ check "mistral" in model names
→ set model_verified = True (cached for process lifetime)
```

## Connects To
- `api_layer/app.py` (startup hook + all inference callers)
- Ollama HTTP API at `http://127.0.0.1:11434`
- `scripts/install_ladylinux.sh` (installs Ollama and pulls `mistral` + `nomic-embed-text`)
- [[Infrastructure/Installer]]

## Known Constraints / Gotchas
- `model_verified` is a module-level boolean protected by a `threading.Lock`. It is set to `True` once and never reset — a model being removed from Ollama after startup will not be detected.
- The 30-second preload delay in `init_rag()` is a heuristic based on VM boot time. On faster hardware this can be reduced; on slower hardware the first inference request may still arrive before the model is verified.
- `ensure_model()` swallows all exceptions from the Ollama health check. If Ollama is down, the function returns without setting `model_verified = True`, and the next call will retry.
- This module only checks for `mistral`. The embedding model (`nomic-embed-text`) is verified separately by the RAG layer when `embed_query()` first runs.
- `MODEL_NAME` and `OLLAMA_BASE_URL` are module-level constants — changing the model requires editing this file and restarting the service.
