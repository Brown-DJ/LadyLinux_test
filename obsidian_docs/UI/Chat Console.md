# Chat Console
## Purpose
Document the main browser chat client used on the Unified Control Surface pages.

## Key Responsibilities
- Bind the chat form and prompt input.
- Send prompt requests to the streaming backend.
- Parse NDJSON events and incrementally render assistant output.
- Maintain bounded conversation history and action-handling helpers.

## Module Path
`static/js/chat.js`

## Public Interface (functions / endpoints / events)
- Form ID: `ucsChatForm`
- Input ID: `ucsPrompt`
- `sendPrompt(prompt)`
- `processAssistantReply(prompt, rawReply, options)`
- `initChat()`
- `window.sendPrompt`
- `window.processAssistantReply`

## Data Flow
`sendPrompt()` pushes the user turn into `conversationHistory`, then `fetch()`es `POST /api/prompt/stream` with `{prompt, messages, context}`. The current page path is mapped inline to backend context values: `/ -> dashboard`, `/os -> system-monitor`, `/network -> network-manager`, `/users -> user-manager`, `/logs -> log-viewer`. The response body is read as a stream, split on newlines, parsed as NDJSON, and rendered according to `token`, `done`, `tool`, `command`, `ui`, or `error` events.

## Connects To
- `/api/prompt/stream`
- `static/js/ladyWidget.js`
- `static/js/main.js`
- `window.LadyActions`
- `window.DesignEngine`
- [[API/Prompt Routes]]
- [[UI/Lady Widget]]
- [[UI/Main JS]]

## Known Constraints / Gotchas
- The backend comment references a `PAGE_CONTEXT_MAP`, but the current frontend keeps that mapping inline inside `sendPrompt()` rather than as a named constant.
- The current file no longer uses `streamToElement()`; archived versions still exist in `static/js/chat_old.js`, `static/js/chat_js_tossed`, and `static/js/archive/`.
