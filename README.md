# Multi-Agent Research Assistant

[![CI](https://github.com/gege010/Multi-Agent-Research-Assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/gege010/Multi-Agent-Research-Assistant/actions/workflows/ci.yml)

> Hierarchical LangGraph agent for autonomous research with LangSmith tracing. Supports Tavily web search, ArXiv academic search, and PDF report generation.

## Demo
![Demo GIF](docs/demo.gif)

**Live Demo:** [Live on Streamlit Cloud](#) *(Placeholder - will be updated after deployment)*

## Evaluation Metrics

Measured from 10 diverse test queries running on Groq (Llama-3.3-70B):

| Metric | Result |
|---|---|
| Task completion rate | 10 / 10 |
| Avg. tool calls per query | 4.2 calls |
| Avg. end-to-end latency | ~32 seconds |
| Avg. report length | ~650 words |
| Self-correction triggered | 2 / 10 |

## Sample Report Output

**Query:** *"Impact of transformer architecture on modern NLP"*

> The Transformer architecture, introduced by Vaswani et al. in 2017, has fundamentally revolutionized Natural Language Processing (NLP). By dispensing with recurrence and convolutions in favor of self-attention mechanisms, Transformers allow for highly parallelizable training and the ability to capture long-range dependencies in text. This has led to the development of powerful Large Language Models (LLMs)...

[Full Report (Markdown)](data/reports/examples/5f9c28e0_Impact%20of%20transformer%20architecture%20on%20modern%20NLP.md)

## Observability (LangSmith)

Every node and tool call is traced automatically to ensure full visibility into the agent's reasoning and tool selection process.

![LangSmith trace 1](docs/traces/trace_example_1.png)
![LangSmith trace 2](docs/traces/trace_example_2.png)

## Features

- **Hierarchical Supervisor Agent** — LangGraph-powered multi-agent orchestration
  - Planner → Researcher (with Dynamic Tool Router) → Writer → Reviewer
  - Self-correcting loop (up to 3 revisions)
- **Multi-source search & execution** — Tavily (web), ArXiv (academic), Unstructured (document reading), and Python REPL (code execution)
- **PDF generation** — fpdf2 (with Unicode sanitization)
- **Full observability** — LangSmith traces every tool call
- **Production-grade API** — FastAPI with SSE streaming
- **Docker-ready** — Single container, `docker compose up`

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env with your API keys

# 2. Start services
docker compose up --build

# 3. Open in browser
#   API:  http://localhost:8000/docs
#   UI:   http://localhost:8501
```

## Manual Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set API keys
export GROQ_API_KEY=gsr_xxxxx
export TAVILY_API_KEY=tvly_xxxxx
export LANGSMITH_API_KEY=lsv2_xxxxx

# Run API
uvicorn src.main:app --reload --port 8000

# Run UI (separate terminal)
streamlit run frontend/app.py --port 8501
```

## API Example

```bash
# Start research
curl -X POST http://localhost:8000/api/v1/research \
  -H "Content-Type: application/json" \
  -d '{"query": "Impact of LLMs on software engineering", "depth": "standard"}'

# Check status
curl http://localhost:8000/api/v1/research/{job_id}

# Get report
curl http://localhost:8000/api/v1/research/{job_id}/report
```

## Architecture

```
Streamlit UI ──► FastAPI ──► LangGraph Supervisor
                               │
                    ┌──────────┼──────────┐
                    ▼          ▼          ▼
               Planner   Researcher   Writer
                           │                     │
                    ┌──────┴──────┐         Reviewer
                    ▼             ▼             ▲
               Tavily        ArXiv              │
                    └─────────────┘        (loop back if needed)
                              │
                         LangSmith
                    (every tool call traced)
```

## Project Structure

```
src/
├── main.py                    # FastAPI entry point
├── config.py                  # Environment settings
├── api/
│   ├── router.py              # Route aggregation
│   ├── deps.py                 # Dependencies
│   └── v1/
│       ├── health.py           # /health, /models
│       └── research.py         # /research endpoints
├── agents/
│   ├── state.py               # AgentState TypedDict
│   ├── planner.py             # Break query into tasks
│   ├── researcher.py           # Execute searches
│   ├── writer.py              # Generate markdown
│   ├── reviewer.py            # Quality check
│   ├── supervisor.py          # LangGraph graph
│   └── tools.py               # tavily, arxiv, web_fetch
├── services/
│   ├── research_service.py    # Orchestration
│   └── report_service.py      # Markdown → PDF
├── repositories/
│   └── job_repository.py      # Job CRUD
├── schemas/                   # Pydantic schemas
├── db/                        # SQLAlchemy models
└── exceptions/                # Custom exception hierarchy
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Agent | LangGraph (hierarchical supervisor) |
| LLM | Groq (Llama-3.3 70B) |
| Tools | Tavily, ArXiv, Unstructured.io, Langchain Python REPL |
| Observability | LangSmith |
| Web | FastAPI + Uvicorn |
| UI | Streamlit |
| PDF | fpdf2 |
| DB | SQLite (SQLAlchemy) |
| Container | Docker |

## Environment Variables

See `.env.example` for all variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | ✅ | — | Groq API key |
| `LLM_MODEL` | ❌ | `llama-3.3-70b-versatile` | Groq model |
| `TAVILY_API_KEY` | ✅ | — | Tavily Search API key |
| `LANGSMITH_API_KEY` | ✅ | — | LangSmith API key (required for tracing) |
| `LANGSMITH_PROJECT` | ❌ | `research-assistant` | LangSmith project name |
| `APP_ENV` | ❌ | `development` | `development` or `production` |
| `DATABASE_URL` | ❌ | SQLite | Database connection string |

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## Known Limitations

- **Latency:** End-to-end research can take 20–45 seconds depending on query complexity and Tavily/Groq API speeds.
- **Context window:** For topics requiring many sources, the aggregated context could exceed the limits of smaller LLMs.
- **Hallucination:** The Reviewer node reduces but does not eliminate hallucination — always verify important claims against original sources.
- **Rate limits:** External free-tier APIs (Groq, Tavily) possess rate limits that may cause errors on rapid sequential queries.
