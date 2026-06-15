# AI Content Hub — Architecture

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SOURCES LAYER                                 │
│  14 collectors, each extends BaseCollector                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  linkedin  reddit  techcrunch  techgig  arxiv  youtube  hackernews          │
│     │        │         │          │       │       │          │              │
│  medium    rss    newsapi    devto   global_rss   podcast    demo           │
│     │      │        │         │          │          │         │             │
└─────┴──────┴────────┴─────────┴──────────┴──────────┴─────────┴─────────────┘
       │
       │  collect() returns list[ContentItem]
       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PIPELINE LAYER                                     │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  ContentOrchestrator.run_all()                                        │  │
│  │                                                                       │  │
│  │  1. get_enabled_collectors() → run each collector.collect()           │  │
│  │  2. classify_item() on each item (keyword + optional LLM)             │  │
│  │  3. store in ChromaDB (vectors) + SQLite (metadata)                   │  │
│  │  4. _generate_digest() → topic-grouped Markdown digest                │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  Classifier (30 topics)                                               │  │
│  │   method: keyword | llm | hybrid                                      │  │
│  │   keyword: TOPIC_KEYWORDS dict → match → score → rank                 │  │
│  │   llm: OpenAI/Anthropic → prompt → parse → validate                   │  │
│  │   hybrid: merge keyword_scores + llm_topics → sort → top 3            │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  Scheduler (APScheduler)                                              │  │
│  │   runs pipeline every 6 hours (configurable)                          │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           STORAGE LAYER                                    │
│                                                                             │
│  ┌─────────────────────┐    ┌─────────────────────────────────────────┐    │
│  │  ChromaDB            │    │  SQLite                                  │    │
│  │  Vector Store        │    │  Item metadata, full-text, stats,       │    │
│  │  Embeddings:         │    │  schedules, workspaces, campaigns,      │    │
│  │  sentence-transformers│   │  alerts, competitors, workflows, auth   │    │
│  │  all-MiniLM-L6-v2    │    │                                         │    │
│  │  cosine similarity   │    │  Tables: items, sources, workspaces,    │    │
│  │  dedup via threshold │    │  projects, campaigns, alerts, auth      │    │
│  └─────────────────────┘    └──────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             API LAYER                                      │
│                                                                             │
│  FastAPI (port 8000) — 130+ endpoints                                      │
│                                                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│  │ Content  │ │ AI/ML    │ │ Enterprise│ │ Analytics│ │ Workflow │         │
│  │ /search  │ │ /ai/*    │ │ /collab/* │ │ /trends  │ │ /workflow│         │
│  │ /recent  │ │ /mlops/* │ │ /comply/* │ │ /export  │ │ /mcp     │         │
│  │ /stats   │ │ /rag     │ │ /monitor  │ │           │ │          │         │
│  │ /digest  │ │          │ │ /projects │ │           │ │          │         │
│  │ /sources │ │          │ │ /campaigns│ │           │ │          │         │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘         │
│                                                                             │
│  Middleware:  CORS, JWT auth, rate limiting                                 │
└─────────────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              UI LAYER                                      │
│                                                                             │
│  ┌──────────────────────────────┐    ┌──────────────────────────────────┐  │
│  │  React + Vite (port 3003)    │    │  Streamlit (port 8501)           │  │
│  │                              │    │  Real-time monitoring dashboard  │  │
│  │  22 pages (Routes):          │    │  Pipeline status, source health  │  │
│  │  Dashboard, Search, Sources,  │    │  Topic trends, word clouds       │  │
│  │  Topics, Digest, Schedule,   │    │  Configuration management        │  │
│  │  Settings, Analytics, Trends, │    │  Manual pipeline triggers        │  │
│  │  RagChat, AiLab,             │    │  Digest preview                  │  │
│  │  EnterpriseSearch, MlopsLab, │    │                                   │  │
│  │  Integrations, Compliance,   │    │                                   │  │
│  │  Collaboration, Projects,    │    │                                   │  │
│  │  Campaigns, Monitoring,      │    │                                   │  │
│  │  Workflows, Notifications,   │    │                                   │  │
│  │  Processing, Forum           │    │                                   │  │
│  └──────────────────────────────┘    └──────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Map

| Layer | Component | Tech | Purpose |
|-------|-----------|------|---------|
| **Sources** | 14 collectors | Python, httpx, feedparser, playwright | Scrape content from web sources |
| **Pipeline** | Orchestrator | Python | Coordinate collection → classification → storage |
| **Pipeline** | Classifier | Python, regex, optional LLM | 30-topic keyword + LLM classification |
| **Pipeline** | Scheduler | APScheduler | Periodic pipeline execution |
| **Storage** | Vector Store | ChromaDB, sentence-transformers | Embedding storage & semantic search |
| **Storage** | SQL Store | SQLite (WAL mode) | Metadata, full-text search, stats |
| **AI** | Model Registry | Singleton, 150+ models | Runtime-switchable LLM selection |
| **AI** | LLM Service | LiteLLM, direct API | Unified provider access with fallback |
| **AI** | RAG Chat Engine | Vector search + LLM | Context-augmented Q&A |
| **AI** | Recommender | ChromaDB similarity | Content recommendations |
| **API** | FastAPI | Python, uvicorn | REST API gateway |
| **UI** | React SPA | Vite, MUI, Recharts | Enterprise web dashboard |
| **UI** | Streamlit | Python, plotly | Real-time monitoring & config |
| **Auth** | JWT | Python, PyJWT | User authentication |
| **Workflow** | DAG Engine | Python | Custom workflow builder/executor |
| **MCP** | MCP Server | Python, mcp SDK | Model Context Protocol server |

## Data Flow (end-to-end pipeline run)

```
1. CLI trigger → python -m pipeline run (or /run API)
2. ContentOrchestrator.run_all()
3.   → get_enabled_collectors() from COLLECTOR_MAP
4.   → for each collector: collector.collect() → list[ContentItem]
5.   → for each item: classify_item()
6.       → keyword matching against 30 TOPIC_KEYWORDS
7.       → if LLM enabled: _classify_with_llm() for enrichment
8.       → merge → top 3 topics → ClassifiedItem
9.   → VectorStore.store_items() → ChromaDB (embeddings)
10.  → SQLStore.store_items() → SQLite (metadata)
11.  → _generate_digest() → Markdown to data/digests/
12.  → update crawl timestamps in sources table
```

## Data Model

```
ContentItem (Pydantic)
├── id: str (MD5 hash of URL)
├── title, content, content_cleaned
├── url, source, source_type
├── author_name, author_url
├── published_at, crawled_at
├── hashtags: list[str]
├── topics: list[str] (up to 3)
├── relevance_score: float
├── engagement: int
├── image_urls: list[str]
├── video_url: str
├── metadata: dict
│
└── ClassifiedItem extends ContentItem
    ├── is_relevant: bool
    └── classification_method: str
```
