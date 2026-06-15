# AI & Agentic Code Deep Dive

This document walks through every AI/agentic code path in the application, from content collection through AI-powered RAG chat.

---

## 1. Content Collection Pipeline

### Collector Abstraction

Every source collector extends `BaseCollector` which provides standard item construction:

```python
# pipeline/core/base_collector.py
from abc import ABC, abstractmethod
from ..core.models import ContentItem

class BaseCollector(ABC):
    @abstractmethod
    def collect(self) -> list[ContentItem]:
        """Fetch items from source — each collector implements this."""

    def make_id(self, url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()

    def make_item(self, source: str, title: str, content: str, url: str,
                  **kwargs) -> ContentItem:
        return ContentItem(
            id=self.make_id(url),
            title=title, content=content, url=url, source=source,
            published_at=kwargs.get('published_at'),
            hashtags=kwargs.get('hashtags', []),
            source_type=kwargs.get('source_type', 'post'),
            image_urls=kwargs.get('image_urls', []),
            video_url=kwargs.get('video_url', ''),
        )
```

### Example: Hacker News Collector

```python
# pipeline/sources/hackernews/hn_collector.py
class HackerNewsCollector(BaseCollector):
    def collect(self) -> list[ContentItem]:
        resp = httpx.get("https://hacker-news.firebaseio.com/v0/topstories.json")
        story_ids = resp.json()[:30]
        items = []
        for sid in story_ids:
            s = httpx.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json").json()
            items.append(self.make_item(
                source="hackernews",
                title=s.get("title", ""),
                content=s.get("text", s.get("title", "")),
                url=s.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                published_at=datetime.fromtimestamp(s.get("time", 0)),
                source_type="news",
            ))
        return items
```

### Collector Registry

```python
# pipeline/sources/__init__.py
COLLECTOR_MAP: dict[str, type[BaseCollector]] = {
    "hackernews": HackerNewsCollector,
    "reddit": RedditCollector,
    "arxiv": ArXivCollector,
    "techcrunch": TechCrunchCollector,
    "medium": MediumCollector,
    "devto": DevToCollector,
    "rss": RSSCollector,
    "global_rss": GlobalRSSCollector,
    "podcast": PodcastCollector,
    # ... more
}

def get_enabled_collectors() -> list[BaseCollector]:
    enabled = settings.SOURCES_ENABLED.split(",")
    return [COLLECTOR_MAP[name.strip()]() for name in enabled if name.strip() in COLLECTOR_MAP]
```

---

## 2. 30-Topic Classifier

### Keyword Classification (Always Active)

```python
# pipeline/pipeline/classifier.py

TOPIC_KEYWORDS: dict[str, list[str]] = {
    "AI": ["artificial intelligence", "machine learning", "neural network", "gpt", "llm", "foundation model", "generative ai", "genai", "multimodal"],
    "AgenticAI": ["agent", "multi-agent", "agentic", "function calling", "tool use", "agent orchestration", "react agent", "claude code", "cursor", "windsurf", "aider", "agent mode", "agentic coding"],
    "MCP": ["mcp", "model context protocol", "mcp server", "mcp client", "mcp tool", "context protocol"],
    "RAG": ["rag", "retrieval augmented", "vector database", "chromadb", "qdrant", "pinecone", "embedding", "retrieval", "reranker", "graphrag"],
    "Prompting": ["chain-of-thought", "cot", "tree-of-thoughts", "tot", "react", "reflexion", "dspy", "structured output", "constrained decoding"],
    "Vector_Databases": ["pinecone", "weaviate", "qdrant", "milvus", "chroma", "pgvector", "hnsw", "ann", "vector search"],
    "Coding_Assistants": ["claude code", "cursor", "copilot", "github copilot", "windsurf", "continue", "aider", "codex cli", "ai coding assistant"],
    "Semiconductors": ["risc-v", "arm", "nvidia cuda", "amd rocm", "google tpu", "cerebras", "chip design", "asic", "fpga"],
    # ... 22 more topics
}

def classify_item(item: ContentItem, method: str = "hybrid") -> ClassifiedItem:
    text = (item.content + " " + item.title + " " + " ".join(item.hashtags)).lower()

    # Step 1: Keyword matching
    keyword_topics: set[str] = set()
    keyword_scores: dict[str, float] = {}
    for topic, keywords in TOPIC_KEYWORDS.items():
        score = sum(text.count(kw) * (1.0 if len(kw) > 5 else 0.5) for kw in keywords)
        if score > 0:
            keyword_topics.add(topic)
            keyword_scores[topic] = score

    # Step 2: Optional LLM enrichment
    llm_topics: list[str] = []
    if method in ("llm", "hybrid") and settings.LLM_PROVIDER != "none":
        llm_topics = _classify_with_llm(item, text)

    # Step 3: Merge — keyword wins if no LLM, otherwise union sorted by score
    final_topics = sorted(keyword_topics | set(llm_topics),
                         key=lambda t: keyword_scores.get(t, 0) + (2 if t in llm_topics else 0),
                         reverse=True)

    return ClassifiedItem(
        **item.model_dump(exclude={"topics", "relevance_score"}),
        topics=final_topics[:3],
        relevance_score=keyword_scores.get(final_topics[0], 0.5) if final_topics else 0.0,
        is_relevant=len(final_topics) > 0,
    )
```

### LLM Classification (Optional, API Key Required)

```python
def _classify_with_llm(item: ContentItem, text: str) -> list[str]:
    provider = settings.LLM_PROVIDER
    valid_topics = "AI, AgenticAI, AI_Frameworks, Prompting, RAG, MCP, ... (30 topics)"

    prompt = f"""Classify this content into relevant topics from: {valid_topics}
Title: {item.title[:200]}
Content: {text[:1500]}
Return ONLY a comma-separated list of relevant topics:"""

    if provider == "openai":
        from openai import OpenAI
        resp = OpenAI(api_key=settings.OPENAI_API_KEY).chat.completions.create(
            model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}],
            temperature=0.1, max_tokens=50)
        result = resp.choices[0].message.content or ""
    elif provider == "anthropic":
        # Anthropic Claude API call
        ...
    else:
        return []

    topics = [t.strip().replace(" ", "_") for t in result.split(",") if t.strip()]
    valid_set = {"AI", "AgenticAI", ...}  # 30 valid topics
    return [t for t in topics if t in valid_set]
```

---

## 3. Orchestrator — The Pipeline Engine

```python
# pipeline/pipeline/orchestrator.py
class ContentOrchestrator:
    def run_all(self, source_list: list[str] | None = None) -> dict:
        collectors = get_enabled_collectors()
        if source_list:
            collectors = [c for c in collectors if c.__class__.__name__ in source_list]

        all_items: list[ClassifiedItem] = []
        for collector in collectors:
            raw_items = collector.collect()
            for item in raw_items:
                classified = classify_item(item, method=settings.CLASSIFICATION_METHOD)
                if classified.is_relevant or settings.INCLUDE_IRRELEVANT:
                    all_items.append(classified)

        # Store in both databases
        self.vector_store.store_items(all_items)
        self.sql_store.store_items(all_items)

        # Generate digest
        digest = self._generate_digest(all_items)
        return {"status": "success", "results": {"_total": len(all_items), ...}}

    def _generate_digest(self, items: list[ClassifiedItem]) -> str:
        lines = [f"# AI Content Hub Digest", f"**Items:** {len(items)}", ""]
        for topic in settings.DIGEST_TOPICS.split(","):
            topic_items = [i for i in items if topic in i.topics][:10]
            if topic_items:
                lines.append(f"## {topic}")
                for item in topic_items:
                    lines.append(f"- [{item.title}]({item.url})")
        return "\n".join(lines)
```

---

## 4. Model Registry — 150+ LLM Models

```python
# pipeline/ai/model_registry.py
class ModelConfig:
    id: str; name: str; provider: str; tier: str  # 'free' | 'premium'
    description: str; context_window: int
    supports_streaming: bool; supports_vision: bool; supports_tools: bool
    supports_image: bool; supports_file: bool; supports_audio: bool; supports_video: bool
    cost_per_1k_input: float; cost_per_1k_output: float

class ModelRegistry:
    def __init__(self):
        self._models: list[ModelConfig] = []
        self._load_defaults()

    def _load_defaults(self):
        # 150+ models across 30+ providers
        self._models = [
            # OpenAI
            ModelConfig(id="gpt-4o", name="GPT-4o", provider="openai", tier="premium",
                       context_window=128000, supports_streaming=True, supports_vision=True,
                       cost_per_1k_input=2.5, cost_per_1k_output=10.0),
            ModelConfig(id="gpt-4o-mini", name="GPT-4o Mini", provider="openai", tier="free",
                       context_window=128000, supports_streaming=True, supports_vision=True,
                       cost_per_1k_input=0.15, cost_per_1k_output=0.6),
            ModelConfig(id="o1", name="o1", provider="openai", tier="premium",
                       context_window=200000, supports_streaming=False, supports_vision=True,
                       cost_per_1k_input=15.0, cost_per_1k_output=60.0),
            ModelConfig(id="o3-mini", name="o3-mini", provider="openai", tier="free",
                       context_window=200000, supports_streaming=True,
                       cost_per_1k_input=1.1, cost_per_1k_output=4.4),
            # Anthropic
            ModelConfig(id="claude-sonnet-4-20250514", name="Claude Sonnet 4", provider="anthropic",
                       tier="premium", context_window=200000, supports_streaming=True,
                       supports_vision=True, supports_tools=True,
                       cost_per_1k_input=3.0, cost_per_1k_output=15.0),
            # Google
            ModelConfig(id="gemini-2.5-pro-exp-03-25", name="Gemini 2.5 Pro", provider="google",
                       tier="premium", context_window=1000000, supports_streaming=True,
                       supports_vision=True,
                       cost_per_1k_input=1.25, cost_per_1k_output=10.0),
            # Groq, Together, Ollama, vLLM, etc...
            ...
        ]

    def list_models(self, tier: str | None = None) -> list[ModelConfig]:
        if tier:
            return [m for m in self._models if m.tier == tier]
        return self._models.copy()

# Singleton accessor
_registry: ModelRegistry | None = None
def get_model_registry() -> ModelRegistry:
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry
```

---

## 5. RAG Chat Engine — Complete AI Flow

```python
# pipeline/ai/rag_chat.py
class ChatEngine:
    def __init__(self):
        self.vector_store = VectorStore()
        self.llm = LLMService()

    def answer(self, question: str, n_context: int = 5,
               model_id: str | None = None) -> dict:
        # Step 1: Retrieve relevant context from vector store
        context_docs = self.vector_store.search(question, n_results=n_context)

        # Step 2: Assemble prompt with source citations
        context_text = "\n\n".join(
            f"[Source {i+1}] {doc['content'][:2000]}"
            for i, doc in enumerate(context_docs)
        )

        prompt = f"""Answer based ONLY on the provided context.
If the context lacks sufficient information, say so.

Context:
{context_text}

Question: {question}

Answer:"""

        # Step 3: Generate answer via selected LLM
        result = self.llm.generate(prompt, model_id=model_id)

        # Step 4: Return answer with source references
        return {
            "answer": result,
            "sources": [
                {"title": doc.get("title", ""),
                 "url": doc.get("url", ""),
                 "source": doc.get("source", "")}
                for doc in context_docs[:n_context]
            ],
            "n_sources": len(context_docs),
        }

    def answer_stream(self, question: str, n_context: int = 5,
                      model_id: str | None = None):
        """Streaming version of answer() — yields tokens as they arrive."""
        context_docs = self.vector_store.search(question, n_results=n_context)
        context_text = "\n\n".join(doc['content'][:2000] for doc in context_docs)
        prompt = f"... (same prompt as above) ..."
        yield from self.llm.generate_stream(prompt, model_id=model_id)
```

### Frontend RAG Chat Page

```tsx
// frontend/src/pages/RagChat.tsx (simplified)
function RagChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [models, setModels] = useState<ModelListResponse | null>(null);
  const [activeModelId, setActiveModelId] = useState('');

  useEffect(() => {
    getModels().then(setModels);
  }, []);

  const sendMessage = async () => {
    const question = input;
    setMessages(prev => [...prev, { role: 'user', content: question }]);
    setInput('');

    // Stream the RAG answer
    const response = await ragQuery(question, activeModelId || undefined);
    setMessages(prev => [...prev, {
      role: 'assistant',
      content: response.answer,
      sources: response.sources,
    }]);
  };

  return (
    <Box>
      <FormControl>
        <Select value={activeModelId} onChange={e => setActiveModelId(e.target.value)}>
          {models?.free_models.map(m => (
            <MenuItem value={m.id}>🆓 {m.name}</MenuItem>
          ))}
          {models?.premium_models.map(m => (
            <MenuItem value={m.id}>⭐ {m.name}</MenuItem>
          ))}
        </Select>
      </FormControl>

      <Box sx={{ flex: 1, overflow: 'auto' }}>
        {messages.map(msg => (
          <ChatBubble message={msg} />
        ))}
      </Box>

      <TextField value={input} onChange={e => setInput(e.target.value)}
        onKeyDown={e => e.key === 'Enter' && sendMessage()}
        placeholder="Ask about the collected content..." />
    </Box>
  );
}
```

---

## 6. LLM Service — Provider Abstraction

```python
# pipeline/ai/llm_service.py
class LLMService:
    def generate(self, prompt: str, model_id: str | None = None,
                 stream: bool = False) -> str | Iterator[str]:
        model = self._resolve_model(model_id)

        # Primary path: LiteLLM for supported providers
        try:
            if stream:
                return self._generate_stream_litellm(model, prompt)
            return self._generate_litellm(model, prompt)
        except Exception:
            # Fallback path: direct provider API
            return self._fallback_generate(model, prompt)

    def _generate_litellm(self, model: ModelConfig, prompt: str) -> str:
        import litellm
        response = litellm.completion(
            model=model.id,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return response.choices[0].message.content

    def _fallback_generate(self, model: ModelConfig, prompt: str) -> str:
        if model.provider == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model=model.id.replace("openai/", ""),
                messages=[{"role": "user", "content": prompt}])
            return response.choices[0].message.content
        elif model.provider == "anthropic":
            # Direct Anthropic API call
            ...
        raise ValueError(f"No fallback for provider: {model.provider}")
```

---

## 7. Agentic Features

### Model Context Protocol (MCP) Server

```python
# pipeline/mcp/server.py
class ContentHubMCP:
    """Exposes content hub data via Model Context Protocol — enables AI
    agents to query content sources, search, and retrieve models."""

    def _build_tools(self):
        self._tools = {
            "search_content": types.Tool(
                name="search_content",
                description="Search across all content items by query",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "default": 20},
                        "topic": {"type": "string", "description": "Filter by topic"},
                    },
                    "required": ["query"],
                },
            ),
            "get_recent_content": types.Tool(
                name="get_recent_content",
                description="Get the most recent content items",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "default": 20},
                        "topic": {"type": "string"},
                    },
                },
            ),
            "get_model_list": types.Tool(
                name="get_model_list",
                description="List available AI models by tier",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tier": {"type": "string", "description": "free, premium, or all"},
                    },
                },
            ),
        }

    async def run(self):
        self.server = Server("ai-content-hub")
        self.server.list_tools = self._handle_list_tools
        self.server.call_tool = self._handle_call_tool
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream, ...)
```

### CLI Agent Interface

```bash
# cli/ai-content-hub — Terminal AI agent interface
#
# Usage examples:
#   python cli/ai-content-hub stats          # Show content statistics
#   python cli/ai-content-hub search "RAG"   # Search content
#   python cli/ai-content-hub recent         # Recent items
#   python cli/ai-content-hub projects       # List projects
#   python cli/ai-content-hub campaigns      # List campaigns
#   python cli/ai-content-hub mcp            # Start MCP server
```

### Workflow Engine (DAG-based Agent Orchestration)

```python
# pipeline/workflow/builder.py — Agent workflow builder
class WorkflowBuilder:
    def create(self, name: str, description: str = "") -> dict:
        """Creates a DAG-based agent workflow with trigger → collect → classify → notify nodes."""
        wf = {
            "id": str(uuid.uuid4()), "name": name, "description": description,
            "nodes": [], "edges": [], "status": "draft",
        }
        self.storage.save(wf)
        return wf

    def add_node(self, workflow_id: str, node_type: str, config: dict) -> dict:
        """node_type: trigger, collector, classifier, notifier"""
        node = {"id": str(uuid.uuid4()), "type": node_type, "config": config}
        self.storage.add_node(workflow_id, node)
        return node

# pipeline/workflow/engine.py — Parallel agent execution
class WorkflowEngine:
    def execute(self, workflow_id: str) -> dict:
        wf = self.storage.get(workflow_id)
        # Topological sort by DAG dependencies
        sorted_nodes = self._topological_sort(wf["nodes"], wf["edges"])
        # Execute in parallel where possible
        results = {}
        for batch in self._parallel_batches(sorted_nodes):
            with ThreadPoolExecutor() as pool:
                batch_results = pool.map(lambda n: self._execute_node(n, results), batch)
                results.update(batch_results)
        return results
```

---

## 8. Complete End-to-End Flow

```
User Input (CLI/API/UI)
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│  1. Collection Layer                                      │
│     BaseCollector.collect() → httpx/playwright/RSS → items │
│     Items normalized to ContentItem model                 │
└──────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│  2. Classification Layer                                  │
│     classify_item(item, method="hybrid")                  │
│       ├─ keyword TOPIC_KEYWORDS scoring (30 topics)       │
│       └─ optional LLM enrichment (OpenAI/Anthropic)       │
│     → ClassifiedItem with topics[0:3] + relevance_score   │
└──────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│  3. Storage Layer                                         │
│     VectorStore.store_items() → ChromaDB (embeddings)     │
│       └─ sentence-transformers all-MiniLM-L6-v2           │
│     SQLStore.store_items() → SQLite (metadata + FTS)      │
└──────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│  4. API Layer                                             │
│     FastAPI exposes:                                      │
│       /search?q= → vector + SQL full-text                 │
│       /stats → topic/source distribution                  │
│       /ai/rag/query → ChatEngine.answer()                 │
│       /ai/models → ModelRegistry.list_models()            │
│       /digest → topic-grouped Markdown                    │
└──────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│  5. UI Layer                                              │
│     React SPA consumes API → renders:                    │
│       Dashboard (stats, charts, recent items)             │
│       RagChat (model picker, Q&A with sources)            │
│       EnterpriseSearch (faceted filter, sort)            │
│       Projects/Campaigns (CRUD + Kanban)                  │
│       Streamlit dashboard (real-time monitoring)          │
└──────────────────────────────────────────────────────────┘
```
