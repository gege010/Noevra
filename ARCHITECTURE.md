# Noevra architecture

## Operating model

The supported product is a local, single-owner research workspace: FastAPI serves both the browser UI and its API, SQLite persists history, and one process owns the cancellable job runtime. This keeps installation small and avoids external infrastructure. A public multi-user service requires a different identity and job-execution design; see DEPLOYMENT.md.

## Module ownership

| Module | Interface and responsibility |
| --- | --- |
| `run.py` | Bootstrap `.venv`, install the constrained runtime, and hand over to the application CLI. Standard-library-only; does not import application code before installation. |
| `src/cli.py` | Start a loopback-only server or perform a non-billing configuration/storage check. |
| `src/config.py` | Resolve environment, secret-safe settings, application paths and deployment constraints once. |
| `src/main.py` | Own application startup/shutdown, database ownership, sessions and HTTP middleware. |
| `src/api/` | Validate requests, present errors/results and stream progress. No LLM SDK is needed to serve the initial interface. |
| `src/services/provider_service.py` | Provider capabilities, endpoint validation and live account-model discovery. |
| `src/services/job_runtime.py` | Bound admission/concurrency, retain task ownership, interrupt work and close tasks on shutdown. |
| `src/services/research_service.py` | Execute the research graph and coordinate durable status/results with transient events. Graph imports are deferred until work starts. |
| `src/agents/` | Bounded planning, retrieval, provenance checks, report writing and automated review. Provider construction lives in one factory. |
| `src/repositories/` | Persist jobs, settings without credentials, reports, source records and evidence. |
| `src/db/` | Async storage, compatibility upgrades and local database process ownership. |
| `src/static/` | Existing editorial UI, authored controls, report navigation, preferences, provider connections and safe Markdown rendering. |

## Lifecycle and invariants

1. Configuration is loaded from the application root or an explicit `NOEVRA_ENV_FILE`; it never depends on where a shell happened to start. SQLite paths are resolved deterministically. Downloads are generated in memory; concurrent exports do not share a file. Installed wheels use the user's `.noevra` directory by default.
2. Startup acquires an OS lock for a local SQLite database before recovery runs. A second process cannot mark another running process's jobs interrupted. Closing the descriptor or process releases ownership; a stale filename is not an active lock.
3. The database directory is created before connection. Compatibility upgrades preserve existing columns/data and add only known missing columns. This additive upgrade path is intentionally limited; destructive or multi-version hosted migrations need a versioned migration system.
4. Admission records the job before its task starts. Task execution gets its own database session; a request-scoped session is never handed to a background task. Queue limits include active work.
5. Sources have stable IDs. Evidence must match retrieved passages, and source URLs come from the corpus. Generated model agreement does not establish scientific truth.
6. Durable report state is committed before a terminal success event. Cancelled jobs cannot be overwritten by a late result. Shutdown cancels work and disposes database connections in `finally`.
7. On restart, unfinished jobs are marked interrupted. The application does not restart inference using missing tab credentials. Users reconnect and explicitly start another investigation.
8. SSE is an observation channel. Persisted job/report endpoints support reconnects and polling; in-memory events are not a durable queue or a cross-process event bus.

## Storage and credentials

SQLite and exports live under the data directory; no external database or queue is required locally. Browser credentials remain in tab memory and are excluded from saved job settings. Optional `.env` keys are server credentials. Graph tracing is disabled for jobs carrying tab secrets; other tracing is opt-in. Raw configuration errors must not print secret inputs.

The ignored `data/` directory can still contain previously committed example fixtures. Those are not loaded as user history. Tests set a disposable data directory and empty credential environment before collection, and block unmocked provider HTTP traffic.

## Changes and verification

Prefer fixes at the module that owns a behavior, then test through its interface: startup and real temporary storage for configuration/lifecycle; mocked HTTP protocols for provider adapters; graph-node contracts for research integrity; browser interactions and rendering tests for UI behavior. Do not add adapters for hypothetical platforms or split modules solely to reduce line count.
