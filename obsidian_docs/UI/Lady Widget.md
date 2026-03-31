# Lady Widget
## Purpose
Document the floating mini-console widget.

## Key Responsibilities
- Capture Enter-key prompts from the widget input.
- Reuse the shared chat transport and reply-processing pipeline.
- Render lightweight widget-local message bubbles.

## Module Path
`static/js/ladyWidget.js`

## Public Interface (functions / endpoints / events)
- Input ID: `lady-input`
- Output ID: `lady-response`

## Data Flow
When the user presses Enter in `lady-input`, the widget appends a local user bubble, calls `window.sendPrompt(prompt)` from `chat.js`, optionally forwards the raw reply to `window.processAssistantReply()`, then appends a widget-local assistant bubble.

## Connects To
- `static/js/chat.js`
- `static/js/voice_client.js`
- [[UI/Chat Console]]
- [[UI/Voice Client]]

## Known Constraints / Gotchas
- The widget depends on `window.sendPrompt` and `window.processAssistantReply`; if `chat.js` is not loaded first, it fails with `Chat transport unavailable`.
- The widget renders the raw reply text after `processAssistantReply()` runs; it does not have its own NDJSON parser.
