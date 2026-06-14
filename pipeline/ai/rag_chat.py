import json
from typing import Optional, Generator
from ..core.config import settings
from ..core.models import ContentItem
from ..storage.vector_store import VectorStore


class ChatEngine:
    def __init__(self, collection_name: str = "content_hub"):
        self.collection_name = collection_name
        self.store = VectorStore(db_path=settings.CHROMA_DB_PATH)

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

    def query(self, question: str, n_context: int = 5, system_prompt: str = None) -> dict:
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

        provider = settings.LLM_PROVIDER
        if provider == "none" or (not settings.OPENAI_API_KEY and not settings.ANTHROPIC_API_KEY and provider != "ollama"):
            return {
                "answer": f"No LLM configured. Found {len(sources)} relevant sources.\n\nRelevant content:\n\n{context_text}",
                "sources": sources,
            }

        user_prompt = f"CONTEXT:\n{context_text}\n\nQUESTION: {question}\n\nAnswer:"

        answer = None
        if provider == "openai" and settings.OPENAI_API_KEY:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=settings.OPENAI_API_KEY)
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_tokens=1000,
                    temperature=0.3,
                )
                answer = resp.choices[0].message.content
            except Exception as e:
                answer = f"OpenAI error: {e}"
        elif provider == "anthropic" and settings.ANTHROPIC_API_KEY:
            try:
                from anthropic import Anthropic
                client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
                resp = client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=1000,
                    system=system,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                answer = resp.content[0].text
            except Exception as e:
                answer = f"Anthropic error: {e}"
        elif provider == "ollama":
            try:
                import requests
                resp = requests.post(
                    "http://localhost:11434/api/generate",
                    json={"model": "llama3", "prompt": f"{system}\n\n{user_prompt}", "stream": False},
                    timeout=60,
                )
                if resp.ok:
                    answer = resp.json().get("response", "")
                else:
                    answer = f"Ollama error: {resp.status_code}"
            except Exception as e:
                answer = f"Ollama error: {e}"
        else:
            answer = "No LLM configured."

        return {"answer": answer, "sources": sources}

    def query_stream(self, question: str) -> Generator[str, None, None]:
        sources = self.get_context(question, n=5)
        if not sources:
            yield "No relevant content found in the database."
            return

        context_text = "\n\n".join(
            f"[{i+1}] {s['title']} ({s['source']})\n{s['snippet']}"
            for i, s in enumerate(sources)
        )

        provider = settings.LLM_PROVIDER
        if provider == "none" or (not settings.OPENAI_API_KEY and not settings.ANTHROPIC_API_KEY and provider != "ollama"):
            yield f"No LLM configured. Found {len(sources)} relevant sources.\n\nRelevant content:\n\n{context_text}"
            return

        system = (
            "You are an AI assistant answering questions based on provided context. "
            "Answer concisely using only the context below."
        )
        user_prompt = f"CONTEXT:\n{context_text}\n\nQUESTION: {question}\n\nAnswer:"

        if provider == "openai" and settings.OPENAI_API_KEY:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=settings.OPENAI_API_KEY)
                stream = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_tokens=1000,
                    temperature=0.3,
                    stream=True,
                )
                for chunk in stream:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content
            except Exception as e:
                yield f"OpenAI error: {e}"
        elif provider == "ollama":
            try:
                import requests
                resp = requests.post(
                    "http://localhost:11434/api/generate",
                    json={"model": "llama3", "prompt": f"{system}\n\n{user_prompt}", "stream": True},
                    stream=True,
                    timeout=120,
                )
                for line in resp.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            chunk = data.get("response", "")
                            if chunk:
                                yield chunk
                        except json.JSONDecodeError:
                            pass
            except Exception as e:
                yield f"Ollama error: {e}"
        else:
            yield "LLM streaming not supported for the current provider."
