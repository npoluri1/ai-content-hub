from ...core.base_collector import BaseCollector
from ...core.models import ContentItem
from datetime import datetime, timedelta
import random

DEMO_DATA = {
    "linkedin": [
        ContentItem(id="dli1", title="Production AI Stack", content="The $0 agent stack: Ollama + LangGraph + ChromaDB + MCP works for demos. Production requires checkpointing, RBAC, observability, and hardware specs. The gap is where AI PMs get destroyed.", source="linkedin", source_type="post", author_name="Bally S Kehal", author_url="https://linkedin.com/in/ballyskehal", hashtags=["AgenticAI","LangGraph","MCP"], topics=["AgenticAI","AI_Frameworks","MCP"], engagement=567, published_at=datetime.now()-timedelta(hours=2), relevance_score=0.95),
        ContentItem(id="dli2", title="Multi-Agent Systems", content="Multi-agent systems are eating the world. We just deployed 12 specialized agents across procurement, legal, and compliance. Key insight: agent handoff protocol matters more than agent capability.", source="linkedin", source_type="post", author_name="Harrison Chase", author_url="https://linkedin.com/in/harrisonchase", hashtags=["AgenticAI","multiagent"], topics=["AgenticAI"], engagement=1200, published_at=datetime.now()-timedelta(hours=5), relevance_score=0.92),
        ContentItem(id="dli3", title="MCP Protocol", content="MCP is the most important protocol you haven't adopted yet. It turns your database, APIs, and file system into tools your LLM can use with proper auth and rate limiting.", source="linkedin", source_type="post", author_name="Anthropic", hashtags=["MCP","protocol"], topics=["MCP"], engagement=3200, published_at=datetime.now()-timedelta(hours=3), relevance_score=0.90),
        ContentItem(id="dli4", title="LangGraph Checkpointing", content="LangGraph checkpointing saved us 40 hours this week. Being able to pause, inspect, correct, and resume agent mid-run is not a feature — it's a requirement.", source="linkedin", source_type="post", author_name="LangChain Team", hashtags=["LangGraph","AgenticAI"], topics=["AgenticAI","AI_Frameworks"], engagement=780, published_at=datetime.now()-timedelta(hours=4), relevance_score=0.88),
        ContentItem(id="dli5", title="GPT-5 Production", content="Just deployed GPT-5.5 in production for our customer support pipeline. Latency dropped 40% with speculative decoding. Key: batching strategy matters more than model size.", source="linkedin", source_type="post", author_name="Andrej Karpathy", hashtags=["AI","LLM","production"], topics=["AI","LLM_Ops"], engagement=1420, published_at=datetime.now()-timedelta(hours=1), relevance_score=0.85),
        ContentItem(id="dli6", title="OpenFang Agent Security", content="Dangerous: connecting MCP to production without RBAC. One prompt injection into your RAG pipeline ends enterprise deals. Data isolation before MCP, always.", source="linkedin", source_type="post", author_name="Bally S Kehal", hashtags=["MCP","security"], topics=["MCP","LLM_Ops"], engagement=890, published_at=datetime.now()-timedelta(hours=6), relevance_score=0.93),
        ContentItem(id="dli7", title="Hybrid RAG Production", content="Hybrid RAG is the only RAG that works in production. Keyword + vector search + reranking. Pure vector search fails on exact match.", source="linkedin", source_type="post", author_name="Jerry Liu", hashtags=["RAG"], topics=["RAG"], engagement=980, published_at=datetime.now()-timedelta(hours=8), relevance_score=0.87),
    ],
    "reddit": [
        ContentItem(id="dre1", title="r/MachineLearning - What's your AI stack?", content="What's everyone using for their production AI stack in 2026? We're on LangGraph + ChromaDB + FastAPI. Thinking of adding MCP for tool integration. What's your experience?", source="reddit", source_type="post", author_name="u/ml_engineer", hashtags=["AI","stack"], topics=["AI_Frameworks"], engagement=342, published_at=datetime.now()-timedelta(hours=1)),
        ContentItem(id="dre2", title="r/LocalLLaMA - Running 70B on consumer hardware", content="Successfully running Llama 4 70B on 2x RTX 5090s with 4-bit quantization. Getting 45 tokens/s. Here's my config and setup guide.", source="reddit", source_type="post", author_name="u/local_ai_guy", hashtags=["LLM","quantization"], topics=["AI","LLM_Ops"], engagement=567, published_at=datetime.now()-timedelta(hours=3)),
        ContentItem(id="dre3", title="r/Rag - GraphRAG vs Vector RAG", content="Comparing GraphRAG and Vector RAG on a dataset of 10k documents. GraphRAG wins on multi-hop questions (30% better) but loses on simple lookup. Hybrid approach recommended.", source="reddit", source_type="post", author_name="u/rag_researcher", hashtags=["RAG","GraphRAG"], topics=["RAG"], engagement=234, published_at=datetime.now()-timedelta(hours=5)),
        ContentItem(id="dre4", title="r/ClaudeAI - MCP server for databases", content="Built an MCP server that connects Claude to our Postgres database. Write SQL queries in natural language. Open sourcing it here.", source="reddit", source_type="post", author_name="u/db_dev", hashtags=["MCP","Claude"], topics=["MCP","AI_Frameworks"], engagement=189, published_at=datetime.now()-timedelta(hours=2)),
        ContentItem(id="dre5", title="r/artificial - Google Willow quantum chip", content="Google's Willow chip reaches error correction below threshold. 105 qubits. This changes everything for quantum computing.", source="reddit", source_type="post", author_name="u/quantum_fan", hashtags=["Quantum_Computing"], topics=["Quantum_Computing"], engagement=890, published_at=datetime.now()-timedelta(hours=7)),
    ],
    "techcrunch": [
        ContentItem(id="dtc1", title="OpenAI Launches GPT-5.5 with 1M Context Window", content="OpenAI has announced GPT-5.5, featuring a 1 million token context window and 60% reduction in API pricing. The model shows significant improvements in reasoning and coding benchmarks.", source="techcrunch", source_type="news", author_name="TechCrunch", url="https://techcrunch.com/2026/06/gpt-5-5", hashtags=["AI","OpenAI","GPT"], topics=["AI"], engagement=1200, published_at=datetime.now()-timedelta(hours=3)),
        ContentItem(id="dtc2", title="Anthropic Releases Claude 5 with Agent Mode", content="Anthropic's Claude 5 introduces native agent mode with tool calling, multi-step planning, and computer use capabilities built into the base model.", source="techcrunch", source_type="news", author_name="TechCrunch", url="https://techcrunch.com/2026/06/claude-5", hashtags=["AI","Anthropic","Claude"], topics=["AI","AgenticAI"], engagement=980, published_at=datetime.now()-timedelta(hours=6)),
        ContentItem(id="dtc3", title="Robotics Startup Raises $2B for Humanoid Factory Workers", content="Figure Robotics has raised $2B in Series D funding to deploy humanoid robots in manufacturing. The company claims full autonomy in 80% of factory tasks by 2027.", source="techcrunch", source_type="news", author_name="TechCrunch", hashtags=["Robotics","funding"], topics=["Robotics"], engagement=1560, published_at=datetime.now()-timedelta(hours=12)),
    ],
    "arxiv": [
        ContentItem(id="dar1", title="GraphRAG: Knowledge Graph Enhanced Retrieval", content="We propose GraphRAG, a method that enhances RAG with knowledge graph structures. Experiments show 35% improvement on multi-hop QA datasets compared to vanilla RAG.", source="arxiv", source_type="paper", author_name="Zhang et al.", url="https://arxiv.org/abs/2606.01234", hashtags=["RAG","GraphRAG"], topics=["RAG"], published_at=datetime.now()-timedelta(days=2)),
        ContentItem(id="dar2", title="MCP-Agent: Model Context Protocol for Tool Use", content="This paper formalizes the Model Context Protocol (MCP) for safe tool use in language agents. We demonstrate 40% reduction in security incidents when enforcing MCP boundaries.", source="arxiv", source_type="paper", author_name="Anthropic Research", url="https://arxiv.org/abs/2606.04567", hashtags=["MCP","agents"], topics=["MCP","AgenticAI"], published_at=datetime.now()-timedelta(days=1)),
        ContentItem(id="dar3", title="Scaling Multi-Agent Systems: A Production Framework", content="We present a framework for scaling multi-agent systems from prototype to production. Key contributions: agent handoff protocol, state checkpointing, and observability instrumentation.", source="arxiv", source_type="paper", author_name="Singh et al.", url="https://arxiv.org/abs/2606.07890", hashtags=["AgenticAI","multi-agent"], topics=["AgenticAI"], published_at=datetime.now()-timedelta(days=3)),
        ContentItem(id="dar4", title="Llama 4: Technical Report", content="Meta presents Llama 4, the next generation of open large language models. Mixture-of-experts architecture with 10^25 training FLOPs. Outperforms GPT-4 on key benchmarks.", source="arxiv", source_type="paper", author_name="Meta AI", url="https://arxiv.org/abs/2606.00001", hashtags=["LLM","Meta","Llama"], topics=["AI","LLM_Ops"], published_at=datetime.now()-timedelta(days=5)),
    ],
    "youtube": [
        ContentItem(id="dyt1", title="Building Production AI Agents with LangGraph", content="Full tutorial on building production-grade AI agents using LangGraph, MCP, and ChromaDB. Includes checkpointing, error handling, and deployment.", source="youtube", source_type="video", author_name="AI Engineering", url="https://youtube.com/watch?v=abc123", hashtags=["LangGraph","AgenticAI","tutorial"], topics=["AgenticAI","AI_Frameworks"], video_url="https://youtube.com/watch?v=abc123", engagement=45000, published_at=datetime.now()-timedelta(days=1)),
        ContentItem(id="dyt2", title="RAG from Scratch to Production", content="Complete RAG pipeline walkthrough: embeddings, vector databases, retrieval strategies, reranking, and evaluation. Code available on GitHub.", source="youtube", source_type="video", author_name="ML Engineering", url="https://youtube.com/watch?v=def456", hashtags=["RAG","tutorial"], topics=["RAG"], video_url="https://youtube.com/watch?v=def456", engagement=32000, published_at=datetime.now()-timedelta(days=3)),
        ContentItem(id="dyt3", title="MCP Protocol Explained (with Demo)", content="Deep dive into the Model Context Protocol by Anthropic. How MCP enables LLMs to safely interact with external tools and data sources.", source="youtube", source_type="video", author_name="Tech Deep Dive", url="https://youtube.com/watch?v=ghi789", hashtags=["MCP","Anthropic"], topics=["MCP"], video_url="https://youtube.com/watch?v=ghi789", engagement=28000, published_at=datetime.now()-timedelta(days=2)),
    ],
    "hackernews": [
        ContentItem(id="dhn1", title="Show HN: Open-source AI agent orchestration platform", content="Built an open-source platform for orchestrating AI agents in production. Supports LangGraph workflows, MCP integration, and ChromaDB storage. 5k GitHub stars in first week.", source="hackernews", source_type="post", author_name="show-hn", url="https://news.ycombinator.com/item?id=1", hashtags=["AgenticAI","opensource"], topics=["AgenticAI","AI_Frameworks"], engagement=345, published_at=datetime.now()-timedelta(hours=8)),
        ContentItem(id="dhn2", title="Ask HN: What's your RAG stack in 2026?", content="Curious what RAG stacks people are using in production this year. Seeing a lot of ChromaDB + LiteLLM + LangChain combos. Anyone using Qdrant or Weaviate?", source="hackernews", source_type="post", author_name="ask-hn", hashtags=["RAG","stack"], topics=["RAG"], engagement=234, published_at=datetime.now()-timedelta(hours=10)),
        ContentItem(id="dhn3", title="Google Willow: Error correction milestone", content="Google's quantum chip Willow achieves error correction below threshold for the first time. 105 qubits with error suppression. This is the crossover point for fault-tolerant quantum computing.", source="hackernews", source_type="post", author_name="quantum-physics", url="https://news.ycombinator.com/item?id=2", hashtags=["Quantum_Computing"], topics=["Quantum_Computing"], engagement=567, published_at=datetime.now()-timedelta(hours=4)),
    ],
}


class DemoCollector(BaseCollector):
    name = "demo"

    def __init__(self, source_filter: str = None):
        self.source_filter = source_filter

    def collect(self, max_items: int = 200) -> list[ContentItem]:
        items = []
        for source_key, source_items in DEMO_DATA.items():
            if self.source_filter and source_key != self.source_filter:
                continue
            items.extend(source_items)

        random.shuffle(items)
        for item in items:
            item.content_cleaned = self.clean_content(item.content)
        return items[:max_items]

    def collect_by_source(self, source: str, max_items: int = 50) -> list[ContentItem]:
        items = DEMO_DATA.get(source, [])
        for item in items:
            item.content_cleaned = self.clean_content(item.content)
        return items[:max_items]
