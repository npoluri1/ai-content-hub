"""Multi-source orchestrator — runs all enabled collectors through the pipeline."""

from ..core.config import settings
from ..core.models import ContentItem, ClassifiedItem, DigestConfig
from ..sources import get_enabled_collectors
from .classifier import classify_item
from ..storage.vector_store import VectorStore
from ..storage.sql_store import SQLStore
from datetime import datetime
from typing import Optional


class ContentOrchestrator:
    def __init__(self):
        self.vector_store = VectorStore()
        self.sql_store = SQLStore()

    def run_all(self, sources: Optional[list[str]] = None) -> dict[str, int]:
        if sources:
            collectors = []
            for s in sources:
                from ..sources import get_collector
                collectors.append(get_collector(s))
        else:
            enabled = settings.SOURCES_ENABLED.split(",")
            collectors = get_enabled_collectors(enabled)

        results = {}
        all_items: list[ContentItem] = []

        for collector in collectors:
            src_name = collector.name
            print(f"  [{src_name}] Collecting...")
            try:
                items = collector.collect(max_items=100)
                print(f"  [{src_name}] Got {len(items)} items")
                results[src_name] = len(items)
                all_items.extend(items)
            except Exception as e:
                print(f"  [{src_name}] Failed: {e}")
                results[src_name] = 0

        if not all_items:
            print("  No items collected from any source.")
            return results

        # Classify
        print(f"\n  Classifying {len(all_items)} items...")
        classified: list[ClassifiedItem] = []
        for item in all_items:
            classified.append(classify_item(item))

        relevant = [c for c in classified if c.is_relevant]
        print(f"  Relevant: {len(relevant)}/{len(classified)}")

        # Store
        print("  Storing in ChromaDB...")
        self.vector_store.store_items(classified)
        print(f"  Total in vector store: {self.vector_store.count()}")

        print("  Storing in SQLite...")
        self.sql_store.store_items(classified)
        print(f"  Total in SQL: {self.sql_store.count()}")

        # Generate digest
        topics = [t.strip() for t in settings.DIGEST_TOPICS.split(",")]
        digest = self._generate_digest(relevant, topics)
        self._save_digest(digest)

        results["_total"] = len(all_items)
        results["_relevant"] = len(relevant)
        return results

    def run_source(self, source: str) -> list[ContentItem]:
        from ..sources import get_collector
        collector = get_collector(source)
        items = collector.collect(max_items=100)
        classified = [classify_item(item) for item in items]
        relevant = [c for c in classified if c.is_relevant]
        self.vector_store.store_items(classified)
        self.sql_store.store_items(classified)
        return items

    def _generate_digest(self, items: list[ClassifiedItem], topics: list[str]) -> str:
        lines = [f"# AI Content Hub Digest", f"**Generated:** {datetime.now().isoformat()}", f"**Sources:** {settings.SOURCES_ENABLED}", f"**Total Items:** {len(items)}", ""]
        for topic in topics:
            topic_items = [i for i in items if topic in i.topics][:10]
            if not topic_items:
                continue
            lines.append(f"## {topic}")
            for item in topic_items:
                snippet = item.content_cleaned[:150].replace("\n", " ")
                source_tag = f"[{item.source.upper()}]"
                lines.append(f"- {source_tag} **{item.title}** — {snippet}...")
                if item.url:
                    lines.append(f"  {item.url}")
            lines.append("")
        return "\n".join(lines)

    def _save_digest(self, digest: str):
        import os
        out_dir = f"{settings.DATA_DIR}/digests"
        os.makedirs(out_dir, exist_ok=True)
        fname = f"{out_dir}/digest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(fname, "w", encoding="utf-8") as f:
            f.write(digest)
        print(f"  Digest saved: {fname}")
