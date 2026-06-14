import json
import re
from typing import Optional
from ..core.config import settings
from ..core.models import ContentItem

TAG_TAXONOMY = {
    "Technology": [
        "Python", "JavaScript", "Rust", "TypeScript", "Go",
        "Docker", "Kubernetes", "AWS", "GCP", "Azure",
    ],
    "Framework": [
        "LangChain", "LangGraph", "LlamaIndex", "Haystack",
        "PyTorch", "TensorFlow", "JAX", "FastAPI",
        "React", "Next.js", "Vue", "Django", "Flask",
    ],
    "Company": [
        "OpenAI", "Anthropic", "Google", "Meta", "Microsoft",
        "Apple", "Amazon", "NVIDIA", "IBM", "Intel", "AMD", "HuggingFace",
    ],
    "Domain": [
        "Healthcare", "Finance", "Legal", "Education",
        "Manufacturing", "Retail", "Energy", "Agriculture", "Transportation",
    ],
    "ContentType": [
        "Tutorial", "Research", "News", "Opinion",
        "Case Study", "Review", "Comparison", "Interview",
    ],
}


def _keyword_match(text: str, term: str) -> bool:
    pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
    return bool(pattern.search(text))


def _llm_enrich_tags(text: str, existing_tags: dict[str, list[str]]) -> dict[str, list[str]]:
    provider = settings.LLM_PROVIDER
    if provider == "none" or (not settings.OPENAI_API_KEY and not settings.ANTHROPIC_API_KEY and provider != "ollama"):
        return existing_tags

    flat_terms = []
    for category, terms in TAG_TAXONOMY.items():
        flat_terms.extend(terms)

    prompt = (
        "From the following content, identify which of these tags apply.\n"
        f"Available tags: {', '.join(flat_terms)}\n"
        "Return a JSON object with categories as keys and lists of matching tags as values. "
        "Only include tags that are clearly relevant.\n\n"
        f"CONTENT:\n{text[:4000]}"
    )

    try:
        if provider == "openai" and settings.OPENAI_API_KEY:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            result = resp.choices[0].message.content
        elif provider == "anthropic" and settings.ANTHROPIC_API_KEY:
            from anthropic import Anthropic
            client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            resp = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt + "\n\nRespond with valid JSON only."}],
            )
            result = resp.content[0].text
        elif provider == "ollama":
            import requests
            resp = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": "llama3", "prompt": prompt, "stream": False},
                timeout=60,
            )
            result = resp.json().get("response", "{}") if resp.ok else "{}"
        else:
            return existing_tags

        result = re.sub(r'^```(?:json)?\s*|\s*```$', '', result.strip())
        llm_tags = json.loads(result)
        for category, tags in llm_tags.items():
            if category in existing_tags:
                merged = set(existing_tags[category] + tags)
                existing_tags[category] = sorted(merged)
            elif isinstance(tags, list):
                existing_tags[category] = tags
    except Exception as e:
        print(f"  [Tagger] LLM enrichment error: {e}")

    return existing_tags


def auto_tag(item: ContentItem) -> dict[str, list[str]]:
    text = f"{item.title}\n{item.content_cleaned or item.content}"

    tags: dict[str, list[str]] = {}
    for category, terms in TAG_TAXONOMY.items():
        matched = []
        for term in terms:
            if _keyword_match(text, term):
                matched.append(term)
        if matched:
            tags[category] = matched

    tags = _llm_enrich_tags(text, tags)

    flat_tags = []
    for category_terms in tags.values():
        flat_tags.extend(category_terms)

    item.topics = list(set(item.topics + flat_tags))
    item.metadata["tags"] = tags
    item.metadata["tagging_method"] = "keyword" if not tags else "hybrid"

    return tags


def extract_entities(text: str) -> list[dict]:
    entities = []

    url_pattern = re.compile(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*', re.IGNORECASE)
    for m in url_pattern.finditer(text):
        entities.append({"type": "URL", "value": m.group()})

    email_pattern = re.compile(r'\b[\w.+-]+@[\w-]+\.[\w.-]+\b')
    for m in email_pattern.finditer(text):
        entities.append({"type": "Email", "value": m.group()})

    known_pattern = re.compile(r'\b(?:' + '|'.join(
        re.escape(t) for terms in TAG_TAXONOMY.values() for t in terms
    ) + r')\b', re.IGNORECASE)
    seen_known = set()
    for m in known_pattern.finditer(text):
        val = m.group()
        if val.lower() not in seen_known:
            seen_known.add(val.lower())
            category = None
            for cat, terms in TAG_TAXONOMY.items():
                if any(t.lower() == val.lower() for t in terms):
                    category = cat
                    break
            entities.append({"type": category or "KnownEntity", "value": val})

    cap_pattern = re.compile(r'\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b')
    seen_cap = set()
    for m in cap_pattern.finditer(text):
        val = m.group()
        if val.lower() not in seen_known and len(val) > 2 and val.lower() not in seen_cap:
            seen_cap.add(val.lower())
            entities.append({"type": "ProperNoun", "value": val})

    return entities


def tag_items(items: list[ContentItem]) -> list[dict]:
    results = []
    for item in items:
        tags = auto_tag(item)
        results.append({
            "id": item.id,
            "title": item.title,
            "tags": tags,
            "entities": extract_entities(item.content_cleaned or item.content),
        })
    return results
