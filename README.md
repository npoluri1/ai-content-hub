# AI Content Hub

Multi-source content aggregation pipeline — scrapes AI/ML/tech content from **12+ sources**, classifies with LangGraph, stores in ChromaDB + SQLite, and surfaces through **dual dashboards** (Streamlit + React).

## Architecture

```
Sources Layer                        Pipeline Layer                    Storage Layer              UI Layer
─────────────────                    ─────────────                    ────────────               ───────
LinkedIn (Playwright/Proxycurl)       ─┐                               ┌─ ChromaDB (vectors)       Streamlit
Reddit (PRAW/HTTP API)               ─┤                               │                           Dashboard
TechCrunch (RSS)                     ─┤  ┌─ Orchestrator ──────────────┤                          (port 8501)
TechGig (Web Scrape)                 ─┼──┤  runs all sources           ├─ SQLite (metadata,        ────
ArXiv (API)                          ─┤  │  classifies with LangGraph  │   full-text search)       React
YouTube (Data API v3)                ─┤  │  deduplicates               │                           Frontend
Hacker News (Firebase API)           ─┤  │  generates digest           │                           (port 3000)
Medium (RSS)                         ─┤  └─────────────────────────────┘                           ────
RSS Feeds (generic)                  ─┤                                                           FastAPI
NewsAPI                              ─┤                                                           Backend
dev.to (API)                         ─┤                                                           (port 8000)
Demo (built-in sample data)          ─┘
```

## Quick Start

### 1. Install

```bash
cd pipeline
pip install -r requirements.txt
# Optional: for LinkedIn Playwright scraper
playwright install chromium
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env — set SOURCES_ENABLED=demo for testing without API keys
```

### 3. Run Pipeline

```bash
# Single run with all enabled sources
python -m pipeline run

# Single source
python -m pipeline run-source reddit

# Run on schedule (every 6h by default)
python -m pipeline serve
```

### 4. Launch Dashboards

```bash
# Streamlit dashboard (port 8501)
python -m pipeline dashboard

# FastAPI backend (port 8000)
python -m pipeline api
```

### 5. Search & Query

```bash
# CLI search
python -m pipeline search "LangGraph RAG"

# Status
python -m pipeline status

# Generate digest
python -m pipeline digest
```

## Sources

| Source | Type | API Key Required? | Free Tier? | Backend |
|--------|------|-------------------|------------|---------|
| LinkedIn | Posts | Optional | No (Proxycurl) | Playwright / Proxycurl |
| Reddit | Posts | Optional | Yes | PRAW / HTTP API |
| TechCrunch | News | No | Yes | RSS Feed |
| TechGig | News | No | Yes | Web Scrape |
| ArXiv | Papers | No | Yes | API |
| YouTube | Videos | Yes (API key) | Yes (10k req/day) | Data API v3 |
| Hacker News | Posts | No | Yes | Firebase API |
| Medium | Posts | No | Yes | RSS Feed |
| RSS (generic) | News/Posts | No | Yes | RSS/Atom parser |
| NewsAPI | News | Yes (API key) | Yes (100 req/day) | REST API |
| dev.to | Posts | No | Yes | API |
| Demo | All types | No | — | Built-in sample data |

## Demo Mode

Set `SOURCES_ENABLED=demo` in `.env` to run with built-in sample data (60+ items across all source types). No API keys needed.

## API Endpoints (port 8000)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/run` | Trigger pipeline run |
| GET | `/search?q=...` | Search stored content |
| GET | `/topics/{topic}` | Get items by topic |
| GET | `/sources/{source}` | Get items by source |
| GET | `/stats` | Storage statistics |
| GET | `/recent` | Recent items |
| POST | `/schedule` | Set scrape schedule |
| GET | `/digest` | Generate digest |

## Docker Deployment

```bash
docker compose up -d
```

Services:
- **api** — FastAPI backend (port 8000)
- **scheduler** — APScheduler (background)
- **dashboard** — Streamlit UI (port 8501)
- **chromadb** — Vector database (port 8001)
- **langfuse** — Observability (port 3000)
- **postgres** — Langfuse DB
- **n8n** — No-code workflows (port 5678)

## React Frontend

```bash
cd frontend
npm install
npm run dev    # port 3000, proxies /api to localhost:8000
```

## Adding a New Source

1. Create `pipeline/sources/newsource/` with `__init__.py` + `newsource_collector.py`
2. Extend `BaseCollector` and implement `collect()`
3. Add demo data to `sources/demo/demo_collector.py`
4. Register in `sources/__init__.py` `COLLECTOR_MAP`
5. Add config to `core/config.py`

## Project Structure

```
ai-content-hub/
├── pipeline/
│   ├── __main__.py              # CLI entry point
│   ├── core/
│   │   ├── config.py            # Pydantic settings from .env
│   │   ├── models.py            # Data models (ContentItem, ClassifiedItem, etc.)
│   │   └── base_collector.py    # Abstract base collector
│   ├── sources/                 # 12 source collectors
│   │   ├── demo/                # Built-in sample data
│   │   ├── linkedin/            # Playwright + Proxycurl
│   │   ├── reddit/              # PRAW + HTTP API
│   │   ├── techcrunch/          # RSS feed
│   │   ├── techgig/             # Web scrape
│   │   ├── arxiv/               # ArXiv API
│   │   ├── youtube/             # YouTube Data API
│   │   ├── hackernews/          # Firebase API
│   │   ├── medium/              # RSS feed
│   │   ├── rss/                 # Generic RSS/Atom
│   │   ├── newsapi/             # NewsAPI.org
│   │   └── devto/               # dev.to API
│   ├── pipeline/                # Orchestration
│   │   ├── orchestrator.py      # Main pipeline runner
│   │   ├── classifier.py        # LangGraph + keyword classification
│   │   └── scheduler.py         # APScheduler
│   ├── storage/
│   │   ├── vector_store.py      # ChromaDB wrapper
│   │   └── sql_store.py         # SQLite store
│   ├── api/
│   │   └── main.py              # FastAPI backend
│   ├── dashboard/
│   │   └── app.py               # Streamlit dashboard
│   ├── n8n/                     # n8n workflow JSON
│   ├── docker-compose.yml
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/                    # React UI (Vite + MUI)
│   ├── src/
│   ├── package.json
│   └── Dockerfile
├── AGENTIC_AI_1000_USE_CASES.md
└── README.md
```
