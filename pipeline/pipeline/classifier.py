"""LangGraph classifier — classifies items by topic using keyword + LLM."""

from ..core.models import ContentItem, ClassifiedItem
from ..core.config import settings
import re

TOPIC_KEYWORDS: dict[str, list[str]] = {
    "AI": ["artificial intelligence", "machine learning", "deep learning", "neural network", "transformer", "gpt", "llm", "foundation model", "diffusion", "attention mechanism", "generative ai", "genai", "multimodal", "large language model"],
    "AgenticAI": ["agent", "langgraph", "autogen", "crewai", "multi-agent", "agentic", "agent orchestration", "function calling", "tool use", "agent framework", "task decomposition", "handoff", "agentic workflow", "react agent", "tool calling", "computer use", "claude code", "opencode", "codex cli", "copilot workspace", "windsurf", "aider", "cline", "agent mode", "ai coding", "agentic coding"],
    "AI_Frameworks": ["langchain", "llamaindex", "haystack", "pytorch", "tensorflow", "jax", "fastapi", "gradio", "vllm", "tgi", "ollama", "llamacpp", "mlflow", "kubeflow", "semantic kernel", "dspy", "chainlit", "crewai", "autogen", "agno", "dify", "multi-agent framework", "orchestration framework"],
    "LangChain": ["langchain", "lcel", "langchain expression", "langchain agent", "langchain chain", "langsmith", "langserve", "langgraph"],
    "LangGraph": ["langgraph", "state graph", "state machine", "graph state", "node edge", "graph agent", "conditional edge", "workflow graph", "stateful graph", "cyclic graph"],
    "Python": ["python", "django", "flask", "fastapi", "pydantic", "asyncio", "pandas", "numpy", "scipy", "jupyter", "pytest", "poetry", "pip", "virtualenv", "conda", "type hint", "dataclass", "starlette"],
    "ReactJS": ["react", "reactjs", "next.js", "nextjs", "typescript", "jsx", "tsx", "vite", "tailwind", "shadcn", "redux", "zustand", "react query", "server component", "ssr", "suspense", "hooks", "usestate", "useeffect"],
    "Transformers": ["transformers", "huggingface", "bert", "gpt-2", "gpt-3", "gpt-4", "t5", "bart", "roberta", "vit", "clip", "whisper", "codegen", "codellama", "mistral", "llama", "falcon", "phi", "gemma", "mixtral", "transformer architecture", "self-attention", "deepseek", "qwen", "codegemma", "starcoder", "mamba", "state space model"],
    "Prompting": ["prompt engineering", "prompt design", "few-shot", "zero-shot", "chain-of-thought", "cot", "tree-of-thoughts", "tot", "graph-of-thoughts", "got", "react", "reasoning and acting", "reflexion", "self-ask", "plan-and-solve", "reasoning", "system prompt", "prompt template", "prompt chaining", "prompt tuning", "instruction tuning", "prompt injection defense", "dspy", "structured output", "json mode", "constrained decoding", "outlines", "guidance"],
    "MCP": ["mcp", "model context protocol", "tool server", "mcp server", "mcp client", "resource", "prompt template", "mcp tool", "mcp resource", "mcp integration", "context protocol", "mcp sdk", "mcp connector"],
    "RAG": ["rag", "retrieval augmented", "vector database", "vector store", "chromadb", "qdrant", "weaviate", "pinecone", "embedding", "retrieval", "reranker", "hybrid search", "graphrag", "dense retrieval", "sparse retrieval", "colbert", "late interaction", "splade", "multi-vector", "agentic rag"],
    "Vector_Databases": ["pinecone", "weaviate", "qdrant", "milvus", "chromadb", "chroma", "pgvector", "elasticsearch", "vector search", "vector database", "vector index", "hnsw", "ivf", "ann", "approximate nearest neighbor", "lancedb"],
    "Embeddings": ["embedding", "embedding model", "text-embedding-3", "cohere embed", "bge", "bge embedding", "e5", "jina embedding", "voyage", "sentence-transformers", "openai embedding", "embed", "dense vector"],
    "Quantum_Computing": ["quantum", "qubit", "qbit", "willow", "sycamore", "qiskit", "cirq", "ionq", "quantum computing", "error correction", "superposition", "entanglement", "quantum circuit", "nisq", "penny lane", "braket", "q#", "q sharp", "quantinuum", "rigetti", "d-wave", "annealing", "cuda-q", "q-ctrl", "classiq"],
    "Robotics": ["robot", "robotics", "humanoid", "ros ", "ros2", "gazebo", "manipulation", "grasping", "slam", "motion planning", "figure ", "tesla bot", "optimus", "atlas", "spot", "drone", "autonomous vehicle", "mujoco", "pybullet", "isaac sim", "moveit", "reinforcement learning", "stable-baselines3", "rllib", "dopamine", "sb3"],
    "LLM_Ops": ["fine-tune", "rlhf", "dpo", "guardrail", "observability", "langfuse", "wandb", "mlflow", "prompt engineering", "prompt injection", "red team", "eval", "benchmark", "deploy", "inference", "quantization", "pruning", "distillation", "lora", "qlora", "peft", "sft", "model registry", "langsmith", "arize", "weights and biases", "ray", "experiment tracking", "llm observability"],
    "MLOps": ["mlops", "ci/cd", "data pipeline", "feature store", "model serving", "model monitoring", "data drift", "model drift", "a/b test", "canary deploy", "pipeline orchestration", "airflow", "kubeflow", "zenml", "dvc", "mlflow pipeline"],
    "DevOps_Cloud": ["docker", "kubernetes", "k8s", "terraform", "aws", "gcp", "azure", "cloud computing", "serverless", "lambda", "ecs", "eks", "github actions", "gitlab ci", "devops", "infrastructure", "microservice", "helm", "ansible", "pulumi"],
    "Database": ["postgresql", "postgres", "mongodb", "redis", "sqlite", "mysql", "sql", "nosql", "database", "data modeling", "orm", "sqlalchemy", "prisma", "migration", "indexing", "cassandra", "dynamodb", "cockroachdb", "timescaledb"],
    "Security": ["cybersecurity", "prompt injection", "jailbreak", "guardrail", "authentication", "authorization", "oauth", "jwt", "rbac", "pii", "data privacy", "compliance", "penetration test", "zero trust", "encryption", "waf", "rate limit", "api security"],
    "Data_Science": ["data science", "data analysis", "statistics", "visualization", "matplotlib", "seaborn", "plotly", "tableau", "power bi", "eda", "feature engineering", "hypothesis testing", "regression", "classification", "clustering", "pandas dataframe"],
    "Computer_Vision": ["computer vision", "opencv", "yolo", "object detection", "image segmentation", "image classification", "facial recognition", "ocr", "visual question answering", "stable diffusion", "dall-e", "midjourney", "image generation", "video understanding", "pose estimation"],
    "NLP": ["natural language processing", "text classification", "ner", "named entity", "sentiment analysis", "text summarization", "machine translation", "tokenizer", "pos tagging", "dependency parsing", "text generation", "speech recognition", "text to speech", "tts", "speech to text", "stt"],
    "Edge_AI": ["edge ai", "edge computing", "onnx", "tensorrt", "openvino", "tflite", "coreml", "tinyML", "embedded ml", "mobile inference", "quantization aware", "wasmedge", "webassembly", "ebpf", "jetson", "raspberry pi", "arm ethos"],
    "Semiconductors": ["semiconductor", "chip design", "cadence", "synopsys", "siemens eda", "systemverilog", "uvm", "verilator", "chisel", "arm", "risc-v", "x86", "nvidia cuda", "amd rocm", "google tpu", "groq lpu", "cerebras", "graphcore ipu", "tenstorrent", "eda", "asic", "fpga", "vlsi"],
    "IoT": ["iot", "internet of things", "aws iot", "azure iot hub", "gcp iot", "edgex foundry", "mqtt", "coap", "lwm2m", "opc-ua", "modbus", "industrial iot", "smart home", "sensor network", "telemetry"],
    "API_Development": ["api", "rest api", "graphql", "apollo", "strawberry", "grpc", "websocket", "server-sent events", "sse", "api gateway", "api design", "openapi", "swagger", "fastapi", "starlette"],
    "Workflow_Automation": ["n8n", "zapier", "make", "integromat", "workflow automation", "low-code", "no-code", "automation", "visual workflow", "drag and drop", "workflow builder"],
    "Coding_Assistants": ["claude code", "opencode", "cursor", "copilot", "github copilot", "windsurf", "codeium", "continue", "aider", "codex cli", "ai coding assistant", "ai ide", "agent mode", "ai pair programming", "tabnine", "supermaven"],
    "AI_Cloud_Infra": ["aws bedrock", "azure openai", "gcp vertex ai", "amazon sagemaker", "huggingface inference", "ollama", "vllm", "tgi", "text generation inference", "together ai", "groq", "fireworks ai", "inference endpoint", "model serving", "ai platform", "cloud ai"],
}

TOPIC_ALIASES: dict[str, str] = {
    "ai": "AI", "artificial intelligence": "AI", "machine learning": "AI", "deep learning": "AI", "genai": "AI", "generative ai": "AI",
    "agent": "AgenticAI", "agents": "AgenticAI", "multi agent": "AgenticAI", "agentic": "AgenticAI",
    "langchain": "LangChain", "lc el": "LangChain",
    "langgraph": "LangGraph", "state graph": "LangGraph",
    "python": "Python", "fastapi": "Python", "django": "Python", "flask": "Python", "pydantic": "Python",
    "react": "ReactJS", "nextjs": "ReactJS", "typescript": "ReactJS", "vite": "ReactJS",
    "transformer": "Transformers", "huggingface": "Transformers", "bert": "Transformers", "gpt": "Transformers",
    "prompt": "Prompting", "few shot": "Prompting", "chain of thought": "Prompting", "cot": "Prompting", "dspy": "Prompting", "react reasoning": "Prompting",
    "mcp": "MCP", "model context protocol": "MCP",
    "retrieval": "RAG", "vector store": "RAG", "chroma": "RAG", "reranker": "RAG",
    "pinecone": "Vector_Databases", "weaviate": "Vector_Databases", "qdrant": "Vector_Databases", "milvus": "Vector_Databases", "pgvector": "Vector_Databases",
    "embedding model": "Embeddings", "sentence transformer": "Embeddings", "bge": "Embeddings",
    "quantum": "Quantum_Computing", "qiskit": "Quantum_Computing", "qubit": "Quantum_Computing",
    "robot": "Robotics", "robotics": "Robotics", "humanoid": "Robotics", "ros2": "Robotics",
    "fine tune": "LLM_Ops", "guardrail": "LLM_Ops", "deploy": "LLM_Ops", "lora": "LLM_Ops", "peft": "LLM_Ops", "langfuse": "LLM_Ops", "langsmith": "LLM_Ops",
    "mlops": "MLOps", "pipeline orchestration": "MLOps",
    "docker": "DevOps_Cloud", "kubernetes": "DevOps_Cloud", "cloud": "DevOps_Cloud", "aws": "DevOps_Cloud", "gcp": "DevOps_Cloud",
    "database": "Database", "postgres": "Database", "sql": "Database", "mongodb": "Database", "redis": "Database",
    "security": "Security", "cybersecurity": "Security", "injection": "Security",
    "data science": "Data_Science", "visualization": "Data_Science", "statistics": "Data_Science",
    "computer vision": "Computer_Vision", "object detection": "Computer_Vision", "image": "Computer_Vision",
    "nlp": "NLP", "natural language": "NLP", "sentiment": "NLP", "translation": "NLP",
    "edge": "Edge_AI", "onnx": "Edge_AI", "tflite": "Edge_AI", "jetson": "Edge_AI", "webassembly": "Edge_AI", "wasmedge": "Edge_AI",
    "chip": "Semiconductors", "semiconductor": "Semiconductors", "risc v": "Semiconductors", "cuda": "Semiconductors", "tpu": "Semiconductors",
    "iot": "IoT", "mqtt": "IoT", "internet of things": "IoT",
    "graphql": "API_Development", "grpc": "API_Development", "websocket": "API_Development", "rest api": "API_Development",
    "n8n": "Workflow_Automation", "zapier": "Workflow_Automation", "automation": "Workflow_Automation",
    "claude code": "Coding_Assistants", "cursor": "Coding_Assistants", "copilot": "Coding_Assistants", "aider": "Coding_Assistants",
    "bedrock": "AI_Cloud_Infra", "vertex ai": "AI_Cloud_Infra", "sagemaker": "AI_Cloud_Infra", "ollama": "AI_Cloud_Infra", "vllm": "AI_Cloud_Infra", "groq": "AI_Cloud_Infra",
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
    valid_topics = "AI, AgenticAI, AI_Frameworks, LangChain, LangGraph, Python, ReactJS, Transformers, Prompting, MCP, RAG, Vector_Databases, Embeddings, Quantum_Computing, Robotics, LLM_Ops, MLOps, DevOps_Cloud, Database, Security, Data_Science, Computer_Vision, NLP, Edge_AI, Semiconductors, IoT, API_Development, Workflow_Automation, Coding_Assistants, AI_Cloud_Infra"
    prompt = f"""Classify this content into relevant topics from: {valid_topics}

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
    valid = {"AI", "AgenticAI", "AI_Frameworks", "LangChain", "LangGraph", "Python", "ReactJS", "Transformers", "Prompting", "MCP", "RAG", "Vector_Databases", "Embeddings", "Quantum_Computing", "Robotics", "LLM_Ops", "MLOps", "DevOps_Cloud", "Database", "Security", "Data_Science", "Computer_Vision", "NLP", "Edge_AI", "Semiconductors", "IoT", "API_Development", "Workflow_Automation", "Coding_Assistants", "AI_Cloud_Infra"}
    return [t for t in topics if t in valid]
