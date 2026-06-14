from ..core.config import settings
from ..core.models import ContentItem, ClassifiedItem
from typing import Optional
from datetime import datetime, timedelta
from ..storage.sql_store import SQLStore
import json
import os
import csv


def _ensure_dir(path: str):
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)


def _to_dicts(items: list[ContentItem | dict]) -> list[dict]:
    return [item.model_dump() if hasattr(item, "model_dump") else dict(item) for item in items]


def _default_output_path(prefix: str, ext: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(settings.DATA_DIR, "exports", f"{prefix}_{ts}.{ext}")


def export_to_csv(items: list[ContentItem | dict], output_path: str = None) -> str:
    if output_path is None:
        output_path = _default_output_path("export", "csv")
    _ensure_dir(output_path)
    dicts = _to_dicts(items)
    if not dicts:
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            f.write("")
        return os.path.abspath(output_path)
    fieldnames = list(dicts[0].keys())
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for d in dicts:
            row = {}
            for k, v in d.items():
                if isinstance(v, (list, dict)):
                    row[k] = json.dumps(v, ensure_ascii=False)
                elif isinstance(v, datetime):
                    row[k] = v.isoformat()
                else:
                    row[k] = v
            writer.writerow(row)
    return os.path.abspath(output_path)


def export_to_json(items: list[ContentItem | dict], output_path: str = None) -> str:
    if output_path is None:
        output_path = _default_output_path("export", "json")
    _ensure_dir(output_path)
    dicts = _to_dicts(items)
    for d in dicts:
        for k, v in d.items():
            if isinstance(v, datetime):
                d[k] = v.isoformat()
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dicts, f, indent=2, ensure_ascii=False, default=str)
    return os.path.abspath(output_path)


def export_to_markdown(
    items: list[ContentItem | dict],
    output_path: str = None,
    include_content: bool = False,
) -> str:
    if output_path is None:
        output_path = _default_output_path("export", "md")
    _ensure_dir(output_path)
    dicts = _to_dicts(items)
    lines = [f"# AI Content Export — {datetime.now().strftime('%Y-%m-%d %H:%M')}", "", f"**Total items:** {len(dicts)}", ""]
    for i, item in enumerate(dicts, 1):
        title = item.get("title", "Untitled")
        source = item.get("source", "unknown")
        author = item.get("author_name", item.get("author", "unknown"))
        url = item.get("url", "")
        published = item.get("published_at", "")
        if isinstance(published, datetime):
            published = published.strftime("%Y-%m-%d")
        topics = item.get("topics", [])
        if isinstance(topics, (list, tuple)):
            topics = ", ".join(topics)
        engagement = item.get("engagement", 0)
        lines.append(f"## {i}. {title}")
        lines.append(f"**Source:** {source} | **Author:** {author} | **Date:** {published}")
        if topics:
            lines.append(f"**Topics:** {topics}")
        lines.append(f"**Engagement:** {engagement}")
        if url:
            lines.append(f"**URL:** {url}")
        if include_content:
            content = item.get("content_cleaned") or item.get("content", "")
            if content:
                lines.append("")
                lines.append(content)
        lines.append("")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return os.path.abspath(output_path)


def export_digest(
    items: list[ContentItem],
    topic: str = None,
    format: str = "markdown",
) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    label = topic.replace(" ", "_") if topic else "all"
    if format == "csv":
        path = os.path.join(settings.DATA_DIR, "exports", f"digest_{label}_{ts}.csv")
        return export_to_csv(items, path)
    elif format == "json":
        path = os.path.join(settings.DATA_DIR, "exports", f"digest_{label}_{ts}.json")
        return export_to_json(items, path)
    else:
        path = os.path.join(settings.DATA_DIR, "exports", f"digest_{label}_{ts}.md")
        return export_to_markdown(items, path, include_content=False)


def export_source_report(source: str, days: int = 7, format: str = "json") -> str:
    store = SQLStore()
    rows = store.get_by_source(source, limit=500)
    items = [ContentItem(**r) if isinstance(r, dict) else r for r in rows]
    cutoff = datetime.now() - timedelta(days=days)
    items = [it for it in items if it.published_at is None or it.published_at >= cutoff]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if format == "csv":
        path = os.path.join(settings.DATA_DIR, "exports", f"source_{source}_{ts}.csv")
        return export_to_csv(items, path)
    elif format == "markdown":
        path = os.path.join(settings.DATA_DIR, "exports", f"source_{source}_{ts}.md")
        return export_to_markdown(items, path, include_content=False)
    else:
        path = os.path.join(settings.DATA_DIR, "exports", f"source_{source}_{ts}.json")
        return export_to_json(items, path)


def export_topic_report(topic: str, days: int = 7, format: str = "json") -> str:
    store = SQLStore()
    rows = store.get_by_topic(topic, limit=500)
    items = [ContentItem(**r) if isinstance(r, dict) else r for r in rows]
    cutoff = datetime.now() - timedelta(days=days)
    items = [it for it in items if it.published_at is None or it.published_at >= cutoff]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    label = topic.replace(" ", "_")
    if format == "csv":
        path = os.path.join(settings.DATA_DIR, "exports", f"topic_{label}_{ts}.csv")
        return export_to_csv(items, path)
    elif format == "markdown":
        path = os.path.join(settings.DATA_DIR, "exports", f"topic_{label}_{ts}.md")
        return export_to_markdown(items, path, include_content=False)
    else:
        path = os.path.join(settings.DATA_DIR, "exports", f"topic_{label}_{ts}.json")
        return export_to_json(items, path)
