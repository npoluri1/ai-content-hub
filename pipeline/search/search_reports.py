"""Scheduled search reports and alerts — create, generate, send."""

from ..core.models import ContentItem
from .saved_searches import SavedSearch
from datetime import datetime, timedelta
import json
import os
import sqlite3
import uuid


class SearchReportManager:
    def __init__(self, saved_searches: 'SavedSearch' = None, db_path: str = "./data/search_reports.db"):
        self.saved_searches = saved_searches or SavedSearch()
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        self._init_db()

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS report_definitions (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    search_id TEXT NOT NULL,
                    schedule TEXT NOT NULL DEFAULT 'weekly',
                    recipients TEXT DEFAULT '[]',
                    format TEXT DEFAULT 'markdown',
                    channels TEXT DEFAULT '[]',
                    active INTEGER DEFAULT 1,
                    last_generated_at TEXT,
                    next_due_at TEXT,
                    created_at TEXT,
                    updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS report_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id TEXT NOT NULL,
                    generated_at TEXT,
                    content TEXT,
                    channels_sent TEXT DEFAULT '[]',
                    status TEXT DEFAULT 'generated',
                    error TEXT,
                    FOREIGN KEY (report_id) REFERENCES report_definitions(id)
                );
                CREATE INDEX IF NOT EXISTS idx_report_history_report ON report_history(report_id);
                CREATE INDEX IF NOT EXISTS idx_report_definitions_next ON report_definitions(next_due_at);
            """)

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def create_report(self, name: str, search_id: str, schedule: str = "weekly",
                      recipients: list[str] = None, format: str = "markdown",
                      channels: list[str] = None) -> str:
        report_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        next_due = self._compute_next_due(schedule)

        with self._conn() as conn:
            conn.execute("""
                INSERT INTO report_definitions
                (id, name, search_id, schedule, recipients, format, channels,
                 active, next_due_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
            """, (report_id, name, search_id, schedule,
                  json.dumps(recipients or []), format,
                  json.dumps(channels or []), next_due, now, now))
        return report_id

    def update_report(self, report_id: str, **kwargs) -> bool:
        allowed = {"name", "schedule", "recipients", "format", "channels", "active", "search_id"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False

        if "recipients" in updates and isinstance(updates["recipients"], list):
            updates["recipients"] = json.dumps(updates["recipients"])
        if "channels" in updates and isinstance(updates["channels"], list):
            updates["channels"] = json.dumps(updates["channels"])
        if "schedule" in updates:
            updates["next_due_at"] = self._compute_next_due(updates["schedule"])

        updates["updated_at"] = datetime.now().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [report_id]

        with self._conn() as conn:
            conn.execute(f"UPDATE report_definitions SET {set_clause} WHERE id = ?", values)
            return conn.rowcount > 0

    def delete_report(self, report_id: str) -> bool:
        with self._conn() as conn:
            conn.execute("DELETE FROM report_definitions WHERE id = ?", (report_id,))
            conn.execute("DELETE FROM report_history WHERE report_id = ?", (report_id,))
            return conn.rowcount > 0

    def list_reports(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT * FROM report_definitions
                ORDER BY created_at DESC
            """).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def generate(self, report_id: str) -> str:
        report = self._get_by_id(report_id)
        if not report:
            return ""

        search_results = self.saved_searches.execute(report["search_id"])
        content = self._build_report_content(search_results, report.get("format", "markdown"))

        now = datetime.now().isoformat()
        next_due = self._compute_next_due(report["schedule"])

        with self._conn() as conn:
            conn.execute(
                "UPDATE report_definitions SET last_generated_at = ?, next_due_at = ? WHERE id = ?",
                (now, next_due, report_id)
            )
            conn.execute("""
                INSERT INTO report_history (report_id, generated_at, content, status)
                VALUES (?, ?, ?, 'generated')
            """, (report_id, now, content[:50000] if content else ""))

        return content

    def send(self, report_id: str, channels: list[str] = None) -> bool:
        report = self._get_by_id(report_id)
        if not report:
            return False

        content = self.generate(report_id)
        if not content:
            return False

        channels = channels or json.loads(report.get("channels", "[]"))
        recipients = json.loads(report.get("recipients", "[]"))

        sent_channels = []
        all_success = True

        for channel in channels:
            for recipient in recipients:
                success = self._send_via_channel(content, channel, recipient)
                if success:
                    sent_channels.append(f"{channel}:{recipient}")
                else:
                    all_success = False

        status = "sent" if all_success else "partial"
        with self._conn() as conn:
            conn.execute("""
                UPDATE report_history SET channels_sent = ?, status = ?
                WHERE report_id = ? AND generated_at = (
                    SELECT MAX(generated_at) FROM report_history WHERE report_id = ?
                )
            """, (json.dumps(sent_channels), status, report_id, report_id))

        return all_success

    def generate_all_due(self) -> int:
        now = datetime.now().isoformat()
        with self._conn() as conn:
            due = conn.execute("""
                SELECT * FROM report_definitions
                WHERE active = 1 AND next_due_at IS NOT NULL AND next_due_at <= ?
                ORDER BY next_due_at ASC
            """, (now,)).fetchall()

        count = 0
        for row in due:
            report = self._row_to_dict(row)
            try:
                content = self.generate(report["id"])
                if content:
                    channels = json.loads(report.get("channels", "[]"))
                    recipients = json.loads(report.get("recipients", "[]"))
                    for channel in channels:
                        for recipient in recipients:
                            self._send_via_channel(content, channel, recipient)
                    count += 1
            except Exception:
                pass
        return count

    def get_report_history(self, report_id: str, limit: int = 20) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT id, report_id, generated_at, channels_sent, status, error
                FROM report_history
                WHERE report_id = ?
                ORDER BY generated_at DESC
                LIMIT ?
            """, (report_id, limit)).fetchall()
        return [
            {
                "id": r[0],
                "report_id": r[1],
                "generated_at": r[2],
                "channels_sent": json.loads(r[3]) if r[3] else [],
                "status": r[4],
                "error": r[5],
            }
            for r in rows
        ]

    def _build_report_content(self, search_results: dict, format: str = "markdown") -> str:
        if format == "json":
            return json.dumps(search_results, indent=2, default=str)

        results = search_results.get("results", [])
        total = search_results.get("total", len(results))
        name = search_results.get("saved_search_name", "Search Report")
        query = search_results.get("query", "")

        lines = [
            f"# {name}",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Total Results: {total}",
            "",
        ]
        if query:
            lines.append(f"Query: {query}")
            lines.append("")

        lines.append(f"## Results ({len(results)} items)")
        lines.append("")

        for i, item in enumerate(results[:50], 1):
            title = item.get("title", "Untitled")
            url = item.get("url", "")
            source = item.get("source", "")
            author = item.get("author", "")
            published = item.get("published_at", "")
            topics = item.get("topics", [])
            engagement = item.get("engagement", 0)

            lines.append(f"### {i}. {title}")
            if url:
                lines.append(f"URL: {url}")
            source_parts = []
            if source:
                source_parts.append(f"Source: {source}")
            if author:
                source_parts.append(f"Author: {author}")
            if published:
                try:
                    d = datetime.fromisoformat(published.replace("Z", "+00:00").split(".")[0])
                    source_parts.append(f"Published: {d.strftime('%Y-%m-%d')}")
                except (ValueError, TypeError):
                    source_parts.append(f"Published: {published}")
            if engagement:
                source_parts.append(f"Engagement: {engagement}")
            if source_parts:
                lines.append(" | ".join(source_parts))
            if topics:
                topics_str = ", ".join(topics) if isinstance(topics, list) else str(topics)
                lines.append(f"Topics: {topics_str}")
            lines.append("")

        lines.append("---")
        lines.append(f"Report generated by LinkedIn AI TechStack Content Pipeline")
        return "\n".join(lines)

    def _send_via_channel(self, content: str, channel: str, recipient: str) -> bool:
        try:
            if channel == "slack":
                return self._send_slack(content, recipient)
            elif channel == "email":
                return self._send_email(content, recipient)
            elif channel == "telegram":
                return self._send_telegram(content, recipient)
            elif channel == "webhook":
                return self._send_webhook(content, recipient)
            elif channel == "file":
                return self._send_file(content, recipient)
            return False
        except Exception as e:
            with self._conn() as conn:
                conn.execute("""
                    UPDATE report_history SET status = 'failed', error = ?
                    WHERE id = (SELECT MAX(id) FROM report_history WHERE status = 'generated')
                """, (str(e),))
            return False

    def _send_slack(self, content: str, webhook_url: str) -> bool:
        import urllib.request
        data = json.dumps({"text": content[:4000]}).encode("utf-8")
        req = urllib.request.Request(webhook_url, data=data,
                                     headers={"Content-Type": "application/json"},
                                     method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200

    def _send_email(self, content: str, recipient: str) -> bool:
        try:
            import smtplib
            from email.mime.text import MIMEText
            msg = MIMEText(content, "plain")
            msg["Subject"] = f"Search Report - {datetime.now().strftime('%Y-%m-%d')}"
            msg["To"] = recipient
            msg["From"] = "reports@example.com"
            with smtplib.SMTP("localhost", 25, timeout=10) as server:
                server.send_message(msg)
            return True
        except Exception:
            return False

    def _send_telegram(self, content: str, chat_id: str) -> bool:
        import urllib.request
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        if not token:
            return False
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = json.dumps({"chat_id": chat_id, "text": content[:4096]}).encode("utf-8")
        req = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/json"},
                                     method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200

    def _send_webhook(self, content: str, url: str) -> bool:
        import urllib.request
        data = json.dumps({"content": content, "type": "search_report",
                           "generated_at": datetime.now().isoformat()}).encode("utf-8")
        req = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/json"},
                                     method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200

    def _send_file(self, content: str, filepath: str) -> bool:
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return os.path.exists(filepath)

    def _compute_next_due(self, schedule: str) -> str:
        now = datetime.now()
        schedule = schedule.strip().lower()

        if schedule == "hourly":
            next_due = now + timedelta(hours=1)
        elif schedule == "daily":
            next_due = now + timedelta(days=1)
        elif schedule == "weekly":
            next_due = now + timedelta(weeks=1)
        elif schedule == "monthly":
            next_due = now + timedelta(days=30)
        elif schedule.startswith("*/") or schedule.startswith("0 ") or len(schedule.split()) >= 5:
            try:
                from croniter import croniter
                next_due = croniter(schedule, now).get_next(datetime)
            except ImportError:
                next_due = now + timedelta(days=1)
        else:
            next_due = now + timedelta(days=1)
        return next_due.isoformat()

    def _get_by_id(self, report_id: str) -> dict:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM report_definitions WHERE id = ?", (report_id,)
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        keys = ["id", "name", "search_id", "schedule", "recipients", "format",
                "channels", "active", "last_generated_at", "next_due_at",
                "created_at", "updated_at"]
        d = {}
        for i, k in enumerate(keys):
            d[k] = row[i] if i < len(row) else None
        d["active"] = bool(d.get("active", 1))
        return d
