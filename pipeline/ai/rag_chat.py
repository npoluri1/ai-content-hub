import json
from typing import Optional, Generator
from ..core.config import settings
from ..core.models import ContentItem
from ..storage.vector_store import VectorStore
from .llm_service import LLMService


class ChatEngine:
    def __init__(self, collection_name: str = "content_hub"):
        self.collection_name = collection_name
        self.store = VectorStore(db_path=settings.CHROMA_DB_PATH)
        self.llm = LLMService()

    def get_context(self, question: str, n: int = 5) -> list[dict]:
        results = self.store.search(question, n_results=n)
        return [
            {
                "id": r["id"],
                "title": r["metadata"].get("title", ""),
                "url": r["metadata"].get("url", ""),
                "source": r["metadata"].get("source", ""),
                "snippet": r["content"][:500],
                "distance": r.get("distance", 0),
            }
            for r in results
        ]

    def query(self, question: str, n_context: int = 5, system_prompt: str = None, model_id: Optional[str] = None) -> dict:
        sources = self.get_context(question, n=n_context)

        if not sources:
            return {"answer": "No relevant content found in the database.", "sources": []}

        context_text = "\n\n".join(
            f"[{i+1}] {s['title']} ({s['source']})\n{s['snippet']}"
            for i, s in enumerate(sources)
        )

        default_system = (
            "You are an AI assistant answering questions based on provided content. "
            "Answer concisely using only the context below. If the context doesn't contain "
            "enough information, say so."
        )
        system = system_prompt or default_system

        user_prompt = f"CONTEXT:\n{context_text}\n\nQUESTION: {question}\n\nAnswer:"

        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import threading
                future = asyncio.run_coroutine_threadsafe(
                    self.llm.generate(prompt=user_prompt, system_prompt=system, model_id=model_id),
                    loop,
                )
                answer = future.result(timeout=60)
            else:
                answer = asyncio.run(self.llm.generate(prompt=user_prompt, system_prompt=system, model_id=model_id))
        except ImportError:
            answer = self._fallback_llm(system, user_prompt, model_id)
        except Exception as e:
            answer = f"LLM error: {e}"

        return {"answer": answer, "sources": sources}

    def _fallback_llm(self, system: str, user_prompt: str, model_id: Optional[str] = None) -> str:
        model_cfg = self.llm.registry._available_models.get(model_id) if model_id else self.llm.get_active_config()
        provider = model_cfg.provider.value
        if provider == "openai" and settings.OPENAI_API_KEY:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=settings.OPENAI_API_KEY)
                resp = client.chat.completions.create(
                    model=model_cfg.litellm_model.replace("openai/", ""),
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user_prompt}],
                    max_tokens=1000, temperature=0.3,
                )
                return resp.choices[0].message.content
            except Exception as e:
                return f"OpenAI error: {e}"
        elif provider == "anthropic" and settings.ANTHROPIC_API_KEY:
            try:
                from anthropic import Anthropic
                client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
                resp = client.messages.create(
                    model=model_cfg.litellm_model.replace("anthropic/", ""),
                    max_tokens=1000, system=system,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                return resp.content[0].text
            except Exception as e:
                return f"Anthropic error: {e}"
        elif provider == "ollama":
            try:
                import requests
                resp = requests.post(
                    "http://localhost:11434/api/generate",
                    json={"model": model_cfg.id.replace("ollama-", ""), "prompt": f"{system}\n\n{user_prompt}", "stream": False},
                    timeout=60,
                )
                if resp.ok:
                    return resp.json().get("response", "")
                return f"Ollama error: {resp.status_code}"
            except Exception as e:
                return f"Ollama error: {e}"
        else:
            return f"[{model_cfg.name}] Mock response — no API key found."

    def query_stream(self, question: str, model_id: Optional[str] = None) -> Generator[str, None, None]:
        sources = self.get_context(question, n=5)
        if not sources:
            yield "No relevant content found in the database."
            return

        context_text = "\n\n".join(
            f"[{i+1}] {s['title']} ({s['source']})\n{s['snippet']}"
            for i, s in enumerate(sources)
        )

        system = "You are an AI assistant answering questions based on provided context. Answer concisely using only the context below."
        user_prompt = f"CONTEXT:\n{context_text}\n\nQUESTION: {question}\n\nAnswer:"

        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import threading
                future = asyncio.run_coroutine_threadsafe(
                    self.llm.generate(prompt=user_prompt, system_prompt=system, model_id=model_id),
                    loop,
                )
                yield future.result(timeout=60)
            else:
                yield asyncio.run(self.llm.generate(prompt=user_prompt, system_prompt=system, model_id=model_id))
        except:
            yield self._fallback_llm(system, user_prompt, model_id)
