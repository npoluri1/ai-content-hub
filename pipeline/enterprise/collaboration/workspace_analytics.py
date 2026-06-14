import sqlite3
import os
import json
from datetime import datetime, timedelta, timezone
from collections import Counter
from typing import Optional


class WorkspaceAnalytics:
    def __init__(self, sql_store=None, activity_feed=None, workspaces_db: str = "./data/workspaces.db"):
        self.sql_store = sql_store
        self.activity_feed = activity_feed
        self.db_path = workspaces_db
        os.makedirs(os.path.dirname(workspaces_db) if os.path.dirname(workspaces_db) else ".", exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workspace_cache (
                    workspace_id TEXT,
                    metric TEXT,
                    value TEXT,
                    computed_at TEXT DEFAULT (datetime('now')),
                    PRIMARY KEY (workspace_id, metric)
                )
            """)

    def get_overview(self, workspace_id: str, days: int = 30) -> dict:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        total_items = 0
        unique_sources = set()
        topics = Counter()
        active_members = set()
        items_added = 0
        top_sources = []
        top_topics = []

        if self.activity_feed:
            added_entries = self.activity_feed.get_feed(
                workspace_id, limit=5000, actions=["content_added"]
            )
            for entry in added_entries:
                if entry.get("timestamp", "") >= since:
                    items_added += 1
                    if entry.get("actor"):
                        active_members.add(entry["actor"])

            summary = self.activity_feed.get_workspace_summary(workspace_id, days)
            active_count = summary.get("unique_actors", 0)

        if self.sql_store and hasattr(self.sql_store, "get_workspace_items"):
            items = self.sql_store.get_workspace_items(workspace_id)
            total_items = len(items)
            for item in items:
                if item.get("source"):
                    unique_sources.add(item["source"])
                if item.get("topic"):
                    topics[item["topic"]] += 1
                if item.get("added_by"):
                    active_members.add(item["added_by"])

            source_counts = Counter()
            for item in items:
                if item.get("source"):
                    source_counts[item["source"]] += 1
            top_sources = [{"source": s, "count": c} for s, c in source_counts.most_common(10)]
            top_topics = [{"topic": t, "count": c} for t, c in topics.most_common(10)]

        active_count = max(active_count, len(active_members))
        items_per_day_avg = round(items_added / max(days, 1), 2)

        return {
            "workspace_id": workspace_id,
            "period_days": days,
            "total_items": total_items,
            "unique_sources": len(unique_sources),
            "topics_covered": len(topics),
            "active_members": active_count,
            "items_added": items_added,
            "items_per_day_avg": items_per_day_avg,
            "top_sources": top_sources,
            "top_topics": top_topics
        }

    def get_content_growth(self, workspace_id: str, days: int = 30) -> list[dict]:
        since = (datetime.now(timezone.utc) - timedelta(days=days))
        date_counts = Counter()

        if self.activity_feed:
            feed = self.activity_feed.get_feed(
                workspace_id, limit=5000, actions=["content_added"]
            )
            for entry in feed:
                try:
                    ts = datetime.fromisoformat(entry["timestamp"])
                    if ts >= since:
                        date_counts[ts.strftime("%Y-%m-%d")] += 1
                except (ValueError, TypeError):
                    continue

        result = []
        for i in range(days):
            day = (since + timedelta(days=i)).strftime("%Y-%m-%d")
            result.append({"date": day, "count": date_counts.get(day, 0)})
        return result

    def get_source_breakdown(self, workspace_id: str) -> list[dict]:
        if not (self.sql_store and hasattr(self.sql_store, "get_workspace_items")):
            return []

        items = self.sql_store.get_workspace_items(workspace_id)
        source_counts = Counter()
        for item in items:
            if item.get("source"):
                source_counts[item["source"]] += 1

        total = sum(source_counts.values()) or 1
        return [
            {"source": s, "count": c, "percentage": round(c / total * 100, 1)}
            for s, c in source_counts.most_common()
        ]

    def get_topic_breakdown(self, workspace_id: str) -> list[dict]:
        if not (self.sql_store and hasattr(self.sql_store, "get_workspace_items")):
            return []

        items = self.sql_store.get_workspace_items(workspace_id)
        topic_counts = Counter()
        for item in items:
            if item.get("topic"):
                topic_counts[item["topic"]] += 1

        total = sum(topic_counts.values()) or 1
        return [
            {"topic": t, "count": c, "percentage": round(c / total * 100, 1)}
            for t, c in topic_counts.most_common()
        ]

    def get_member_activity(self, workspace_id: str, days: int = 30) -> list[dict]:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        member_counts = Counter()

        if self.activity_feed:
            feed = self.activity_feed.get_feed(workspace_id, limit=5000)
            for entry in feed:
                if entry["timestamp"] >= since:
                    member_counts[entry["actor"]] += 1

        total = sum(member_counts.values()) or 1
        return [
            {"member": m, "activity_count": c, "percentage": round(c / total * 100, 1)}
            for m, c in member_counts.most_common()
        ]

    def get_engagement_metrics(self, workspace_id: str, days: int = 30) -> dict:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        counts = {"comments": 0, "shares": 0, "reactions": 0}
        content_ids = set()

        if self.activity_feed:
            feed = self.activity_feed.get_feed(workspace_id, limit=5000)
            for entry in feed:
                if entry["timestamp"] < since:
                    continue
                if entry["action"] == "comment_added":
                    counts["comments"] += 1
                    if entry["target_id"]:
                        content_ids.add(entry["target_id"])
                elif entry["action"] == "content_added":
                    if entry["target_id"]:
                        content_ids.add(entry["target_id"])

        num_items = len(content_ids) or 1
        return {
            "workspace_id": workspace_id,
            "period_days": days,
            "total_comments": counts["comments"],
            "total_shares": counts["shares"],
            "total_reactions": counts["reactions"],
            "comments_per_item": round(counts["comments"] / num_items, 2),
            "shares_per_item": round(counts["shares"] / num_items, 2),
            "reactions_per_item": round(counts["reactions"] / num_items, 2)
        }

    def get_workspace_comparison(
        self,
        workspace_ids: list[str],
        metric: str = "items_added",
        days: int = 30
    ) -> dict:
        results = {}
        for ws_id in workspace_ids:
            overview = self.get_overview(ws_id, days)
            if metric == "items_added":
                results[ws_id] = overview.get("items_added", 0)
            elif metric == "active_members":
                results[ws_id] = overview.get("active_members", 0)
            elif metric == "unique_sources":
                results[ws_id] = overview.get("unique_sources", 0)
            elif metric == "total_items":
                results[ws_id] = overview.get("total_items", 0)
            else:
                results[ws_id] = overview.get(metric, 0)

        return {
            "metric": metric,
            "period_days": days,
            "workspaces": results,
            "top_workspace": max(results, key=results.get) if results else None,
            "average": round(sum(results.values()) / len(results), 2) if results else 0
        }

    def get_top_contributors(
        self,
        workspace_id: str,
        limit: int = 10,
        days: int = 30
    ) -> list[dict]:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        member_data = Counter()
        member_items = Counter()

        if self.activity_feed:
            feed = self.activity_feed.get_feed(workspace_id, limit=5000)
            for entry in feed:
                if entry["timestamp"] >= since:
                    member_data[entry["actor"]] += 1
                    if entry["action"] == "content_added":
                        member_items[entry["actor"]] += 1

        result = []
        for member, count in member_data.most_common(limit):
            result.append({
                "member": member,
                "total_actions": count,
                "items_added": member_items.get(member, 0)
            })
        return result

    def get_weekly_report(self, workspace_id: str) -> str:
        overview = self.get_overview(workspace_id, 7)
        growth = self.get_content_growth(workspace_id, 7)
        top_contribs = self.get_top_contributors(workspace_id, 5, 7)
        engagement = self.get_engagement_metrics(workspace_id, 7)
        source_breakdown = self.get_source_breakdown(workspace_id)
        topic_breakdown = self.get_topic_breakdown(workspace_id)

        growth_str = "\n".join(f"  - {g['date']}: {g['count']} items" for g in growth if g["count"] > 0)
        contrib_str = "\n".join(
            f"  - {c['member']}: {c['total_actions']} actions ({c['items_added']} items added)"
            for c in top_contribs
        )
        source_str = "\n".join(f"  - {s['source']}: {s['count']} ({s.get('percentage', 0)}%)" for s in source_breakdown[:5])
        topic_str = "\n".join(f"  - {t['topic']}: {t['count']} ({t.get('percentage', 0)}%)" for t in topic_breakdown[:5])

        return f"""# Weekly Report: {workspace_id}
**Period:** Last 7 days

## Overview
- Total Items: {overview['total_items']}
- Items Added (7d): {overview['items_added']}
- Active Members: {overview['active_members']}
- Unique Sources: {overview['unique_sources']}
- Topics Covered: {overview['topics_covered']}
- Avg Items/Day: {overview['items_per_day_avg']}

## Content Growth
{growth_str or '  (no new content)'}

## Top Contributors
{contrib_str or '  (no activity)'}

## Engagement Metrics
- Comments: {engagement['total_comments']}
- Shares: {engagement['total_shares']}
- Reactions: {engagement['total_reactions']}
- Comments/Item: {engagement['comments_per_item']}

## Source Breakdown
{source_str or '  (no source data)'}

## Topic Breakdown
{topic_str or '  (no topic data)'}

## Top Sources
{', '.join(s['source'] for s in overview['top_sources'][:5]) or 'N/A'}

## Top Topics
{', '.join(t['topic'] for t in overview['top_topics'][:5]) or 'N/A'}
"""

    def export_workspace_data(self, workspace_id: str, format: str = "json") -> str:
        data = {
            "workspace_id": workspace_id,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "overview": self.get_overview(workspace_id, 30),
            "growth": self.get_content_growth(workspace_id, 30),
            "sources": self.get_source_breakdown(workspace_id),
            "topics": self.get_topic_breakdown(workspace_id),
            "engagement": self.get_engagement_metrics(workspace_id, 30),
            "top_contributors": self.get_top_contributors(workspace_id, 10, 30)
        }

        if format == "json":
            return json.dumps(data, indent=2)
        elif format == "markdown":
            return self.get_weekly_report(workspace_id)
        else:
            raise ValueError(f"Unsupported format: {format}")
