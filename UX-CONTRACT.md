# ScholarAgent interaction contract

## Canonical owners
| Capability | Owner | Verification |
|---|---|---|
| Form validation | research form + inline live error in app.js | empty question, invalid collections |
| Select/Listbox | native select | keyboard and mobile |
| Dialog | native HTML dialog with explicit close and focus restoration | Escape, close button, native focus containment |
| Feedback | shared notify/status region in app.js | success and failure messages |
| Scrollbars | global CSS tokens | all application surfaces |
| Research and library | API adapters in app.js | no invented saved jobs |

## Behavior
- New research preserves provider preferences, clears the current question only on explicit navigation, and does not silently cancel an active server job.
- Submitting validates the question and at least one source collection; failure keeps the question and settings editable.
- Exactly one EventSource/polling timer per observed job. Failure is recoverable, terminal events close connections, and reconnect falls back to bounded polling.
- Running jobs disable duplicate submission. Returning to an active job resumes observation. Completed reports are loaded through the existing report API.
- The library lists real persisted jobs, supports local text filtering, and restores reports or resumes running jobs. Failed jobs show the saved error.
- Every export uses the existing server endpoint. Copy acknowledges success through a shared live region. No browser alert/confirm/prompt.
- Report tabs use tablist semantics and arrow-key navigation. Source links permit only http/https URLs. Generated content is rendered as text or escaped Markdown.
- Evidence includes every attached passage, original source links, unresolved questions, and supported/contested/unverified/stale filtering. Scores and review outcomes are displayed only when recorded.
- Theme preference can persist locally. API keys stay only in memory and are never placed in URLs or local storage.
