# UI redesign verification — 2026-10-28

- Backend unit suite: 39 passed; two existing warnings (LangGraph deprecation and repository test mock).
- Browser renderer suite: 8 passed, including raw HTML escaping, unsafe URL rejection, citation actions, code isolation, duplicate heading IDs, escaped table pipes, preserved TeX and remote-image suppression.
- JavaScript syntax and git whitespace checks passed.
- Desktop inspected at default 1280px viewport; mobile inspected at 390px. Neither home layout has horizontal document overflow.
- Checked real persisted library entries and a stored DPO/RLHF report, provider switching to Ollama and back, endpoint disclosure, empty-query validation, suggested question insertion, citation-to-source navigation and source filtering with stable reference numbers.
- Light and dark modes inspected. No browser error logs in the final pass.
- Native dialogs provide focus containment and Escape behavior; report tabs implement arrow/Home/End keyboard navigation. A complete automated accessibility audit was not run.
- Full research runs using live paid provider credentials were not started during this UI task. SSE and polling remain connected to the existing API; live-provider execution and all export formats need end-to-end coverage before a public release.
- Screenshots are actual local app renders: workspace-desktop.jpg, workspace-mobile.jpg, research-report.jpg.

## Interaction and OAuth refinement
- Backend suite: 49 passed (including ten OAuth exchange/validation/failure cases).
- Node suites: 11 passed (eight renderer cases plus PKCE randomness/challenge, callback mismatch/expiry and safe authorization URL cases).
- Browser: minimized sidebar survives reload; all primary icon actions remain available; global settings are distinct from Research setup; theme dropdown selected by keyboard; Escape closes the listbox without closing its dialog; defaults affect the next New research; provider-specific OAuth connection UI is present.
- Report navigation visibly selects the clicked section and exposes aria-current=location; scrolling uses the same active-location state.
- Settings and shared dropdowns inspected at 1280px and 390px. Mobile settings fit the viewport; select popovers appear above dialog content without clipping.
- OAuth uses official OpenRouter PKCE, a fixed backend exchange origin, one-time tab verifier/state, a ten-minute expiry and no-store responses. Live account authorization was not performed; protocol/network paths were tested with mocked upstream responses and pure frontend security tests.
- Additional screenshots: workspace-settings.jpg, settings-mobile.jpg, sidebar-minimized.jpg, report-active-section.jpg.
