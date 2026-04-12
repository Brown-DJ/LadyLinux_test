# Voice Client
## Purpose
Document the shared browser voice-input client used by both the console and the widget.

## Key Responsibilities
- Manage the `/ws/voice` connection and reconnect loop.
- Drive browser `SpeechRecognition`.
- Reflect per-surface voice state into the mic buttons.
- Fall back to browser speech synthesis for spoken output.

## Module Path
`static/js/voice_client.js`

## Public Interface (functions / endpoints / events)
- `window.voiceClient`
- `startVoice(source)`
- `stopVoice(source)`
- `getState()`
- Mic button attributes: `data-mic-btn`, `data-voice-source`

## Data Flow
On `DOMContentLoaded`, the module opens `ws://<host>/ws/voice` and registers delegated click handling for `[data-mic-btn]`. Each source (`console` or `widget`) maintains its own state machine: `idle -> listening -> processing -> speaking -> error`. Final browser transcripts are sent as `voice_text_final`; server responses are mapped back into the correct surface using the `source` field.

## Connects To
- `/ws/voice`
- `static/js/chat.js`
- `static/js/ladyWidget.js`

## Known Constraints / Gotchas
- `SpeechRecognition` support is browser-dependent and currently expects Chrome or Edge behavior.
- The websocket URL is hardcoded as `ws://`; there is no `wss://` branch in the current file.
