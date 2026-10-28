# ScholarAgent — Autonomous Multi-Agent Academic Research Workbench

[![CI](https://github.com/gege010/Multi-Agent-Research-Assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/gege010/Multi-Agent-Research-Assistant/actions/workflows/ci.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-Hierarchical%205--Agent-1c3d5a.svg)](https://github.com/langchain-ai/langgraph)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **ScholarAgent** is an agentic, provider-agnostic academic research assistant. It transforms any user-defined topic or scientific inquiry into a source-grounded research draft grounded strictly in peer-reviewed literature and empirical data, backed by a 5-node autonomous multi-agent pipeline and an obsidian academic web workbench.

---

> Development status: prototype under refinement. Reports require source inspection and human review. See [engineering review and production blockers](REFINEMENT.md).

## 🌟 Key Capabilities

### 1. 🌐 Provider-Agnostic Model Engine
Users can run research using any LLM provider and any model of their choice:
- **Groq** — Ultra-high-speed inference (`openai/gpt-oss-120b`, `qwen/qwen3.8-27b`, `llama-3.3-70b-versatile`)
- **OpenAI** — `gpt-4o`, `gpt-4o-mini`, `o3-mini`, `o1`
- **Anthropic Claude** — `claude-3-7-sonnet-latest`, `claude-3-5-sonnet-latest`, `claude-3-5-haiku-latest`
- **Google Gemini** — `gemini-2.0-flash`, `gemini-1.5-pro`
- **DeepSeek** — `deepseek-chat`, `deepseek-reasoner`
- **OpenRouter** — Universal open/commercial model routing
- **Ollama** — Local air-gapped models (`llama3.2`, `mistral`, `qwen2.5`)
- **Custom OpenAI Endpoint** — Connect any internal vLLM, LMDeploy, or custom corporate gateway
- *Zero lock-in*: API keys and custom models can be set globally via `.env` or overridden directly in the UI per research request.

### 2. 🏛️ Authentic Scientific Retrieval (Zero-Key by Default)
Eliminates speculation by tapping directly into world-class scientific repositories:
- **CrossRef REST API** — Query over 150 million peer-reviewed journal papers (IEEE, Nature, Springer, Elsevier, ACM, Wiley) with persistent DOIs and verified citations (no API key required).
- **NCBI PubMed Entrez** — Direct PubMed API integration for biomedical, clinical, and life sciences studies (no API key required).
- **ArXiv API** — Preprints across computer science, machine learning, physics, and mathematics.
- **Tavily & Open Web Fallback** — Scrapes authoritative institutional whitepapers and reports.

### 3. 🛡️ The Evidence Ledger & Research Machine Engineering (Traceable Evidence)
Adheres to the *"Research Engineering: Build an AI Research Machine"* architecture:
- **Bounded Research Contract:** Turns inquiries into bounded contracts (`as_of` temporal anchor, decision context, explicit scope, and must-resolve subquestions).
- **Functional Search Lanes:** "Split the question before you split the agents" — organizes search into *Primary Evidence Lane*, *Independent Validation Lane*, and *Counter-Evidence & Limitations Lane*.
- **Untrusted Data Defense:** Sanitizes all incoming retrieved web and document text against adversarial prompt-injection directives.
- **Immutable Source Records & Exact Passages:** Assigns unique source IDs (`S-01`, `S-02`) and preserves the exact primary passage, publisher, and access date.
- **The Evidence Ledger (Center of Truth):** Extracts testable atomic claims (`C-01`, `C-02`) with explicit, rigorous statuses:
  - `supported`: Linked primary passage directly proves the claim.
  - `contested`: Credible independent sources disagree or restrict the claim (surfaced, never silently averaged).
  - `unverified`: Corpus lacks direct reproducible evidence.
  - `stale`: Temporal freshness window expired or superseded.
- **Targeted Revision Loops:** If the referee requests revisions, the system executes laser-targeted search queries specifically aimed at resolving the unverified claims or contested conflicts, rather than repeating generic searches.

### 4. ✍️ Publication-Grade Academic Monograph Output
- Synthesizes findings into formal scholarly prose strictly grounded in the Evidence Ledger:
  - Contract Metadata Header (`as_of` date, scope, and decision context)
  - Structured Abstract (Background, Objectives, Methods, Synthesis, Conclusion)
  - Theoretical Framework & Mathematical Formulations
  - Comparative Markdown Benchmark Tables
  - Contested Findings & Methodological Divergences (explains *why* studies differ)
  - Epistemic Boundaries & Open Questions (explicitly states what the evidence does not settle)
  - Dense inline citations `[N]` mapped directly to a comprehensive References bibliography with clickable DOIs and URLs.

### 5. 🎨 Bespoke Obsidian Academic Workbench
Built from the ground up according to `design-taste-frontend` and `impeccable` guidelines:
- **Dark Obsidian Aesthetics** (`#07090e`) with warm parchment accents and editorial typography (*Newsreader* + *Instrument Sans* + *JetBrains Mono*).
- **Interactive Evidence Ledger Viewer:** Filter claims by `Supported`, `Contested`, `Unverified`, and `Stale`, inspect exact passage excerpts, stances, and operational rationale.
- **Real-Time Agent Radar** via Server-Sent Events (SSE): watch Planner, Researcher, Verifier, Writer, and Reviewer stream live execution telemetry.
- **Interactive Citation Inspector**: hover over any inline `[N]` citation to preview the paper's title, authors, DOI, and relevance score without leaving your reading position.
- **Floating Document Navigator**: dynamic Table of Contents with smooth section jumping.
- **Scholarly Exports**: one-click BibTeX export, PDF generation, raw Markdown copy, and search history library.

---

## 🏛️ Autonomous 5-Agent Architecture

```
User Query & Model Settings (via Web Workbench or REST API)
                       │
                       ▼
            ┌──────────────────────┐
            │    1. PLANNER        │  Builds Bounded Contract (as_of anchor, scope)
            └──────────┬───────────┘  and functional search lanes (Primary, Indep, Counter).
                       │
                       ▼
            ┌──────────────────────┐
            │   2. RESEARCHER      │  Queries CrossRef, PubMed, ArXiv, Web concurrently.
            └──────────┬───────────┘  Assigns S-01 IDs, saves exact passages, sanitizes.
                       │
                       ▼
            ┌──────────────────────┐
            │    3. VERIFIER       │  Compiles Evidence Ledger (C-01..): assigns statuses
            └──────────┬───────────┘  (supported/contested/unverified) and surfaces conflicts.
                       │
                       ▼
            ┌──────────────────────┐
            │    4. WRITER         │  Authors structured monograph grounded in Ledger;
            └──────────┬───────────┘  highlights contested findings & open questions.
                       │
                       ▼
            ┌──────────────────────┐
            │   5. PEER REVIEWER   │  Referees along 6 dimensions (Support, Coverage,
            └──────────┬───────────┘  Freshness, Contradictions, Calibration, Rigor).
                       │              If score < 7.5: Targeted Revision Loop (only for gaps).
                       ▼ (Approved)
            Academic Monograph + Evidence Ledger + BibTeX
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+ (tested on Python 3.11)
- At least one LLM API key (e.g. Groq, OpenAI, Anthropic, Gemini, or a running local Ollama instance)

### 1. Setup Environment

```bash
# Clone the repository
git clone https://github.com/gege010/Multi-Agent-Research-Assistant.git
cd Multi-Agent-Research-Assistant

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate   # Windows
# source venv/bin/activate  # macOS / Linux

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Keys

Copy `.env.example` to `.env` and fill in whichever providers you wish to use:

```ini
# Default provider & model
DEFAULT_PROVIDER=groq
LLM_MODEL=openai/gpt-oss-120b

# Provider API Keys (fill the ones you want to use)
GROQ_API_KEY=gsk_your_groq_key_here
OPENAI_API_KEY=sk-your_openai_key_here
ANTHROPIC_API_KEY=sk-ant-your_claude_key_here
GEMINI_API_KEY=AIzaSy_your_gemini_key_here
DEEPSEEK_API_KEY=sk-your_deepseek_key_here
OPENROUTER_API_KEY=sk-or-your_openrouter_key_here
OLLAMA_BASE_URL=http://localhost:11434/v1

# Optional Web Search (CrossRef and PubMed work without any keys)
TAVILY_API_KEY=tvly-your_key_here

# Optional LangSmith Tracing
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=
```

### 3. Launch ScholarAgent

```bash
uvicorn src.main:app --reload --port 8000
```

Open your browser to:
👉 **`http://localhost:8000`** — Full Interactive Academic Workbench  
👉 **`http://localhost:8000/docs`** — OpenAPI / Swagger API documentation

---

## 🔬 API Reference

### Start an Autonomous Research Job
```bash
POST /api/v1/research
Content-Type: application/json

{
  "query": "Quantum decoherence mechanisms in superconducting transmon qubits",
  "provider": "groq",
  "model": "openai/gpt-oss-120b",
  "depth": "deep",
  "domain_focus": "physics",
  "citation_style": "ieee",
  "language": "en"
}
```

### Real-Time SSE Telemetry
```bash
GET /api/v1/research/{job_id}/stream
```
Streams `node_start`, `node_complete`, progress percentages, step logs, and the finalized monograph.

### Fetch Monograph & Bibliographic Exports
- **Get Monograph Data:** `GET /api/v1/research/{job_id}/report`
- **Download Markdown:** `GET /api/v1/research/{job_id}/download`
- **Download BibTeX:** `GET /api/v1/research/{job_id}/bibtex`
- **Download PDF:** `GET /api/v1/research/{job_id}/pdf`
- **List Providers:** `GET /api/v1/research/providers`

---

## 🧪 Testing & Validation

ScholarAgent includes a comprehensive test suite covering schemas, tools, agent nodes, and database repositories:

```bash
pytest tests/ -v
```

**Results:**
```
======================= 33 passed, 2 warnings in 17.97s =======================
```

---

## 📂 Project Structure

```
├── src/
│   ├── main.py                     # FastAPI app with static workbench mount
│   ├── config.py                   # Pydantic Settings & UTF-8 Windows safety
│   ├── api/
│   │   ├── router.py               # API route aggregator
│   │   └── v1/
│   │       ├── health.py           # System diagnostics & health check
│   │       └── research.py         # Research endpoints, SSE streaming, BibTeX
│   ├── agents/
│   │   ├── llm_factory.py          # Unified factory for 8 LLM providers
│   │   ├── state.py                # AgentState TypedDict schema
│   │   ├── planner.py              # Orthogonal scientific vector planning
│   │   ├── researcher.py           # Multi-database literature retrieval
│   │   ├── verifier.py             # Empirical fact-checker & Credibility Tiers
│   │   ├── writer.py               # Publication-grade monograph synthesis
│   │   ├── reviewer.py             # Journal referee & revision controller
│   │   ├── supervisor.py           # LangGraph StateGraph orchestration
│   │   └── tools.py                # CrossRef, PubMed, ArXiv, Web tools
│   ├── static/
│   │   ├── index.html              # Academic workbench interface
│   │   ├── app.css                 # Dark obsidian & editorial styling
│   │   └── app.js                  # Reactive SSE client & citation tooltips
│   ├── services/
│   │   ├── research_service.py     # Background task execution & SSE queue
│   │   └── report_service.py       # Monograph formatting & PDF rendering
│   ├── repositories/
│   │   └── job_repository.py       # Async SQLAlchemy job persistence
│   ├── schemas/                    # Pydantic request & response contracts
│   └── db/                         # SQLite async models and migration
├── tests/
│   └── unit/                       # 33 comprehensive unit tests
├── requirements.txt                # Production dependencies
└── README.md                       # Documentation
```

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for details.
