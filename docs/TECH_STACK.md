# Technology Stack

## Backend Stack

| Category | Technology | Purpose | Key Features |
|----------|-----------|---------|--------------|
| **Runtime** | Python 3.10+ | Primary backend language | Async/await, type hints, dataclasses |
| **API Framework** | FastAPI | REST API | Auto OpenAPI docs, Pydantic validation, async support |
| **Server** | Uvicorn | ASGI server | High performance, hot reload |
| **Config** | Pydantic Settings | Environment-based config | `.env` file, type-safe, hierarchical |
| **Vector DB** | ChromaDB | Vector embeddings | Cosine similarity, metadata filtering, persistent storage |
| **Relational DB** | SQLite | Metadata & full-text | WAL mode, zero-config, embedded |
| **Embeddings** | sentence-transformers (`all-MiniLM-L6-v2`) | Text to vectors | 384-dim, fast inference, ONNX support |

### AI & ML Stack

| Category | Technology | Purpose |
|----------|-----------|---------|
| **LLM Gateway** | LiteLLM | Unified API for 150+ models across 30+ providers |
| **Model Registry** | Custom singleton | Runtime-switchable model selection, free/premium tiers |
| **LLM Providers** | OpenAI, Anthropic, Google, Groq, Together, Ollama, vLLM, etc. | Inference backends |
| **RAG Engine** | Custom (ChromaDB + LLM) | Context retrieval → prompt assembly → answer generation |
| **Classification** | Keyword (30 topics) + optional LLM | Hybrid approach for maximum coverage |
| **Sentiment** | Custom keyword + ML | Content sentiment analysis |
| **Quality Scoring** | Custom algorithm | Content quality assessment |
| **NER/Enrichment** | Custom pipeline | Named entity extraction, content enrichment |

### Enterprise Stack

| Category | Technology | Purpose |
|----------|-----------|---------|
| **Auth** | JWT (PyJWT) | Stateless authentication |
| **Workflow** | Custom DAG engine | Visual workflow builder with parallel execution |
| **Monitoring** | Custom alert engine | Keyword/topic alerts, anomaly detection, competitor tracking |
| **Compliance** | Custom modules | PII detection, moderation, audit log, retention, GDPR toolkit |
| **Collaboration** | Custom SQLite-backed | Workspaces, comments, approvals, share links, activity feed |
| **Notifications** | SMTP, Telegram Bot, Webhooks | Multi-channel delivery |
| **MCP** | MCP Python SDK | Model Context Protocol server |

### Task Scheduling & Background Jobs

| Category | Technology | Purpose |
|----------|-----------|---------|
| **Scheduler** | APScheduler | Periodic pipeline execution |
| **Async Tasks** | Threading | Background job execution |

## Frontend Stack

| Category | Technology | Purpose |
|----------|-----------|---------|
| **Framework** | React 18 + TypeScript | SPA frontend |
| **Build Tool** | Vite | Fast dev server, optimized builds |
| **UI Library** | MUI (Material-UI) v6 | Component library, theming |
| **Charts** | Recharts | Topic distribution, source breakdown |
| **Routing** | React Router v6 | Client-side routing |
| **HTTP Client** | Axios | API communication |
| **State** | React Context | Model selection, theme |

## Developer Tools

| Tool | Purpose |
|------|---------|
| **Python** `requirements.txt` | Dependency management |
| **npm** `package.json` | Frontend dependency management |
| **TypeScript** | Type-safe frontend development |
| **ESLint** | Code quality |

## Infrastructure (Optional)

| Platform | Config File | Purpose |
|----------|------------|---------|
| Docker | `docker-compose.yml` | Containerized deployment |
| Fly.io | `fly.toml` | Cloud deployment |
| Render | `render.yaml` | Cloud deployment |
| Railway | `railway.json` | Cloud deployment |
| Vercel | `vercel.json` | Frontend deployment |

## Key Technology Points

### 1. Dual Storage Architecture
Items are stored in **both** ChromaDB (vector embeddings for semantic search) and SQLite (metadata for full-text search, stats, schedules). This gives:
- Semantic similarity search via vector cosine distance
- Exact match full-text search via SQL LIKE
- Aggregated statistics via SQL GROUP BY
- No single point of failure — each store is independent

### 2. 30-Topic Classifier
The classifier supports 30 technology topics across the full AI/ML/dev landscape:
- **Core AI**: AI, AgenticAI, AI_Frameworks, LangChain, LangGraph
- **Languages**: Python, ReactJS, Transformers
- **Techniques**: Prompting, RAG, MCP, Embeddings, Vector_Databases
- **Domains**: Computer_Vision, NLP, Robotics, Quantum_Computing
- **Ops**: LLM_Ops, MLOps, DevOps_Cloud, Database, Security, Data_Science
- **Infrastructure**: Edge_AI, IoT, Semiconductors, API_Development
- **Ecosystem**: AI_Cloud_Infra, Coding_Assistants, Workflow_Automation

### 3. 150+ Model Registry
The model registry pre-defines models from 30+ providers with tiered access (free vs premium), context windows, capabilities (streaming, vision, tools, images, audio), and per-call pricing. Runtime switching via the ModelContext React context with localStorage persistence.

### 4. RAG with Source Attribution
The ChatEngine retrieves relevant context from ChromaDB vector search, assembles it into a prompt with source citations, and generates answers via the selected LLM model. Responses include source references for verification.

### 5. Enterprise Modularity
All enterprise features (compliance, collaboration, monitoring, projects, campaigns, workflows) are standalone modules with their own SQLite tables, independent of the core pipeline. They can be enabled/disabled via configuration.
