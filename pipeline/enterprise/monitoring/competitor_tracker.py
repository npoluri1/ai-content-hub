import sqlite3
import json
import uuid
import re
from datetime import datetime, timedelta
from collections import defaultdict

from .alerts import ContentItem


class CompetitorTracker:
    def __init__(self, sql_store=None):
        self.sql_store = sql_store
        self._conn = sqlite3.connect(":memory:")
        self._init_db()

    def _init_db(self):
        c = self._conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS competitors (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                domains TEXT,
                linkedin_urls TEXT,
                twitter_handles TEXT,
                keywords TEXT,
                notes TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS competitor_mentions (
                id TEXT PRIMARY KEY,
                competitor_id TEXT NOT NULL,
                content_id TEXT,
                title TEXT,
                content TEXT,
                source TEXT,
                url TEXT,
                published_at TEXT,
                sentiment REAL DEFAULT 0.0,
                engagement INTEGER DEFAULT 0,
                mentioned_at TEXT,
                FOREIGN KEY (competitor_id) REFERENCES competitors(id)
            )
        """)
        self._conn.commit()

    def _now(self):
        return datetime.utcnow().isoformat()

    def _row_to_competitor(self, row):
        return {
            "id": row[0],
            "name": row[1],
            "domains": json.loads(row[2]) if row[2] else [],
            "linkedin_urls": json.loads(row[3]) if row[3] else [],
            "twitter_handles": json.loads(row[4]) if row[4] else [],
            "keywords": json.loads(row[5]) if row[5] else [],
            "notes": row[6],
            "created_at": row[7],
            "updated_at": row[8],
        }

    def _row_to_mention(self, row):
        return {
            "id": row[0],
            "competitor_id": row[1],
            "content_id": row[2],
            "title": row[3],
            "content": row[4],
            "source": row[5],
            "url": row[6],
            "published_at": row[7],
            "sentiment": row[8],
            "engagement": row[9],
            "mentioned_at": row[10],
        }

    def add_competitor(self, name, domains, linkedin_urls=None, twitter_handles=None, keywords=None, notes=None):
        competitor_id = str(uuid.uuid4())
        now = self._now()
        c = self._conn.cursor()
        c.execute(
            "INSERT INTO competitors (id, name, domains, linkedin_urls, twitter_handles, keywords, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (competitor_id, name, json.dumps(domains), json.dumps(linkedin_urls or []), json.dumps(twitter_handles or []), json.dumps(keywords or []), notes, now, now)
        )
        self._conn.commit()
        c.execute("SELECT * FROM competitors WHERE id = ?", (competitor_id,))
        return self._row_to_competitor(c.fetchone())

    def remove_competitor(self, competitor_id):
        c = self._conn.cursor()
        c.execute("DELETE FROM competitors WHERE id = ?", (competitor_id,))
        c.execute("DELETE FROM competitor_mentions WHERE competitor_id = ?", (competitor_id,))
        self._conn.commit()
        return c.rowcount > 0

    def list_competitors(self):
        c = self._conn.cursor()
        c.execute("SELECT * FROM competitors ORDER BY name ASC")
        return [self._row_to_competitor(row) for row in c.fetchall()]

    def get_competitor_mentions(self, competitor_id, days=30, limit=100):
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        c = self._conn.cursor()
        c.execute(
            "SELECT * FROM competitor_mentions WHERE competitor_id = ? AND mentioned_at >= ? ORDER BY mentioned_at DESC LIMIT ?",
            (competitor_id, since, limit)
        )
        return [self._row_to_mention(row) for row in c.fetchall()]

    def get_competitor_summary(self, competitor_id, days=30):
        c = self._conn.cursor()
        c.execute("SELECT * FROM competitors WHERE id = ?", (competitor_id,))
        row = c.fetchone()
        if not row:
            return None
        comp = self._row_to_competitor(row)
        mentions = self.get_competitor_mentions(competitor_id, days=days)
        mention_count = len(mentions)
        sentiment_avg = 0.0
        engagement_total = 0
        top_sources = defaultdict(int)
        if mentions:
            sentiment_avg = sum(m["sentiment"] for m in mentions) / mention_count
            engagement_total = sum(m["engagement"] for m in mentions)
            for m in mentions:
                if m["source"]:
                    top_sources[m["source"]] += 1
        top_sources_list = sorted(top_sources.items(), key=lambda x: x[1], reverse=True)[:5]
        return {
            "name": comp["name"],
            "mention_count": mention_count,
            "sentiment_avg": round(sentiment_avg, 3),
            "top_sources": [{"source": s, "count": c2} for s, c2 in top_sources_list],
            "recent_mentions": mentions[:10],
            "engagement_total": engagement_total,
        }

    def get_all_summaries(self, days=30):
        competitors = self.list_competitors()
        summaries = []
        for comp in competitors:
            summary = self.get_competitor_summary(comp["id"], days=days)
            if summary:
                summaries.append(summary)
        return summaries

    def _match_domain(self, text, domains):
        if not text or not domains:
            return False
        text_lower = text.lower()
        for domain in domains:
            d = domain.lower().strip()
            if d in text_lower:
                return True
            escaped = re.escape(d)
            if re.search(escaped, text_lower, re.IGNORECASE):
                return True
        return False

    def find_mentions(self, items):
        competitors = self.list_competitors()
        result = defaultdict(list)
        now = self._now()
        for item in items:
            text = f"{item.title} {item.content} {item.source} {item.url}"
            for comp in competitors:
                matched = False
                if self._match_domain(text, comp["domains"]):
                    matched = True
                if not matched and comp["keywords"]:
                    kw_match = any(kw.lower() in text.lower() for kw in comp["keywords"])
                    if kw_match:
                        matched = True
                if not matched and comp["linkedin_urls"]:
                    url_match = any(lu.lower() in text.lower() for lu in comp["linkedin_urls"])
                    if url_match:
                        matched = True
                if not matched and comp["twitter_handles"]:
                    handle_match = any(th.lower() in text.lower() for th in comp["twitter_handles"])
                    if handle_match:
                        matched = True
                if matched:
                    result[comp["id"]].append(item)
                    mention_id = str(uuid.uuid4())
                    c = self._conn.cursor()
                    c.execute(
                        "INSERT OR IGNORE INTO competitor_mentions (id, competitor_id, content_id, title, content, source, url, published_at, sentiment, engagement, mentioned_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (mention_id, comp["id"], item.id, item.title, item.content[:1000] if item.content else "", item.source, item.url, item.published_at or now, item.sentiment, item.engagement, now)
                    )
                    self._conn.commit()
        return dict(result)

    def generate_report(self, competitor_id, days=30, format="markdown"):
        summary = self.get_competitor_summary(competitor_id, days=days)
        if not summary:
            return ""
        if format == "markdown":
            lines = [
                f"# Competitive Intelligence Report: {summary['name']}",
                f"",
                f"**Period:** Last {days} days",
                f"**Total Mentions:** {summary['mention_count']}",
                f"**Average Sentiment:** {summary['sentiment_avg']}",
                f"**Total Engagement:** {summary['engagement_total']}",
                f"",
                f"## Top Sources",
            ]
            for s in summary["top_sources"]:
                lines.append(f"- {s['source']}: {s['count']} mentions")
            lines.append("")
            lines.append("## Recent Mentions")
            for m in summary["recent_mentions"]:
                lines.append(f"- [{m['title']}]({m['url'] or '#'}) | {m['source']} | Sentiment: {m['sentiment']}")
            return "\n".join(lines)
        elif format == "json":
            return json.dumps(summary, indent=2)
        elif format == "text":
            lines = [
                f"Competitive Intelligence Report: {summary['name']}",
                f"Period: Last {days} days",
                f"Mentions: {summary['mention_count']} | Avg Sentiment: {summary['sentiment_avg']} | Engagement: {summary['engagement_total']}",
            ]
            return "\n".join(lines)
        return str(summary)
