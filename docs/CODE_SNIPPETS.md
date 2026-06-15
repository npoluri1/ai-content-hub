# Key Code Snippets by Module

## 1. Core: Data Models (`pipeline/core/models.py`)

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class ContentItem(BaseModel):
    id: str
    title: str
    content: str
    content_cleaned: str = ""
    url: str = ""
    source: str
    source_type: str = "post"
    author_name: str = ""
    author_url: str = ""
    published_at: Optional[datetime] = None
    crawled_at: datetime = Field(default_factory=datetime.now)
    hashtags: list[str] = []
    topics: list[str] = []
    relevance_score: float = 0.0
    engagement: int = 0
    image_urls: list[str] = []
    video_url: str = ""
    metadata: dict = {}

class ClassifiedItem(ContentItem):
    is_relevant: bool = False
    classification_method: str = "keyword"
```

## 2. Configuration (`pipeline/core/config.py`)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    APP_NAME: str = "AI Content Hub"
    SOURCES_ENABLED: str = "global_rss,techcrunch,techgig,arxiv,medium,hackernews,devto,podcast,rss"
    LLM_PROVIDER: str = "none"
    CLASSIFICATION_METHOD: str = "hybrid"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3003,http://localhost:8501"
    DIGEST_TOPICS: str = "AI,AgenticAI,RAG,MCP,LLM_Ops,Coding_Assistants"
    # ... 50+ more settings
```

## 3. Vector Store (`pipeline/storage/vector_store.py`)

```python
from sentence_transformers import SentenceTransformer
import chromadb

class VectorStore:
    def __init__(self):
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
        self.client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
        self.collection = self.client.get_or_create_collection("content_items")

    def store_items(self, items: list[ClassifiedItem]):
        for item in items:
            text = f"{item.title} {item.content_cleaned or item.content[:2000]}"
            embedding = self.model.encode(text).tolist()
            self.collection.add(
                ids=[item.id],
                embeddings=[embedding],
                metadatas=[{
                    "title": item.title, "source": item.source,
                    "url": item.url, "topics": ",".join(item.topics),
                    "published_at": str(item.published_at),
                }],
            )

    def search(self, query: str, n_results: int = 20, filter_source: str = None) -> list:
        q_embedding = self.model.encode(query).tolist()
        where = {"source": filter_source} if filter_source else None
        results = self.collection.query(query_embeddings=[q_embedding],
                                        n_results=n_results, where=where)
        return [{"id": id, **meta, "content": meta.get("title", "")}
                for id, meta in zip(results["ids"][0], results["metadatas"][0])]
```

## 4. SQL Store (`pipeline/storage/sql_store.py`)

```python
import sqlite3

class SQLStore:
    def _init_db(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS items (
                    id TEXT PRIMARY KEY, title TEXT, content TEXT,
                    url TEXT, source TEXT, source_type TEXT,
                    author_name TEXT, published_at TEXT, crawled_at TEXT,
                    hashtags TEXT, topics TEXT, relevance_score REAL,
                    engagement INTEGER, is_relevant INTEGER DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS sources (
                    name TEXT PRIMARY KEY, last_crawl_at TEXT,
                    items_count INTEGER DEFAULT 0, status TEXT DEFAULT 'idle'
                );
            """)

    def store_items(self, items: list[ClassifiedItem]):
        with self._conn() as conn:
            for item in items:
                conn.execute("""
                    INSERT OR IGNORE INTO items
                    (id, title, content, url, source, source_type, author_name,
                     published_at, crawled_at, hashtags, topics, relevance_score,
                     engagement, is_relevant)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (item.id, item.title, item.content, item.url, item.source,
                      item.source_type, item.author_name,
                      item.published_at.isoformat() if item.published_at else None,
                      item.crawled_at.isoformat(),
                      ",".join(item.hashtags), ",".join(item.topics),
                      item.relevance_score, item.engagement,
                      1 if item.is_relevant else 1))
```

## 5. FastAPI Routes (`pipeline/api/main.py`)

```python
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AI Content Hub API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.API_CORS_ORIGINS.split(","),
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/stats")
def get_stats():
    vs_count = vector_store.count()
    sql_stats = sql_store.get_stats()
    return {"total_items": vs_count, "by_source": sql_stats["by_source"],
            "by_topic": sql_stats["by_topic"]}

@app.get("/search")
def search_items(q: str, limit: int = 20, source: str = None):
    results = vector_store.search(q, n_results=limit, filter_source=source)
    if not results:
        results = sql_store.search(q, limit=limit)
    return results

@app.post("/ai/rag/query")
def rag_query(req: RAGQueryRequest):
    engine = ChatEngine()
    result = engine.answer(req.question, n_context=req.n_context, model_id=req.model_id)
    return result

@app.get("/ai/models")
def list_models():
    registry = get_model_registry()
    return ModelListResponse(
        active_model=registry.get_default(), active_tier="free",
        free_models=registry.list_models(tier="free"),
        premium_models=registry.list_models(tier="premium"),
    )
```

## 6. Frontend API Client (`frontend/src/api/client.ts`)

```typescript
import axios from 'axios';
const API_BASE = 'http://localhost:8000';
const client = axios.create({ baseURL: API_BASE, timeout: 30000 });

export interface ContentItem {
  id: string; title: string; url: string; source: string;
  content: string; topics?: string; published_at: string;
  source_type?: string; image_urls?: string[];
  video_url?: string; audio_url?: string;
}

export async function searchItems(q: string, source?: string, limit = 50) {
  const { data } = await client.get('/search', { params: { q, limit, source } });
  return (data || []).map(normalizeItem);
}

export async function fetchStats() {
  const { data } = await client.get('/stats');
  return data;
}

export async function ragQuery(question: string, model_id?: string) {
  const { data } = await client.post('/ai/rag/query', { question, model_id });
  return data;
}

export async function getModels() {
  const { data } = await client.get('/ai/models');
  return data;
}
```

## 7. Frontend Model Context (`frontend/src/context/ModelContext.tsx`)

```typescript
// Manages global model selection with localStorage persistence
export function ModelProvider({ children }: { children: React.ReactNode }) {
  const [models, setModels] = useState<ModelListResponse | null>(null);
  const [activeModelId, setActiveModelId] = useState(() =>
    localStorage.getItem('activeModelId') || '');

  useEffect(() => { getModels().then(setModels); }, []);

  const switchModel = async (modelId: string) => {
    const res = await apiSwitchModel(modelId);
    if (res.success) {
      setActiveModelId(modelId);
      localStorage.setItem('activeModelId', modelId);
    }
  };

  return (
    <ModelContext.Provider value={{ models, activeModelId, switchModel }}>
      {children}
    </ModelContext.Provider>
  );
}
```

## 8. Frontend Navbar Navigation (`frontend/src/components/Navbar.tsx`)

```typescript
// 22-page navigation sidebar with expandable categories
const NAV = [
  { category: 'Core', items: [
    { label: 'Dashboard', path: '/dashboard', icon: <DashboardIcon /> },
    { label: 'Search', path: '/search', icon: <SearchIcon /> },
    { label: 'Sources', path: '/sources', icon: <RssFeedIcon /> },
    { label: 'Topics', path: '/topics', icon: <TopicIcon /> },
  ]},
  { category: 'Enterprise', items: [
    { label: 'Projects', path: '/projects', icon: <FolderIcon /> },
    { label: 'Campaigns', path: '/campaigns', icon: <RocketLaunchIcon /> },
    { label: 'Integrations', path: '/integrations', icon: <AppsIcon /> },
    { label: 'Collaboration', path: '/collaboration', icon: <GroupIcon /> },
  ]},
  // ... more categories
];
```

## 9. Orchestrator Pipeline (`pipeline/pipeline/orchestrator.py`)

```python
class ContentOrchestrator:
    def run_all(self, source_list=None) -> dict:
        collectors = get_enabled_collectors()
        results, all_items = {}, []
        for collector in collectors:
            try:
                items = collector.collect()
                for item in items:
                    ci = classify_item(item, method=settings.CLASSIFICATION_METHOD)
                    if ci.is_relevant or settings.INCLUDE_IRRELEVANT:
                        all_items.append(ci)
                results[collector.__class__.__name__] = len(items)
            except Exception as e:
                results[collector.__class__.__name__] = f"error: {e}"
        self.vector_store.store_items(all_items)
        self.sql_store.store_items(all_items)
        self._generate_digest(all_items)
        return results
```

## 10. Single Entry Point (`pipeline/__main__.py`)

```python
import typer
app = typer.Typer()

@app.command()
def run():
    """Run the full content pipeline."""
    orch = ContentOrchestrator()
    results = orch.run_all()
    print(json.dumps(results, indent=2))

@app.command()
def serve():
    """Start the FastAPI server."""
    uvicorn.run("pipeline.api.main:app", host=settings.API_HOST, port=settings.API_PORT)

@app.command()
def dashboard():
    """Start the Streamlit dashboard."""
    os.system(f"streamlit run pipeline/dashboard/app.py --server.port 8501")

@app.command()
def search(query: str):
    """Search collected content."""
    store = SQLStore()
    for item in store.search(query, limit=10):
        print(f"[{item['source']}] {item['title']}")

if __name__ == "__main__":
    app()
```

## 11. ItemCard — Content Display (`frontend/src/components/ItemCard.tsx`)

```tsx
// Key excerpts showing source badges, images, podcast player, video indicator
function ItemCard({ item, onClick }: Props) {
  const displayTopics = typeof item.topics === 'string'
    ? item.topics.split(',').filter(Boolean)
    : (item.topics || []).filter(Boolean);

  return (
    <Card onClick={() => onClick?.(item)}>
      {item.source_type === 'podcast' && (
        <Box sx={{ bgcolor: '#7C3AED', color:'#fff', px:2, py:0.5 }}>
          🎙️ Podcast Episode
        </Box>
      )}
      {item.image_urls?.length > 0 && (
        <Box sx={{ display:'flex', gap:0.5, overflow:'auto' }}>
          {item.image_urls.slice(0, 3).map(url => (
            <img src={url} alt="" style={{ height: 80, borderRadius: 4 }} />
          ))}
        </Box>
      )}
      <CardContent>
        <Typography variant="subtitle2">{item.title}</Typography>
        <Box sx={{ display:'flex', gap:0.5, flexWrap:'wrap', mt:1 }}>
          {displayTopics.map(t => <Chip key={t} label={t} size="small" />)}
          <Chip label={item.source} size="small" variant="outlined" />
        </Box>
        {item.audio_url && (
          <audio controls src={item.audio_url} style={{ width:'100%', marginTop:8 }} />
        )}
      </CardContent>
    </Card>
  );
}
```

## 12. Enterprise Search (`frontend/src/pages/EnterpriseSearch.tsx`)

```tsx
// Faceted search with source, type, topic, date range filters
function EnterpriseSearch({ onItemClick }: Props) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<ContentItem[]>([]);
  const [sources, setSources] = useState<string[]>([]);
  const [topics, setTopics] = useState<string[]>([]);
  const [filterSource, setFilterSource] = useState('');
  const [filterTopic, setFilterTopic] = useState('');

  useEffect(() => {
    fetchStats().then(s => {
      setSources(Object.keys(s.by_source).filter(Boolean).sort());
      setTopics(Object.keys(s.by_topic).filter(Boolean).sort());
    });
  }, []);

  const doSearch = async () => {
    let items = await searchItems(query, filterSource || undefined, 100);
    if (filterTopic) items = items.filter(i =>
      (i.topics || '').includes(filterTopic));
    if (sortBy === 'date') items.sort((a, b) =>
      new Date(b.published_at).getTime() - new Date(a.published_at).getTime());
    setResults(items);
  };

  return (
    <Box>
      <TextField value={query} onChange={e => setQuery(e.target.value)}
        onKeyDown={e => e.key === 'Enter' && doSearch()}
        placeholder="Search across 14+ content sources..." />

      <Select value={filterTopic} onChange={e => setFilterTopic(e.target.value)}>
        <MenuItem value="">All Topics</MenuItem>
        {topics.filter(Boolean).sort().map(t => <MenuItem value={t}>{t}</MenuItem>)}
      </Select>

      <Grid container spacing={2}>
        {results.map(item => (
          <ItemCard key={item.id} item={item} onClick={onItemClick} />
        ))}
      </Grid>
    </Box>
  );
}
```

## 13. Campaigns Launch Tracker (`frontend/src/pages/Campaigns.tsx`)

```tsx
// 8-stage launch pipeline with task checklist
const STAGES = ['ideation','planning','in_progress','review','launched','post_launch','completed','cancelled'];

function Campaigns() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [selected, setSelected] = useState<string | null>(null);

  // Pipeline overview bar
  <Card><CardContent>
    <Grid container spacing={1}>
      {STAGES.map(stage => (
        <Chip label={`${STAGE_DISPLAY[stage]}: ${count}`}
          sx={{ bgcolor: STAGE_COLORS[stage], color: '#fff' }} />
      ))}
    </Grid>
  </CardContent></Card>

  // Campaign cards with stage dropdown
  {campaigns.map(c => (
    <Card onClick={() => selectCampaign(c.id)}>
      <Chip label={STAGE_DISPLAY[c.stage]} />
      <Select value={c.stage} onChange={e => updateStage(c.id, e.target.value)}>
        {STAGES.map(s => <MenuItem value={s}>{STAGE_DISPLAY[s]}</MenuItem>)}
      </Select>
    </Card>
  ))}

  // Task checklist with progress bar
  <LinearProgress variant="determinate" value={campaignStats?.completion_pct} />
  {tasks.map(t => (
    <ListItem>
      <Checkbox checked={t.status === 'done'}
        onChange={() => toggleTask(t.id, t.status)} />
      <ListItemText primary={t.title}
        sx={{ textDecoration: t.status === 'done' ? 'line-through' : 'none' }} />
    </ListItem>
  ))}
}
```

## 14. Projects — Shared Context (`pipeline/enterprise/projects/projects.py`)

```python
class ProjectManager:
    """CRUD for projects with reports, chats, context docs, and content links."""
    def __init__(self, db_path: str = "./data/projects.db"):
        self.db_path = db_path
        self._init_db()

    def create_project(self, name: str, description: str = "", owner: str = "admin") -> dict:
        pid = str(uuid.uuid4())
        with self._get_conn() as conn:
            conn.execute("INSERT INTO projects ... VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (pid, name, description, owner, ...))
            conn.execute("INSERT INTO project_members ... VALUES (?, ?, 'admin')",
                        (pid, owner))
        return self.get_project(pid)

    def add_report(self, pid: str, title: str, content: str = "", ...) -> dict: ...
    def create_chat(self, pid: str, title: str, ...) -> dict: ...
    def add_context(self, pid: str, title: str, content: str = "", ...) -> dict: ...
    def get_project_stats(self, pid: str) -> dict: ...
```

## 15. CLI Agent (`cli/ai-content-hub`)

```python
#!/usr/bin/env python3
"""AI Content Hub CLI — Manage content, projects, campaigns from terminal."""
def cmd_stats(args):
    store = _get_sql_store(); items = store.get_all()
    by_source = {}; by_topic = {}
    for item in items:
        by_source[item.source] = by_source.get(item.source, 0) + 1
        for t in item.topics: by_topic[t] = by_topic.get(t, 0) + 1
    print(f"Total items: {len(items)}\nSources: {len(by_source)}\nTopics: {len(by_topic)}")

def cmd_mcp(args):
    """Run MCP server for AI agent integration."""
    from pipeline.mcp.server import ContentHubMCP
    store = _get_sql_store()
    mcp = ContentHubMCP(sql_store=store)
    asyncio.run(mcp.run())
```
