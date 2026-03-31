# Voice Socket
## Purpose
Document the dedicated websocket channel for browser-driven voice sessions.

> **Important constraint:** Voice responses use `evaluate_prompt()` directly — they go through the command kernel only. Voice does NOT reach RAG retrieval or LLM chat generation.

## Key Responsibilities
- Accept voice session lifecycle events.
- Relay final browser speech-to-text transcripts.
- Return assistant text responses for the originating UI surface.
- Stub out server-side TTS events.

## Module Path
- `api_layer/routes/voice_ws.py`
- `static/js/voice_client.js`

## Public Interface (functions / endpoints / events)
- `WebSocket /ws/voice`
- Client events: `voice_start`, `voice_stop`, `voice_text_final`, `tts_request`
- Server events: `voice_ready`, `stt_final`, `assistant_final`, `tts_started`, `tts_finished`, `voice_error`
- Reserved server event: `tts_audio`

## Data Flow
Phase 1 runs browser `SpeechRecognition` in `static/js/voice_client.js`. When speech is finalized, the client sends `voice_text_final` over `/ws/voice`. The server echoes `stt_final`, calls `evaluate_prompt()` from the command kernel, then sends `assistant_final`, `tts_started`, and `tts_finished`. The `source` tag (`console` or `widget`) is carried through every relevant event so the frontend can render to the correct surface.

## Connects To
- `core/command/command_kernel.py`
- `static/js/voice_client.js`
- `static/js/chat.js`
- `static/js/ladyWidget.js`
- [[UI/Voice Client]]
- [[Core/Command Kernel]]
- [[UI/Chat Console]]
- [[UI/Lady Widget]]

## Known Constraints / Gotchas
- The voice route currently uses `evaluate_prompt()` directly, not the full `/api/prompt/stream` pipeline, so it does not reach RAG or LLM chat generation.
- `tts_audio` handling exists on the client, but the server does not currently populate `audio_b64`.
- `/ws/voice` is isolated and has no shared state with `/ws/ui`.
