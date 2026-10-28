# Noevra deployment contract

Noevra currently deploys as a **private research workspace with one application worker**. A password protects the shared library, credentials supplied by the server, and research operations. This is not a multi-tenant public service: there are no per-user ownership boundaries, organization roles, distributed queue, or shared SSE broker.

## Local use

Install with `pip install -r requirements.txt -c constraints.txt`, then run `uvicorn src.main:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log`. Open `http://127.0.0.1:8000`. The direct dependency constraints capture the tested versions; they are not a complete transitive lockfile. Keep `.env` out of Git. Optional server API keys are detected; models are fetched from provider APIs on connection or selection, not bundled in the interface.

## Hosted private workspace

Set `APP_ENV=production`, `APP_PUBLIC_URL=https://your-exact-host.example`, a random `WORKSPACE_PASSWORD` of at least 16 characters, and a distinct random `SESSION_SECRET` of at least 32 characters. Startup rejects missing production credentials or a non-HTTPS public URL. Use a TLS reverse proxy with SSE buffering disabled, streaming idle timeout longer than the configured research timeout, and a trusted proxy configuration. Do not expose the application port directly. The Compose binding defaults to loopback.

Use `docker compose up --build app`. The image runs as UID 10001; ensure mounted `data/` is writable by that UID on Linux. Persist and back up `data/`, which contains the database and reports. The legacy Streamlit application is optional under the `legacy-ui` profile and is not the supported web workspace. Build/container execution requires Docker and remains a separate deployment verification step.

One Uvicorn worker is required: admission, cancellation, and SSE live queues are process-local. `MAX_CONCURRENT_JOBS` bounds active work; `MAX_QUEUED_JOBS` bounds accepted work including active jobs. Excess requests receive 429. `RESEARCH_TIMEOUT_SECONDS` bounds a running graph. Cancel requests interrupt queued or active tasks. A cancelled job cannot later overwrite its durable result with success. Shutdown cancels pending tasks; startup marks interrupted jobs failed with an actionable message. Jobs are not automatically restarted because tab credentials are intentionally not persisted. A restart or lost connection does not imply a provider refunded work already executed.

`GET /api/v1/live` checks process liveness without provider calls. `/api/v1/health` is an authenticated dependency diagnostic; provider usage diagnostics do not launch paid research searches. Browser mutations are same-origin by default. Configure `ALLOWED_ORIGINS` as a JSON list only when another trusted frontend is necessary. For Ollama or custom gateways in production, explicitly list exact origins in `CUSTOM_LLM_ALLOWED_ORIGINS`; redirects are not followed by model discovery. Only trusted workspace operators should configure custom endpoints.

## Provider authentication

| Provider | Connection | Requirements |
| --- | --- | --- |
| OpenAI | API key; official ChatGPT plan OAuth for local use | OAuth callback must use HTTP `127.0.0.1`, not `localhost` or a public host. Dynamic client registration, S256 PKCE, state, nonce, signed ID token and granted model scope are validated. Inference uses streamed public Responses with `store:false` and requires `response.completed`. |
| Google Gemini | API key; Google OAuth | Set `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_CLOUD_PROJECT`; enable Generative Language API and register the exact callback URL shown in the browser (origin + pathname, usually `/`). Grant Cloud API scope and project/billing permissions. Never expose the client secret in browser code. |
| OpenRouter | API key; public PKCE OAuth | Provider credits and account model permissions apply. OAuth keys stay in tab memory. |
| Anthropic | Claude API key | Claude.ai subscription OAuth is prohibited for this third-party application; no borrowed Claude Code client credentials are used. |
| Groq / DeepSeek | API key | Account-specific live catalog; inference quotas still apply. |
| Ollama / custom | Your OpenAI-compatible endpoint | Models endpoint and chat completions support; endpoint allowlist on hosted production. |

OpenAI and Google OAuth access tokens expire. The UI asks users to reconnect; refresh tokens are not persisted or returned to the browser. Reloading clears tab credentials, including OpenRouter keys. Removing credentials from a tab does not revoke the credential at the provider. Host/client identifiers and visual preferences are non-secret and may persist locally. OAuth consent, real accounts and project permissions require verification by the account owner; automated tests mock exchanges and cryptographically test identity validation without granting account access.

Official references: [OpenAI sign-in](https://developers.openai.com/siwc/token-sharing-open-source/sign-in), [OpenAI models and inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference), [Gemini OAuth](https://ai.google.dev/gemini-api/docs/oauth), [Anthropic authentication policy](https://code.claude.com/docs/en/legal-and-compliance#authentication-and-credential-use), [OpenRouter PKCE](https://openrouter.ai/docs/guides/overview/auth/oauth).

## Research integrity and operational limits

Independent search vectors run with bounded concurrency and round-robin allocation so the first engine cannot consume the entire source budget. Source and iteration limits end revisions explicitly. Missing sources or failed generation produce a failed investigation, not a fabricated completed paper. Automated review can be unavailable or leave unresolved findings; a completed report does not mean peer-reviewed scientific correctness. Model catalogs describe account availability, not a guarantee of remaining quota or research quality. Markdown preserves source text; PDF uses bundled Unicode fonts, but does not typeset TeX equations as a scientific publishing tool would.

Tab credentials are excluded from persisted job settings and browser storage. Graph tracing is disabled for jobs carrying tab credentials. Other LangSmith tracing is explicitly opt-in; enabling it sends research content to the configured tracing service. Protect database backups and exported reports as research data.

## Verification

Run `python -m pytest tests/unit -q` and `node --test tests/*.test.cjs`, plus `python -m compileall -q src tests`. Tests cover live-catalog protocols, secret-safe errors, OAuth signatures/nonce/audience/scope, incomplete stream rejection, workspace sessions, queue cancellation, source allocation, result persistence, Unicode PDF export, safe rendering and model-picker races. CI runs on both `main` and `master`.

Before any public multi-user launch, implement durable distributed jobs and events, per-user authentication/authorization and ownership, per-account quotas, managed secret storage, monitored backups, pinned transitive dependency resolution, load/security testing, and a hosted OAuth registration where the provider permits it. Do not increase worker count on this private-workspace architecture.
