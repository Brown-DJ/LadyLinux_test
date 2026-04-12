# Voice Socket
## Purpose
Provide a dedicated WebSocket channel for browser-driven voice sessions, handling the full lifecycle from recording start through transcript relay, prompt execution, and TTS stub events.

> **Critical constraint:** Voice responses use `evaluate_prompt()` directly — they go through the command kernel only. Voice does NOT reach RAG retrieval or LLM chat generation in Phase 1.

## Key Responsibilities
- Accept voice session lifecycle events (`voice_start`, `voice_stop`).
- Relay final browser speech-to-text transcripts back as `stt_final`.
- Execute transcripts through the command kernel and return `assistant_final`.
- Emit `tts_started` and `tts_finished` stub events for Phase 1 client compatibility.
- Carry a `source` tag (`"console"` or `"widget"`) through all events so the frontend renders to the correct surface.
- Keep each connection fully isolated — no shared state with `/ws/ui` or `UIEventBus`.

## Module Path
`api_layer/routes/voice_ws.py`

## Public Interface (functions / endpoints / events)

**Client → Server:**
| Event | Payload | Description |
|---|---|---|
| `voice_start` | `{source}` | Recording began |
| `voice_stop` | `{source}` | Recording stopped |
| `voice_text_final` | `{text, source}` | Browser STT produced final transcript |
| `tts_request` | `{source}` | Client requests server-side TTS (Phase 1 stub) |

**Server → Client:**
| Event | Payload | Description |
|---|---|---|
| `voice_ready` | — | Sent on connect — handshake confirmation |
| `stt_final` | `{text, source}` | Echo of confirmed transcript |
| `assistant_final` | `{text, source}` | Command kernel response text |
| `tts_started` | `{source}` | Phase 1 stub — no audio yet |
| `tts_finished` | `{source}` | Phase 1 stub — no audio yet |
| `tts_audio` | `{audio_b64, mime, source}` | Phase 2 — not yet populated |
| `voice_error` | `{message, source}` | Error in any phase |

## Data Flow
```
browser SpeechRecognition (voice_client.js)
→ WS send: {event: "voice_text_final", text: "...", source: "console"}

voice_websocket() receives text
→ WS send: {event: "stt_final", text: "...", source: "console"}
→ evaluate_prompt(text)          ← command kernel only, no RAG
→ WS send: {event: "assistant_final", text: response, source: "console"}
→ WS send: {event: "tts_started", source: "console"}
→ WS send: {event: "tts_finished", source: "console"}

voice_client.js receives assistant_final
→ renderAssistantResponse(source, text)
→ speakText(text, source)        ← browser TTS (Phase 1)
```

## Phase Roadmap
- **Phase 1 (current):** Browser `SpeechRecognition` → text → WS → command kernel → browser TTS. No server-side STT or TTS.
- **Phase 2 (planned):** Server-side TTS engine populates `audio_b64` in `tts_audio` events. STT source may also move server-side.

## Connects To
- `core/command/command_kernel.py` (`evaluate_prompt()` — only pipeline used for voice)
- `static/js/voice_client.js` (browser counterpart)
- `static/js/ladyWidget.js` (widget voice surface)
- `static/js/chat.js` (console voice surface — `renderUserTranscript` submits the chat form)
- [[Core/Command Kernel]]
- [[UI/Voice Client]]
- [[UI/Chat Console]]
- [[WebSocket/UI Socket]]

## Known Constraints / Gotchas
- Voice bypasses the full `/api/prompt/stream` pipeline — `evaluate_prompt()` is the command kernel only. RAG, LLM chat, memory router, and session history are all unreachable from voice in Phase 1.
- `tts_request` events are logged and ignored — no server-side TTS is implemented yet.
- Each WebSocket connection is fully independent — there is no shared session bus between voice connections or between voice and `/ws/ui`.
- If `evaluate_prompt()` returns `None` (no kernel match), the response text will be `"None"` — the voice path has no fallback to RAG or chat. This is a known limitation until Phase 2.
- The `source` field defaults to `"console"` if absent from the client message — this prevents rendering errors but may cause display issues if a new surface is added without updating the client.
