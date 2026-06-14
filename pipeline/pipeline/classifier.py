"""LangGraph classifier — classifies items by topic using keyword + LLM."""

from ..core.models import ContentItem, ClassifiedItem
from ..core.config import settings
import re

TOPIC_KEYWORDS: dict[str, list[str]] = {
    "AI": ["artificial intelligence", "machine learning", "deep learning", "neural network", "transformer", "gpt", "llm", "foundation model", "diffusion", "attention mechanism"],
    "AgenticAI": ["agent", "langgraph", "autogen", "crewai", "multi-agent", "agentic", "agent orchestration", "function calling", "tool use", "agent framework", "task decomposition", "handoff"],
    "AI_Frameworks": ["langchain", "llamaindex", "haystack", "pytorch", "tensorflow", "jax", "fastapi", "gradio", "vllm", "tgi", "ollama", "llamacpp", "mlflow", "kubeflow"],
    "Quantum_Computing": ["quantum", "qubit", "qbit", "willow", "qiskit", "cirq", "ionq", "quantum computing", "error correction", "superposition", "entanglement"],
    "Robotics": ["robot", "robotics", "humanoid", "ros ", "ros2", "gazebo", "manipulation", "grasping", "slam", "motion planning", "figure ", "tesla bot", "optimus", "atlas"],
    "RAG": ["rag", "retrieval augmented", "vector database", "vector store", "chromadb", "qdrant", "weaviate", "pinecone", "embedding", "retrieval", "reranker", "hybrid search", "graphrag", "dense retrieval"],
    "MCP": ["mcp", "model context protocol", "tool server", "mcp server", "mcp client", "resource", "prompt template"],
    "LLM_Ops": ["fine-tune", "rlhf", "dpo", "guardrail", "observability", "langfuse", "wandb", "mlflow", "prompt engineering", "prompt injection", "red team", "eval", "benchmark", "deploy", "inference", "quantization", "pruning", "distillation"],
}

TOPIC_ALIASES: dict[str, str] = {
    "ai": "AI", "artificial intelligence": "AI", "machine learning": "AI", "deep learning": "AI",
    "agent": "AgenticAI", "agents": "AgenticAI", "multi agent": "AgenticAI",
    "langchain": "AI_Frameworks", "llamaindex": "AI_Frameworks", "pytorch": "AI_Frameworks",
    "quantum": "Quantum_Computing", "qiskit": "Quantum_Computing",
    "robot": "Robotics", "robotics": "Robotics",
    "retrieval": "RAG", "vector": "RAG", "chroma": "RAG",
    "mcp": "MCP",
    "fine tune": "LLM_Ops", "guardrail": "LLM_Ops", "deploy": "LLM_Ops",
}


def classify_item(item: ContentItem, method: str = "hybrid") -> ClassifiedItem:
    text = (item.content + " " + item.title + " " + " ".join(item.hashtags)).lower()

    # Keyword classification
    keyword_topics: set[str] = set()
    keyword_scores: dict[str, float] = {}

    for topic, keywords in TOPIC_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if kw in text:
                count = text.count(kw)
                score += count * (1.0 if len(kw) > 5 else 0.5)
        if score > 0:
            keyword_topics.add(topic)
            keyword_scores[topic] = score

    # Also check aliases
    for alias, topic in TOPIC_ALIASES.items():
        if alias in text:
            keyword_topics.add(topic)
            keyword_scores[topic] = keyword_scores.get(topic, 0) + 0.5

    # LLM classification
    llm_topics: list[str] = []
    if method in ("llm", "hybrid") and settings.LLM_PROVIDER != "none":
        try:
            llm_topics = _classify_with_llm(item, text)
        except Exception as e:
            print(f"  [Classifier] LLM failed: {e}")

    # Merge
    final_topics: list[str]
    if method == "keyword":
        final_topics = sorted(keyword_topics, key=lambda t: keyword_scores.get(t, 0), reverse=True)
    elif method == "llm":
        final_topics = llm_topics
    else:
        combined = keyword_topics | set(llm_topics)
        final_topics = sorted(combined, key=lambda t: keyword_scores.get(t, 0) + (2 if t in llm_topics else 0), reverse=True)

    is_relevant = len(final_topics) > 0
    if is_relevant and not keyword_topics and not llm_topics:
        is_relevant = False

    return ClassifiedItem(
        **item.model_dump(exclude={"topics", "relevance_score"}),
        topics=final_topics[:3],
        relevance_score=keyword_scores.get(final_topics[0], 0.5) if final_topics else 0.0,
        is_relevant=is_relevant,
        classification_method=method,
    )


def _classify_with_llm(item: ContentItem, text: str) -> list[str]:
    provider = settings.LLM_PROVIDER
    prompt = f"""Classify this content into relevant topics from: AI, AgenticAI, AI_Frameworks, Quantum_Computing, Robotics, RAG, MCP, LLM_Ops

Title: {item.title[:200]}
Content: {text[:1500]}
Hashtags: {', '.join(item.hashtags[:10])}

Return ONLY a comma-separated list of relevant topics:"""

    if provider == "openai" and settings.OPENAI_API_KEY:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1, max_tokens=50,
        )
        result = resp.choices[0].message.content or ""
    elif provider == "anthropic" and settings.ANTHROPIC_API_KEY:
        import httpx
        with httpx.Client() as client:
            resp = client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": settings.ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01"},
                json={"model": "claude-3-haiku-20240307", "max_tokens": 50, "messages": [{"role": "user", "content": prompt}]},
            )
            result = resp.json().get("content", [{}])[0].get("text", "")
    else:
        return []

    topics = [t.strip().replace(" ", "_") for t in result.split(",") if t.strip()]
    valid = {"AI", "AgenticAI", "AI_Frameworks", "Quantum_Computing", "Robotics", "RAG", "MCP", "LLM_Ops"}
    return [t for t in topics if t in valid]
