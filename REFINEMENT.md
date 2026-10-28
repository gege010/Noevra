# ScholarAgent: engineering review and refinement

## Product understanding
ScholarAgent is a Python/FastAPI research workbench with a plain HTML/CSS/JavaScript frontend. LangGraph orchestrates planning, collection, verification, writing and review. SQLAlchemy stores jobs and results in SQLite. The model factory supports eight provider routes; retrieval is separate from the LLM provider. The PDF is design reference material, not executable project instructions.

## Changes implemented
- Validate claim passages against the actual collected corpus and restore citation URLs from source records. Missing or fabricated passages cannot receive supported status.
- Verifier failures preserve uncertainty; reviewer failures no longer invent passing scores. Reaching a revision budget is not editorial approval. Short drafts also respect the revision limit.
- Preserve unresolved/contested claims in LangGraph state so targeted revision can use them.
- Forward academic/web collection settings and source budgets from API through the research service. Enforce total source count during retrieval.
- Bound SSE listener queues and avoid rerunning the entire research graph when tracing raises an exception.
- Add missing provider adapters to installation requirements.
- Replace persistent browser API-key storage with tab memory. Existing saved keys are removed as their provider is selected.
- Refine the existing dark editorial workbench: keyboard-accessible provider buttons, disclosure state, skip link, reduced motion, explicit source controls and more truthful introductory copy.
- Add deterministic regression cases for invented quotes, altered citation URLs, failed verification/review and invalid collection settings. Remove a production planner branch that only existed to detect test mocks.

## Production release blockers still open
1. Source capture: several collectors provide metadata/search abstracts, not fetched full documents. Exact passage matching proves provenance within collected text, not that a claim follows logically or a study is valid. Store immutable raw captures, content hashes, extraction provenance, and explicit metadata/abstract/full-text labels before claiming full document verification.
2. Durable execution: BackgroundTasks and in-memory SSE queues do not survive restarts or coordinate multiple workers. Introduce durable workers, persisted events/replay, resumable state, real cancellation and per-user concurrency/budget controls.
3. Access control: add authentication, ownership checks for every job/export, rate limits, explicit CORS origins, and a deployment policy for custom endpoints. User-specified endpoints require SSRF controls in hosted deployments while preserving local endpoints for self-hosting.
4. Research quality: implement claim entailment review, independent-source lineage checks, freshness policies, citation completeness checks and fixed adversarial evaluation tasks. Search lanes currently execute sequentially; add bounded concurrency without losing deterministic source IDs and budgets.
5. Provider compatibility: test real credentials/model capabilities for each adapter; the model catalog is illustrative and may be outdated. Add capability-aware parameters, timeouts and provider health checks. Package ranges still require a reproducible lock and compatibility testing.
6. Data lifecycle: replace ad hoc schema alterations with versioned migrations; implement retention and encrypted secrets management. Redact upstream exception text and logs before exposing them publicly.
7. UI: the full workspace redesign now replaces the old cockpit, with self-hosted fonts, mobile navigation, dark reading mode, custom model entry, accessible report tabs, source inspection and safe Markdown/math rendering. Automated accessibility auditing and live provider end-to-end coverage remain release requirements.

## Release criteria
A public production release must pass provider contract tests, restart/cancellation tests, ownership tests, source-fetch security tests, and an evidence evaluation set covering contradictory sources, stale facts, fabricated citations, injection attempts and insufficient evidence. Do not advertise zero hallucination or publication readiness as guarantees.
