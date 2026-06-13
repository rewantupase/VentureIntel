# VentureIntel

> Type a company name, walk away. Come back to a structured competitive intelligence report — sourced, verified, and exported to PDF — generated entirely by a local AI with no cloud LLM required.

This is a multi-agent competitive research tool built for product and strategy teams. You give it a company name. A LangGraph pipeline fires up, pulls data from six different sources in parallel, runs four specialist AI agents, cross-checks every finding algorithmically, and assembles everything into a PDF report with an executive summary, competitor breakdowns, and a risk score matrix.

Everything runs locally via Ollama + Phi-3. No OpenAI. No Anthropic. Your data stays on your machine.

---

## What it actually does

**Evidence collection first** — before any agent writes a single sentence, the platform fans out six MCP-wrapped data tools simultaneously: Brave Search, Tavily deep search, NewsAPI, Reddit, GitHub, and Firecrawl website scraping. All six run in parallel. The raw text gets embedded with BGE-M3 and stored in ChromaDB as vector chunks.

**Three agents run in parallel** — Research (general company overview), Competitor Discovery (who are the actual rivals?), and Risk Analysis (six risk categories scored by severity). They all query ChromaDB using hybrid retrieval: dense vector search blended with BM25 keyword scoring, then fused with RRF.

**Competitor Analysis runs next** — armed with the names discovered in the previous step, this agent does a dedicated deep-dive on each rival: product differences, pricing signals, team signals, strategic positioning.

**Verification is deterministic — no LLM involved** — every factual claim gets cross-checked algorithmically using RapidFuzz fuzzy matching. A claim only passes if it appears in two or more independent sources. The confidence score formula is transparent and reproducible: `(source_count / max_sources) × avg_credibility / 10 × similarity_avg`. Nothing is trusted on the word of a single source.

**The Report Agent assembles everything** — Phi-3 writes the executive summary and key conclusions, a Jinja2 template renders the full HTML report, WeasyPrint converts it to a downloadable PDF.

You can also open the chat interface and ask follow-up questions against the collected evidence — it uses the same hybrid retrieval pipeline, streamed back token by token.

---

## Architecture

```mermaid
flowchart LR
    user[Analyst\nbrowser]

    subgraph docker[Docker Compose]
        subgraph frontend[Frontend]
            fe[React\nNginx]
        end
        subgraph backend[Backend]
            api[FastAPI\nLangGraph]
            celery[Celery\nworker]
        end
        subgraph infra[Infrastructure]
            pg[(Postgres\nsessions + reports)]
            redis[(Redis\ntask queue)]
            chroma[(ChromaDB\nvector store)]
            ollama[Ollama\nPhi-3 LLM + BGE-M3]
        end
        subgraph monitoring[Monitoring]
            prom[Prometheus]
            grafana[Grafana]
        end
    end

    mcp[MCP tools\nBrave · Tavily · Reddit\nNewsAPI · GitHub · Firecrawl]

    user -->|research request| fe
    fe -->|REST + stream| api
    api -->|enqueue job| redis
    redis -->|dequeue| celery
    api -->|read/write| pg
    celery -->|read/write| pg
    celery -->|embed + search| chroma
    celery -->|generate| ollama
    api -->|hybrid RAG| chroma
    api -->|chat generate| ollama
    celery -->|fetch evidence| mcp
    api -->|metrics| prom
    prom --> grafana
    fe -->|streamed report + chat| user
```
The system has two diagrams worth understanding. First, how the services fit together:

```
Browser (React)
    │
    ▼
FastAPI ─── enqueue ──▶ Redis ──▶ Celery worker
    │                                   │
    ├──▶ Postgres (sessions, reports)   ├──▶ Postgres
    │                                   ├──▶ ChromaDB (vectors)
    │                                   ├──▶ Ollama / Phi-3 (LLM)
    │                                   └──▶ MCP tools (6 external sources)
    │
    └──▶ Prometheus ──▶ Grafana
```

Everything is containerised — `docker compose up` starts all nine services with healthchecks and auto-dependency ordering. For local dev without Docker, the backend falls back to SQLite and embedded ChromaDB so you can run it with a single `uvicorn` command.

Second, how the LangGraph pipeline flows for each research job:

```
collect_evidence          ← MCP tools run in parallel, chunks stored in ChromaDB
        │
   ┌────┼────┐
   ▼    ▼    ▼            ← asyncio.gather fan-out
research  discovery  risk
   └────┼────┘
        │                 ← fan-in (all three must complete)
        ▼
competitor_analysis       ← uses competitor names from discovery
        │
        ▼
verification              ← deterministic, no LLM, cross-source fuzzy match
        │
        ▼
report + PDF              ← Phi-3 writes exec summary, WeasyPrint renders PDF
```

LangGraph's `MemorySaver` checkpoints the graph state after each node. If a node fails, the pipeline resumes from the last checkpoint rather than restarting from scratch.

---

## Tech stack

| | |
|---|---|
| **Frontend** | React, Create React App, Nginx |
| **Backend** | Python 3.11, FastAPI, Uvicorn |
| **Agent framework** | LangGraph `StateGraph` with `MemorySaver` checkpointing |
| **LLM** | Phi-3 via Ollama — runs entirely locally, no cloud API |
| **Embeddings** | BGE-M3 (`BAAI/bge-m3`) — also local |
| **Vector store** | ChromaDB (embedded for local dev, HTTP client for Docker) |
| **Retrieval** | Dense ANN (cosine) + BM25 keyword scoring + RRF fusion |
| **Verification** | Deterministic — RapidFuzz cross-source fuzzy matching, no LLM |
| **Task queue** | Celery + Redis |
| **Database** | PostgreSQL (sessions, agent results, reports, risk scores) |
| **Reporting** | Jinja2 HTML templates → WeasyPrint PDF |
| **Monitoring** | Prometheus + Grafana, `prometheus-fastapi-instrumentator` |
| **Structured logging** | `structlog` |

---

## Getting started

### Option A: Docker (recommended)

You need Docker Desktop and ~8 GB of disk space for the Phi-3 model.

```bash
git clone https://github.com/your-org/competitor-intel.git
cd competitor-intel

cp .env.example .env
# Fill in any API keys you want (all optional — demo data is used without them)

docker compose up --build
```

The first startup pulls the Phi-3 model automatically via `ollama pull phi3`. This takes a few minutes on first run. After that, services are available at:

| Service | URL |
|---|---|
| App | http://localhost:80 |
| API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
| Grafana | http://localhost:3001 (admin / admin) |
| Prometheus | http://localhost:9090 |

### Option B: Local dev without Docker

For faster iteration — no containers, no model download wait.

**Backend:**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# SQLite is used automatically if DATABASE_URL isn't set
# ChromaDB runs embedded (no server needed)
# Ollama still needs to be running locally for the LLM
uvicorn app.main:app --reload --port 8000
```

**Frontend:**

```bash
cd frontend
npm install
REACT_APP_API_URL=http://localhost:8000 npm start
```

---

## Running Ollama locally

Ollama serves Phi-3 on port 11434. If you're running Option B, install and start it separately:

```bash
# Install Ollama: https://ollama.com
ollama serve
ollama pull phi3
```

The backend health check at `/health` will tell you whether it can reach Ollama and which model is loaded.

---

## API keys (all optional)

Every external data source degrades gracefully to demo/placeholder data if its key is missing. You can run a fully working research pipeline with no keys at all — you just get demo chunks instead of real search results.

Add real keys to your `.env` to get live data:

| Variable | Source | What it enables |
|---|---|---|
| `BRAVE_API_KEY` | [brave.com/search/api](https://brave.com/search/api) | General web search results |
| `TAVILY_API_KEY` | [tavily.com](https://tavily.com) | Deep search + raw page content extraction |
| `FIRECRAWL_API_KEY` | [firecrawl.dev](https://firecrawl.dev) | Full website scraping |
| `NEWSAPI_KEY` | [newsapi.org](https://newsapi.org) | News articles |
| `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` | [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) | Reddit posts and community discussion |
| `GITHUB_TOKEN` | [github.com/settings/tokens](https://github.com/settings/tokens) | Public repo data, star counts |
| `LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY` | [langfuse.com](https://langfuse.com) | LLM observability (optional) |

---

## Environment variables

```bash
# ── Local LLM (required — no API key needed, runs locally)
OLLAMA_URL=http://ollama:11434
OLLAMA_MODEL=phi3

# ── PostgreSQL
DATABASE_URL=postgresql+asyncpg://intel:intel_pass@postgres:5432/intel_db

# ── Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1

# ── ChromaDB
# Docker: set CHROMA_HOST to the service name
CHROMA_HOST=chromadb
CHROMA_PORT=8000
# Local dev: leave CHROMA_HOST blank — embedded mode activates automatically

# ── Optional API keys (leave blank for demo data)
BRAVE_API_KEY=
TAVILY_API_KEY=
FIRECRAWL_API_KEY=
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
GITHUB_TOKEN=
NEWSAPI_KEY=

# ── Report output path
REPORTS_DIR=/tmp/reports
```

---

## How a research job flows

1. You POST `/api/research` with `{ "company_name": "Stripe" }`.
2. The API creates a session in Postgres and returns a `session_id` immediately with status `queued`.
3. A background task starts the LangGraph pipeline (FastAPI `BackgroundTasks` in dev, Celery worker in production).
4. You poll `/api/research/{session_id}/status` to watch agents complete in real time.
5. When status is `completed`, hit `/api/research/{session_id}/report` for the full JSON report.
6. Download the PDF at `/api/research/{session_id}/pdf`.
7. Open the chat UI and ask follow-up questions — the evidence is already indexed in ChromaDB for that session.

The LangGraph pipeline checkpoints after every node. If anything fails mid-pipeline, it resumes from the last successful checkpoint rather than starting over.

---

## How verification works

The verification step is worth understanding because it's the main thing that separates this from "just ask an LLM to make stuff up about a company."

No LLM is involved in verification. Instead:

1. Claims are extracted from all agent outputs using regex — sentences containing numbers, dates, or the company name.
2. Each claim is checked against the raw source chunks using RapidFuzz `token_set_ratio` fuzzy matching (threshold: 42).
3. A claim is only marked as `verified` if it appears in two or more independent sources.
4. The confidence score is calculated as `(source_count / max_sources) × (avg_credibility / 10) × avg_similarity`.
5. Source credibility is weighted — SEC filings = 10, official websites = 9, news = 8, Reddit = 3.

Everything is deterministic and reproducible. Running verification twice on the same data produces the same scores.

---

## Project structure

```
competitor-intel/
├── backend/
│   └── app/
│       ├── agents/
│       │   ├── orchestrator.py          # LangGraph StateGraph + AgentOrchestrator
│       │   ├── graph_state.py           # Typed PipelineState definition
│       │   ├── research_agent.py        # General company research
│       │   ├── competitor_discovery_agent.py  # Identify rivals
│       │   ├── competitor_analysis_agent.py   # Deep-dive each rival
│       │   ├── risk_analysis_agent.py   # 6-category risk scoring
│       │   ├── verification_agent.py    # Deterministic cross-source check
│       │   └── report_agent.py          # Exec summary + PDF via WeasyPrint
│       ├── services/
│       │   ├── mcp_client.py            # 6 MCP-wrapped data source tools
│       │   ├── vector_store.py          # ChromaDB + hybrid retrieval (dense + BM25 + RRF)
│       │   ├── embedding_service.py     # BGE-M3 local embeddings
│       │   ├── llm_client.py            # Ollama / Phi-3 client
│       │   └── text_utils.py            # Chunking + credibility constants
│       ├── models/
│       │   ├── schemas.py               # Pydantic request/response types
│       │   └── db_models.py             # SQLAlchemy ORM models
│       ├── main.py                      # FastAPI app + all routes
│       ├── celery_app.py                # Celery configuration
│       ├── database.py                  # SQLAlchemy async session setup
│       └── config.py                    # Settings via pydantic-settings
│
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── Dashboard.js             # Session list + new research form
│       │   ├── SessionPage.js           # Live pipeline status view
│       │   └── ReportPage.js            # Full report + risk scores + chat
│       └── utils/api.js                 # API client
│
└── infra/
    ├── docker-compose.yml               # All 9 services
    ├── init.sql                         # Postgres schema
    ├── nginx.conf                       # Reverse proxy config
    └── prometheus.yml                   # Scrape config
```

---

## Available API endpoints

| Method | Path | What it does |
|---|---|---|
| `POST` | `/api/research` | Start a new research job |
| `GET` | `/api/research/{id}/status` | Poll pipeline progress + per-agent status |
| `GET` | `/api/research/{id}/report` | Full structured report JSON |
| `GET` | `/api/research/{id}/pdf` | Download PDF report |
| `GET` | `/api/sessions` | List last 50 research sessions |
| `POST` | `/api/chat` | Ask a question against a session's evidence |
| `POST` | `/api/chat/stream` | Same, streamed token by token |
| `GET` | `/api/mcp/tools` | List registered MCP tools and their status |
| `GET` | `/api/graph/schema` | LangGraph node/edge schema for visualisation |
| `GET` | `/api/llm/status` | Ollama health + model info |
| `GET` | `/api/chroma/status` | ChromaDB collection count + mode |
| `GET` | `/health` | Overall health check |
| `GET` | `/metrics` | Prometheus metrics endpoint |

---

## GPU support

By default, Ollama runs on CPU. For GPU acceleration, uncomment the `deploy` section in `docker-compose.yml` under the `ollama` service (requires `nvidia-container-toolkit`):

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [gpu]
```

---

## Contributing

1. Fork the repo and create a feature branch
2. Run the backend locally with `uvicorn app.main:app --reload`
3. Add tests for any new agent logic or retrieval changes
4. Open a pull request with a description of what changed and why

For new data sources, implement the MCP tool contract in `mcp_client.py` — a tool is just an async function that returns `List[dict]` chunks with `content`, `source_url`, `source_type`, and `credibility_score` fields, registered via `MCPToolRegistry`.
