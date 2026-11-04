# Engineering and UX review — 2026-11-04

Scope: make Noevra a straightforward, maintainable **local, single-owner workspace**. The review used Vibecode Skills' Matt engineering guidance and Impeccable product-quality guidance, with sequential code review, deterministic tests and actual browser verification. The existing Python/FastAPI/LangGraph and plain-web stack and Noevra visual identity are preserved.

## Findings resolved

| Area | Demonstrated problem | Resolution and verification |
| --- | --- | --- |
| First installation | Manual environment activation; runtime, experiments, old UI and tests installed together | Standard-library `run.py` bootstraps `.venv`; separates runtime/development/legacy dependencies; fresh installation and `pip check` passed. |
| Configuration | Placeholder keys looked configured; paths depended on the caller's directory; config import altered global console streams | Blank optional `.env` template, old-placeholder filtering, secret-safe representations, stable paths and a CLI configuration check. Tests run the check from another directory. |
| Storage ownership | A second application process could mark the first process's jobs interrupted | OS-level SQLite ownership lock before recovery, with cross-process exclusion/release tests. Separate local workspaces also receive separate session cookie names. |
| Lifecycle | Open database resources survived shutdown; terminal job updates could race with cancellation | Cleanup in `finally`; conditional cancellation and terminal-result/progress writes. Tests confirm completed reports remain immutable and cancelled reports cannot become successes. |
| Packaging | No installable command/dependency metadata or explicit static asset packaging | `noevra` CLI entry point, package discovery and bundled assets/licenses. A wheel built successfully; UI/fonts were present and no `.env`/database was bundled. |
| Build context | Docker depended on a required `.env` and host folder permissions; local secrets/data could enter the context | Optional environment file, loopback port, non-root image, named data volume and `.dockerignore`. Compose configuration validation passed. |
| AI contracts | Empty/malformed review objects could inherit a passing score; empty plans could proceed | Pydantic plan, verification and review contracts; bounded fallback plans; invalid review becomes `UNAVAILABLE`. Regression tests include missing verdicts/scores, NaN and out-of-range scores. |
| Evidence | Writer could assume citation 1 and omit reference records after source 30 | Source numbers, origin type and dates derive from corpus records; all reference records reach the writer. A contested status requires supporting and weakening passages from distinct source records. |
| Research revisions | The final revised draft could skip review; targeted searches repeated the original plan | Review the current draft before stopping; respect revision/source/iteration limits and search the reported gaps on revisions. Source-budget allocation preserves counter-evidence lanes. |
| Retrieval | ArXiv query text was concatenated into a URL, so `&`/`+` could alter parameters | Pass query parameters through the HTTP client; regression assertion preserves the original research query. |
| Export | Windows newline conversion and shared temporary files affected download behavior | Generate Markdown/PDF response bytes directly; PDF generation runs off the event loop. The full HTTP flow verifies Markdown, bibliography and PDF downloads. |
| Tests | Tests could inherit developer secrets, touch their database, or contact public services | Disposable storage and empty credentials before collection; unmocked sync/async HTTP traffic is blocked for the application's HTTP client and newer SDK client. |
| Local HTTP access | A rebinding hostname could reach a passwordless loopback workspace | Trusted hosts derived from loopback/public-origin configuration; untrusted Host requests are rejected. Missing provider credentials fail before a job is accepted. |
| Onboarding | No clear first action when all providers were disconnected; credential labels always said optional | Inline Connect a provider action opens Connections; labels distinguish required keys, overrides and OAuth alternatives; missing keys have an inline recovery message. |
| Settings | No explicit lock action; expiry could interrupt password entry and restart polling | Settings exposes Lock workspace when protected; a lock reloads to clear tab memory. Expiry pauses observation, does not repeatedly reopen the dialog, and resumes after unlock. |
| UI mechanics | Supporting text was 10–11px; muted placeholder contrast was marginal; reveal-key state could be stale | Supporting text is at least 12px, the muted token is darker, coarse-pointer targets have a 44px minimum, reveal state resets and icons use the existing SVG system. |
| Documentation | README described an obsolete dark UI, old model lists, wrong export paths and Python 3.10 support | Replaced with a local-first quick start, troubleshooting, data/backups, current authentication and architecture. Tests and CI commands are explicit. |

## Verification record

- Fresh `.venv` installation through the actual launcher: passed; the existing developer `venv` and `.env` were preserved.
- Clean-data/no-`.env` application launch: passed. The library was empty, all eight providers were available, and no server credentials were configured in that test process.
- Python regression suite: **100 passed** on Windows/Python 3.11.6. SDK construction for all eight providers was checked without external traffic.
- Source coverage: approximately **73%**. CLI subprocess/browser verification is separate from the in-process coverage measurement; this is not exhaustive branch coverage.
- JavaScript suites: **14 passed** for rendering safety, OAuth PKCE/state, model-search selection, failed refresh and response races. The provider test double checks IDs against real HTML, so missing initialization elements are not silently fabricated.
- Ruff lint and format checks: passed. `pip check`: no broken requirements.
- Full API integration with a fake research graph and real temporary SQLite: request → owned task → durable completion → report/library/SSE → Markdown/BibTeX/PDF passed. It does not assert the quality of a live model's research.
- Browser: first-run connection route, missing-key recovery, protected unlock/lock, native-dialog behavior, keyboard theme selection, light/dark mode, reduced motion and sidebar minimize/expand were exercised. Desktop 1280px and mobile 390px had no horizontal document overflow in the inspected views. The temporary viewport override was reset.
- Impeccable detector: small-text warnings were resolved. Two remaining flags were inspected: 1.2 leading belongs to display/report headings, while body leading remains readable; the help-dialog form wraps separately padded header/body regions, so adding wrapper padding would double the inset. These are contextual exceptions, not a clean automated accessibility certification.
- Compose syntax validation: passed. Local container build/run was unavailable because the Docker Desktop Linux daemon was not running.
- CI now targets Windows/Linux and Python 3.11/3.12 with lint, formatting, tests, frontend checks and package build. Remote run results were not available through the read-only check used during this review; do not treat the configuration as an observed green matrix.

## Operational scope and remaining verification

The supported local profile uses one worker and one owner. SQLite additive compatibility upgrades preserve known older columns; destructive or hosted schema evolution needs versioned migrations. Public multi-user hosting still needs user ownership/authorization, durable distributed jobs/events, quotas and managed secrets. The current Library fetches the latest 100 jobs, and automated verification reviews a bounded source subset; source retrieval and metadata matching are not full-text scientific validation.

Live provider OAuth consent, real-account inference quotas and research quality were not exercised with the user's paid credentials. A complete automated WCAG audit, load test, macOS runtime check and local container run were not performed. The original user-owned `output/noevra-ui-audit.json` was left unchanged.

See [README.md](README.md) for startup, [ARCHITECTURE.md](ARCHITECTURE.md) for module ownership and invariants, and [DEPLOYMENT.md](DEPLOYMENT.md) for the hosted-private-workspace boundary.
