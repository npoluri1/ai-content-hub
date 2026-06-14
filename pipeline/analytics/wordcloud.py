from ..core.config import settings
from ..core.models import ContentItem, ClassifiedItem
from typing import Optional
from datetime import datetime, timedelta
from ..storage.sql_store import SQLStore
from collections import Counter
import json
import os
import csv
import re
import warnings

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "by", "with", "from", "as", "is", "was", "are", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "can", "shall", "not",
    "no", "nor", "this", "that", "these", "those", "it", "its", "they",
    "them", "their", "we", "us", "our", "you", "your", "he", "she", "him",
    "her", "his", "my", "me", "who", "which", "what", "when", "where",
    "why", "how", "all", "each", "every", "both", "few", "more", "most",
    "other", "some", "such", "only", "own", "same", "so", "than", "too",
    "very", "just", "also", "about", "into", "over", "after", "before",
    "between", "under", "above", "below", "up", "down", "out", "off",
    "if", "then", "else", "like", "get", "got", "one", "two", "new",
    "use", "used", "using", "make", "made", "way", "also", "well", "back",
    "even", "much", "still", "yet", "because", "while", "since", "until",
    "now", "here", "there", "been", "being", "say", "said", "going",
    "goes", "went", "come", "came", "take", "took", "know", "known",
    "think", "thought", "see", "saw", "want", "wanted", "look", "looking",
    "first", "last", "long", "great", "many", "really", "another",
}


def _clean_text(text: str) -> list[str]:
    text = text.lower()
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    words = text.split()
    return [w for w in words if len(w) >= 3 and w not in STOPWORDS]


def _extract_texts(items: list[ContentItem]) -> list[str]:
    texts = []
    for item in items:
        texts.append(item.content_cleaned or item.content or item.title)
    return texts


def get_frequency_table(items: list[ContentItem], top_n: int = 50) -> list[dict]:
    word_counter: Counter = Counter()
    source_counter: Counter = Counter()
    seen_sources: dict[str, set] = {}
    for item in items:
        words = _clean_text(item.content_cleaned or item.content or item.title)
        unique_words = set(words)
        word_counter.update(words)
        for w in unique_words:
            if w not in seen_sources:
                seen_sources[w] = set()
            seen_sources[w].add(item.source)
    result = []
    for word, count in word_counter.most_common(top_n):
        result.append({
            "word": word,
            "count": count,
            "source_count": len(seen_sources.get(word, set())),
        })
    return result


def get_topic_keywords(topic: str, limit: int = 30) -> list[dict]:
    store = SQLStore()
    rows = store.get_by_topic(topic, limit=1000)
    items = [ContentItem(**r) if isinstance(r, dict) else r for r in rows]
    return get_frequency_table(items, top_n=limit)


def source_keywords(source: str, limit: int = 30) -> list[dict]:
    store = SQLStore()
    rows = store.get_by_source(source, limit=1000)
    items = [ContentItem(**r) if isinstance(r, dict) else r for r in rows]
    return get_frequency_table(items, top_n=limit)


def bigram_analysis(items: list[ContentItem], top_n: int = 20) -> list[dict]:
    bigram_counter: Counter = Counter()
    for item in items:
        words = _clean_text(item.content_cleaned or item.content or item.title)
        for i in range(len(words) - 1):
            bigram_counter[" ".join(words[i:i + 2])] += 1
    return [{"phrase": phrase, "count": count}
            for phrase, count in bigram_counter.most_common(top_n)]


def generate_wordcloud(
    items: list[ContentItem],
    title: str = "Content Word Cloud",
    output_path: str = None,
    width: int = 800,
    height: int = 400,
) -> str:
    try:
        from wordcloud import WordCloud
        import matplotlib.pyplot as plt
    except ImportError:
        warnings.warn("wordcloud library not installed. Returning frequency table instead.")
        return ""

    texts = _extract_texts(items)
    all_words = []
    for t in texts:
        all_words.extend(_clean_text(t))
    text = " ".join(all_words)

    if not text.strip():
        warnings.warn("No text available to generate word cloud.")
        return ""

    if output_path is None:
        output_path = os.path.join(settings.DATA_DIR, "analytics", "wordcloud.png")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    wc = WordCloud(
        width=width,
        height=height,
        background_color="white",
        max_words=200,
        stopwords=STOPWORDS,
        collocations=False,
    ).generate(text)

    plt.figure(figsize=(width / 100, height / 100))
    plt.imshow(wc, interpolation="bilinear")
    plt.axis("off")
    plt.title(title, fontsize=16)
    plt.tight_layout(pad=0)
    plt.savefig(output_path, dpi=100, bbox_inches="tight")
    plt.close()

    return os.path.abspath(output_path)
