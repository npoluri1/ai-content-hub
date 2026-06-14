import re
import json
from typing import Optional
from ..core.config import settings
from ..core.models import ContentItem


def _call_llm(prompt: str, max_tokens: int = 500) -> Optional[str]:
    provider = settings.LLM_PROVIDER
    if provider == "openai" and settings.OPENAI_API_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.3,
            )
            return resp.choices[0].message.content
        except Exception as e:
            print(f"  [Summarizer] OpenAI error: {e}")
    elif provider == "anthropic" and settings.ANTHROPIC_API_KEY:
        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            resp = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.content[0].text
        except Exception as e:
            print(f"  [Summarizer] Anthropic error: {e}")
    elif provider == "ollama":
        try:
            import requests
            resp = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": "llama3", "prompt": prompt, "stream": False, "options": {"num_predict": max_tokens}},
                timeout=60,
            )
            if resp.ok:
                return resp.json().get("response", "")
        except Exception as e:
            print(f"  [Summarizer] Ollama error: {e}")
    return None


def _extractive_summarize(text: str, max_sentences: int = 5) -> str:
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    if len(sentences) <= max_sentences:
        return " ".join(sentences)

    from collections import Counter
    import re as _re

    words = _re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    word_freq = Counter(words)
    max_freq = max(word_freq.values()) if word_freq else 1

    scored = []
    for i, sent in enumerate(sentences):
        sent_lower = sent.lower()
        score = sum(word_freq.get(w, 0) for w in _re.findall(r'\b[a-zA-Z]{3,}\b', sent_lower))
        score /= max_freq
        position_bonus = 1.0 if i == 0 else (0.8 if i <= 2 else 0.5)
        scored.append((score * position_bonus, sent))

    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [s[1] for s in scored[:max_sentences]]

    original_order = sorted(selected, key=lambda s: sentences.index(s))
    return " ".join(original_order)


def summarize(text: str, max_sentences: int = 5) -> str:
    if not text or not text.strip():
        return ""

    provider = settings.LLM_PROVIDER
    if provider not in ("none", "") and (settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY or provider == "ollama"):
        prompt = (
            f"Summarize the following content in {max_sentences} sentences or fewer. "
            f"Capture the key points concisely.\n\nCONTENT:\n{text[:8000]}"
        )
        result = _call_llm(prompt)
        if result:
            return result.strip()

    return _extractive_summarize(text, max_sentences)


def _summarize_with_length(text: str, length: str = "normal") -> str:
    length_map = {"brief": 2, "normal": 5, "detailed": 10}
    n = length_map.get(length, 5)
    provider = settings.LLM_PROVIDER
    if provider not in ("none", "") and (settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY or provider == "ollama"):
        length_desc = {"brief": "1-2 sentences", "normal": "3-5 sentences", "detailed": "a detailed paragraph"}
        prompt = (
            f"Summarize the following content in {length_desc.get(length, '3-5 sentences')}. "
            f"Capture the key points concisely.\n\nCONTENT:\n{text[:8000]}"
        )
        result = _call_llm(prompt)
        if result:
            return result.strip()
    return _extractive_summarize(text, n)


def batch_summarize(items: list[ContentItem]) -> list[dict]:
    results = []
    for item in items:
        summary = summarize(item.content_cleaned or item.content)
        results.append({
            "id": item.id,
            "title": item.title,
            "summary": summary,
        })
    return results


def summarize_to_file(items: list[ContentItem], output_path: str):
    summaries = batch_summarize(items)
    lines = []
    for s in summaries:
        lines.append(f"# {s['title']}")
        lines.append(f"ID: {s['id']}")
        lines.append("")
        lines.append(s['summary'])
        lines.append("")
        lines.append("---")
        lines.append("")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
