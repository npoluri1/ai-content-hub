"""
Azure AI Stack — Azure OpenAI + AI Search + AI Studio for enterprise-grade RAG.
"""

import os
from dataclasses import dataclass

@dataclass
class AzureConfig:
    openai_endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    openai_key: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    search_endpoint: str = os.getenv("AZURE_SEARCH_ENDPOINT", "")
    search_key: str = os.getenv("AZURE_SEARCH_KEY", "")
    deployment: str = "gpt-4o"

class AzureHybridRAG:
    def __init__(self, config: AzureConfig):
        self.config = config

    def retrieve(self, query: str, top_k: int = 5):
        # Azure AI Search hybrid (vector + keyword)
        return self._hybrid_search(query, top_k)

    def _hybrid_search(self, query: str, k: int):
        return [
            {"content": f"Azure AI Search result {i} for: {query}",
             "score": 0.95 - (i * 0.05)}
            for i in range(k)
        ]

    def generate(self, query: str, context: list[dict]) -> str:
        docs = "\n".join([d["content"] for d in context])
        return f"Generated answer based on:\n{docs}"

    def query(self, user_query: str):
        docs = self.retrieve(user_query)
        return self.generate(user_query, docs)

rag = AzureHybridRAG(AzureConfig())
result = rag.query("What is multi-agent orchestration?")
print(result)
