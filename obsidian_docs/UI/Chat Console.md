# Chat Console
## Purpose
Drive the browser-side chat interface — sending prompts to the streaming backend, parsing NDJSON events, rendering responses incrementally, and maintaining bounded conversation history for multi-turn context.

## Key Responsibilities
- Bind the chat form (`ucsChatForm`) and input (`ucsPrompt`).
- Build and send `POST /api/prompt/stream` requests with prompt, history, and page context.
- Read the response as a stream, split on newlines, and parse each line as NDJSON.
- Render `token` events incrementally into the DOM as they arrive.
- Handle `done`, `tool`, `command`, `ui`, and `error` event types discretely.
- Maintain `conversationHistory` in `sessionStorage` bounded to the last 10 exchanges.
- Expose `sendPrompt()` and `processAssistantReply()` on `window` for use by other modules.

## Module Path
`static/js/chat.js`

## Public Interface (functions / endpoints / events)
- `sendPrompt(prompt: string) -> Promise<string>` — sends a prompt, returns the final reply text
- `processAssistantReply(prompt, rawReply, options)` — post-processes a reply for structured action handling
- `initChat()` — binds the form submit handler and restores history from `sessionStorage`
- `window.sendPrompt`
- `window.processAssistantReply`
- Form ID: `ucsChatForm`
- Input ID: `ucsPrompt`

## Data Flow
```
User types prompt → ucsChatForm submit
→ sendPrompt(prompt)
  → push user turn to conversationHistory
  → POST /api/prompt/stream {prompt, messages: history[-10:], context}
  → stream reader loop:
      token  → append to accumulatedText, update DOM live
      done   → record ragMeta, set finalPayload
      tool / command / ui → set finalPayload, trigger UI side-effects
      error  → throw
  → processAssistantReply(prompt, finalPayload)
  → push assistant turn to conversationHistory
  → persist history to sessionStorage
```

## Page Context Mapping
`sendPrompt()` maps `window.location.pathname` to a backend context string inline:

| Path | Context value sent to backend |
|---|---|
| `/` | `dashboard` |
| `/os` | `system-monitor` |
| `/network` | `network-manager` |
| `/users` | `user-manager` |
| `/logs` | `log-viewer` |
| (other) | `unknown` |

## NDJSON Event Handling

| Event type | Action |
|---|---|
| `token` | Append `event.text` to `accumulatedText`, update DOM with `replaceLastAssistantLine()` |
| `done` | Record `{model, retrievedChunks}` in `lastRagMeta`, finalize `finalPayload` |
| `tool` | Format structured data (e.g. service list), trigger `window.loadServices()` if present |
| `command` | Embed structured payload as `%%LLACTION%%` marker in `finalPayload` |
| `ui` + `set_theme` | Set `finalPayload` to `event.message` |
| `ui` + `set_ui_override` | Extract `--css-var` keys, apply via `document.documentElement.style.setProperty()` |
| `error` | Throw `Error(event.message)` |

## Structured Action Markers
`processAssistantReply()` scans `finalPayload` for `%%LLACTION%%` markers followed by a JSON object. It extracts the payload, strips the marker from the display text, and dispatches to `window.LadyActions` or `window.DesignEngine` depending on `route` and `action` fields.

## Conversation History
- Stored in `sessionStorage` under key `ladyConversationHistory`
- Bounded to 10 entries (5 exchanges) — older entries are dropped
- Each entry: `{role: "user"|"assistant", content: string}`
- Sent to backend as `messages` array on every request
- History is trimmed to 4 messages (2 exchanges) server-side for CPU latency reasons

## Connects To
- `/api/prompt/stream` (primary backend endpoint)
- `static/js/ladyWidget.js` (consumes `window.sendPrompt`)
- `static/js/voice_client.js` (submits form programmatically for voice transcripts)
- `static/js/main.js` (calls `initChat()` on page load)
- `window.LadyActions` (action dispatcher for tool/command responses)
- `window.DesignEngine` (CSS override dispatcher)
- `window.marked` (Markdown rendering for assistant replies — CDN loaded)
- [[API/Prompt Routes]]
- [[UI/Lady Widget]]
- [[UI/Main JS]]

## Known Constraints / Gotchas
- History is `sessionStorage` only — it does not persist across browser tabs or page refreshes beyond the session. Cross-page history requires the existing `sessionStorage` pattern to be active (confirmed implemented).
- The page context mapping is inline in `sendPrompt()`, not a named constant — if new pages are added, this mapping must be updated here.
- `streamToElement()` is archived — it no longer exists in the active file. Archived versions exist in `static/js/archive/`.
- `window.marked` is loaded from a CDN. If the CDN is unavailable, the fallback sets `textContent` instead of `innerHTML` — no Markdown rendering.
- History is trimmed to last 4 messages server-side (`_stream_llm_response()`) to limit first-token latency on the CPU-only VM. The client sends up to 10 but only 4 are used.
- `%%LLACTION%%` marker parsing uses a custom bracket-depth JSON extractor rather than `JSON.parse()` on the full string — this handles cases where the model embeds the marker mid-response.
