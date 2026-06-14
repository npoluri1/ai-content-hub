import logging
from difflib import SequenceMatcher
from urllib.parse import urlparse, urlunparse

from ..core.models import ContentItem

logger = logging.getLogger(__name__)

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    logger.debug("sklearn not installed, falling back to title-based dedup")


class Deduplicator:
    def find_duplicates(self, items: list[ContentItem], threshold: float = 0.85) -> list[list[str]]:
        if not items:
            return []
        if not HAS_SKLEARN:
            logger.warning("sklearn not available, using title-based dedup instead")
            return self.find_title_duplicates(items, threshold=threshold - 0.05)

        texts = []
        valid_items = []
        for item in items:
            text = f"{item.title} {item.content_cleaned or item.content}"
            if text.strip():
                texts.append(text)
                valid_items.append(item)

        if len(texts) < 2:
            return []

        matrix = self._compute_tfidf(texts)
        sim_matrix = cosine_similarity(matrix)
        groups = []
        assigned = set()

        for i in range(len(valid_items)):
            if i in assigned:
                continue
            group = [valid_items[i].id]
            assigned.add(i)
            for j in range(i + 1, len(valid_items)):
                if j in assigned:
                    continue
                if sim_matrix[i][j] >= threshold:
                    group.append(valid_items[j].id)
                    assigned.add(j)
            if len(group) > 1:
                groups.append(group)

        return groups

    def find_url_duplicates(self, items: list[ContentItem]) -> list[list[str]]:
        url_map = {}
        for item in items:
            normalized = self._normalize_url(item.url)
            if normalized not in url_map:
                url_map[normalized] = []
            url_map[normalized].append(item.id)

        groups = []
        for ids in url_map.values():
            if len(ids) > 1:
                groups.append(ids)
        return groups

    def find_title_duplicates(self, items: list[ContentItem], threshold: float = 0.8) -> list[list[str]]:
        groups = []
        assigned = set()

        for i in range(len(items)):
            if i in assigned:
                continue
            group = [items[i].id]
            assigned.add(i)
            for j in range(i + 1, len(items)):
                if j in assigned:
                    continue
                ratio = SequenceMatcher(None, items[i].title.lower(), items[j].title.lower()).ratio()
                if ratio >= threshold:
                    group.append(items[j].id)
                    assigned.add(j)
            if len(group) > 1:
                groups.append(group)

        return groups

    def merge_duplicates(self, duplicate_groups: list[list[str]], items: dict[str, ContentItem]) -> list[ContentItem]:
        merged = []
        seen_ids = set()

        for group in duplicate_groups:
            group_items = [items[gid] for gid in group if gid in items]
            if not group_items:
                continue

            best = max(group_items, key=lambda x: (len(x.content_cleaned or x.content), x.engagement))
            seen_ids.add(best.id)

            for other in group_items:
                if other.id == best.id:
                    continue
                if other.title and not best.title:
                    best.title = other.title
                if other.content and not best.content:
                    best.content = other.content
                if other.content_cleaned and not best.content_cleaned:
                    best.content_cleaned = other.content_cleaned
                if other.published_at and (not best.published_at or other.published_at < best.published_at):
                    best.published_at = other.published_at
                if other.engagement > best.engagement:
                    best.engagement = other.engagement
                if other.hashtags:
                    best.hashtags = list(set(best.hashtags + other.hashtags))
                if other.topics:
                    best.topics = list(set(best.topics + other.topics))
                if other.author_name and not best.author_name:
                    best.author_name = other.author_name
                if other.image_urls:
                    best.image_urls = list(set(best.image_urls + other.image_urls))
                best.metadata.update(other.metadata)
                if "merged_from" not in best.metadata:
                    best.metadata["merged_from"] = []
                best.metadata["merged_from"].append(other.id)

            merged.append(best)

        for item in items.values():
            if item.id not in seen_ids:
                merged.append(item)

        return merged

    def deduplicate_and_merge(self, items: list[ContentItem]) -> list[ContentItem]:
        if not items:
            return []

        items_dict = {item.id: item for item in items}

        url_groups = self.find_url_duplicates(items)
        title_groups = self.find_title_duplicates(items)
        content_groups = self.find_duplicates(items)

        all_groups = url_groups + title_groups + content_groups
        merged_groups = self._merge_groups(all_groups)

        return self.merge_duplicates(merged_groups, items_dict)

    def _compute_tfidf(self, texts: list[str]):
        vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words="english",
            ngram_range=(1, 2),
            min_df=1,
        )
        return vectorizer.fit_transform(texts)

    def _normalize_url(self, url: str) -> str:
        if not url:
            return ""
        parsed = urlparse(url.lower().strip())
        hostname = parsed.hostname or ""
        if hostname.startswith("www."):
            hostname = hostname[4:]
        path = parsed.path.rstrip("/")
        query = parsed.query
        cleaned_query = "&".join(
            q for q in query.split("&") if q and not q.startswith(("utm_", "ref=", "source="))
        )
        return urlunparse(("", hostname, path, "", cleaned_query, ""))

    def _merge_groups(self, groups: list[list[str]]) -> list[list[str]]:
        if not groups:
            return []

        id_to_group = {}
        for group in groups:
            group_set = frozenset(group)
            for gid in group:
                if gid in id_to_group:
                    id_to_group[gid] = id_to_group[gid] | group_set
                else:
                    id_to_group[gid] = group_set

        merged = []
        visited = set()

        for gid, group_set in id_to_group.items():
            if gid in visited:
                continue
            current = set(group_set)
            changed = True
            while changed:
                changed = False
                for other_id in list(current):
                    if other_id in id_to_group:
                        before = len(current)
                        current |= id_to_group[other_id]
                        if len(current) > before:
                            changed = True
            visited |= current
            if len(current) > 1:
                merged.append(list(current))

        return merged
