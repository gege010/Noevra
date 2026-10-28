# ScholarAgent interaction contract

## Canonical owners
| Capability | Owner | Verification |
|---|---|---|
| Form validation | research form + inline live error in app.js | empty question, invalid collections |
| Select/Listbox | shared controls.js authored listbox + native form owner | keyboard, focus, collision and mobile |
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

## Customization and connections
- Sidebar can minimize to icons and expand; choice survives reload. Mobile uses its navigation dialog.
- Workspace settings own persistent theme/system theme, report text size, reduced motion and defaults. Provider/model selection in the composer opens a separate per-investigation setup dialog. Changing global defaults does not change an already configured investigation; defaults apply at the next New research.
- In this report marks the active section on click and scroll using aria-current and a visible selected treatment.
- Shared select popovers own keyboard navigation, typeahead, selected state, outside click, Escape/Tab, focus restoration and viewport collision. Dialog closure closes open popovers.
- OpenRouter OAuth uses an unpredictable state, S256 challenge, a one-use verifier and a ten-minute callback window. Credentials are exchanged via a fixed upstream on the backend, returned with no-store and held only in the tab memory. Provider passwords never pass through this application.
- Disconnect clears the tab credential; the UI links to the provider for actual key revocation. OAuth authorization and its billing approval belong to the user. Other providers retain API-key/local-endpoint authentication.
