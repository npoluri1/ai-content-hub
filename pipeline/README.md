# LinkedIn AI Tech Stack Pipeline

An **intelligent LinkedIn content aggregation pipeline** that scrapes posts about AI/ML engineering topics, classifies them with LangGraph, stores in ChromaDB, and generates daily digests for Slack/Discord.

## Architecture

```
LinkedIn (Apify / PhantomBuster / Playwright / Web)
        │
        ▼
  ┌─────────────────────┐
  │   Collectors        │  ← 5 backends: demo, apify, phantombuster, playwright, web
  └────────┬────────────┘
           │
           ▼
  ┌─────────────────────┐
  │   Classifier         │  ← LangGraph agent with keyword + LLM classification
  │   (LangGraph)        │     8 topic categories: AI, AgenticAI, AI_Frameworks,
  └────────┬────────────┘     Quantum_Computing, Robotics, RAG, MCP, LLM_Ops
           │
           ▼
  ┌─────────────────────┐
  │   Vector Store       │  ← ChromaDB with dedup, MD5 hashing, hybrid search
  │   (ChromaDB)         │
  └────────┬────────────┘
           │
           ▼
  ┌─────────────────────┐
  │   Digest Generator   │  ← Markdown / HTML / Slack / Discord
  └────────┬────────────┘
           │
           ▼
    Slack / Discord / Notion / File
```

## Quick Start

```bash
# 1. Clone and install
cd pipeline
pip install -r requirements.txt
playwright install chromium

# 2. Configure
cp .env.example .env
# Edit .env — set SCRAPER_BACKEND=demo for testing

# 3. Run a single pipeline
python -m pipeline run
# Or specify topics:
python -m pipeline run --topics "AI,AgenticAI,MCP"

# 4. Run on schedule
python -m pipeline serve

# 5. Search stored posts
python -m pipeline search "LangGraph checkpointing"
```

## Collector Backends

| Backend       | Requires              | Use Case                    |
|---------------|-----------------------|-----------------------------|
| `demo`        | Nothing               | Testing, development        |
| `apify`       | APIFY_API_TOKEN       | Production, reliable        |
| `phantombuster` | PHANTOMBUSTER_API_KEY | Production, headless        |
| `playwright`  | LinkedIn credentials  | Self-hosted, high volume    |
| `web`         | Nothing               | Basic scraping              |

## Docker Deployment

```bash
docker compose up -d
```

Starts:
- **Pipeline** — collector + classifier + storage + digest
- **ChromaDB** — vector database on port 8001
- **Langfuse** — observability UI on port 3000
- **Postgres** — database for Langfuse
- **n8n** — no-code workflow editor on port 5678

## n8n Alternative

Import `n8n/linkedin_pipeline.json` into n8n (port 5678 after `docker compose up`).

Workflow: Schedule → HTTP Request → Clean → OpenAI Classify → ChromaDB → Merge → Digest → Slack/Discord/Notion

## Outputs

- `output/digest_YYYYMMDD_HHMMSS.md` — Markdown digest on the filesystem
- Slack/Discord webhook notifications (if configured)
- ChromaDB stores everything for search and RAG later
- Langfuse traces every pipeline run (if configured)

## File Structure

```
pipeline/
├── __main__.py              # CLI entry point (typer)
├── pipeline.py              # Main orchestrator
├── config.py                # Pydantic settings
├── models.py                # Pydantic schemas
├── docker-compose.yml       # Full stack deployment
├── Dockerfile               # Container build
├── requirements.txt         # Python dependencies
├── .env.example             # Environment template
├── README.md                # This file
├── collectors/
│   ├── __init__.py
│   ├── base.py              # Abstract collector
│   ├── demo_collector.py    # Sample data
│   ├── apify_collector.py   # Apify integration
│   ├── phantombuster_collector.py  # PhantomBuster
│   ├── playwright_collector.py     # Playwright
│   └── web_collector.py     # Requests + BeautifulSoup
├── classifiers/
│   ├── __init__.py
│   └── topic_classifier.py  # LangGraph agent
├── storage/
│   ├── __init__.py
│   └── vector_store.py      # ChromaDB wrapper
├── digest/
│   ├── __init__.py
│   └── generator.py         # Digest builder
└── n8n/
    └── linkedin_pipeline.json    # n8n workflow
```
