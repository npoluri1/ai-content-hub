import sqlite3
import json
from datetime import datetime, timedelta
from collections import defaultdict


class MonitoringDashboard:
    def __init__(self, sql_store=None, sla_monitor=None, alert_engine=None):
        self.sql_store = sql_store
        self.sla_monitor = sla_monitor
        self.alert_engine = alert_engine
        self._conn = sqlite3.connect(":memory:")
        self._init_db()

    def _init_db(self):
        c = self._conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event TEXT NOT NULL,
                detail TEXT,
                severity TEXT DEFAULT 'info',
                source TEXT,
                created_at TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS perf_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collect_time_ms REAL,
                classify_time_ms REAL,
                store_time_ms REAL,
                items_processed INTEGER,
                error_count INTEGER,
                created_at TEXT
            )
        """)
        self._conn.commit()

    def _now(self):
        return datetime.utcnow().isoformat()

    def log_event(self, event, detail=None, severity="info", source=None):
        c = self._conn.cursor()
        c.execute(
            "INSERT INTO audit_log (event, detail, severity, source, created_at) VALUES (?, ?, ?, ?, ?)",
            (event, detail, severity, source, self._now())
        )
        self._conn.commit()

    def record_perf(self, collect_time_ms=0, classify_time_ms=0, store_time_ms=0, items_processed=0, error_count=0):
        c = self._conn.cursor()
        c.execute(
            "INSERT INTO perf_metrics (collect_time_ms, classify_time_ms, store_time_ms, items_processed, error_count, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (collect_time_ms, classify_time_ms, store_time_ms, items_processed, error_count, self._now())
        )
        self._conn.commit()

    def get_dashboard_data(self, days=7):
        return {
            "health_score": self.get_health_score(days=days),
            "active_sources": self._count_active_sources(days=days),
            "items_collected": self._count_items(days=days),
            "alerts_fired": self._count_alerts(days=days),
            "sla_compliance": self._get_sla_compliance_rate(days=days),
            "anomalies_detected": self._count_anomalies(days=days),
            "top_sources": self._get_top_sources(days=days, limit=10),
            "top_topics": self._get_top_topics(days=days, limit=10),
            "items_per_hour": self._get_items_per_hour(days=days),
            "sources_status": self._get_sources_status(days=days),
            "recent_alerts": self._get_recent_alerts(limit=20),
            "sla_breaches": self._get_recent_sla_breaches(days=days),
        }

    def get_health_score(self, days=7):
        scores = []
        sla_compliance = self._get_sla_compliance_rate(days=days)
        scores.append(sla_compliance * 100)
        source_availability = self._get_source_availability(days=days)
        scores.append(source_availability * 100)
        error_rate = self._get_error_rate(days=days)
        scores.append(max(0, 100 - error_rate * 100))
        if not scores:
            return 100.0
        return round(sum(scores) / len(scores), 2)

    def _get_sla_compliance_rate(self, days=7):
        if not self.sla_monitor:
            return 1.0
        try:
            summary = self.sla_monitor.get_sla_summary(days=days)
            return summary.get("compliance_rate", 100) / 100.0
        except Exception:
            return 1.0

    def _get_source_availability(self, days=7):
        if not self.sla_monitor:
            return 1.0
        try:
            health = self.sla_monitor.get_all_sources_health(days=days)
            if not health:
                return 1.0
            uptimes = [h.get("uptime_pct", 100) for h in health.values()]
            return (sum(uptimes) / len(uptimes)) / 100.0
        except Exception:
            return 1.0

    def _get_error_rate(self, days=7):
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        c = self._conn.cursor()
        c.execute("SELECT SUM(items_processed), SUM(error_count) FROM perf_metrics WHERE created_at >= ?", (since,))
        row = c.fetchone()
        total_items = row[0] or 0
        total_errors = row[1] or 0
        if total_items == 0:
            return 0.0
        return round(total_errors / total_items, 4)

    def _count_active_sources(self, days=7):
        if not self.sql_store:
            return 0
        try:
            stats = self.sql_store.get_stats()
            return len(stats.get("by_source", {}))
        except Exception:
            return 0

    def _count_items(self, days=7):
        if not self.sql_store:
            return 0
        try:
            return self.sql_store.count() or 0
        except Exception:
            return 0

    def _count_alerts(self, days=7):
        if not self.alert_engine:
            return 0
        try:
            stats = self.alert_engine.get_alert_stats(days=days)
            return stats.get("triggered_count", 0)
        except Exception:
            return 0

    def _count_anomalies(self, days=7):
        c = self._conn.cursor()
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        c.execute("SELECT COUNT(*) FROM audit_log WHERE event LIKE '%anomaly%' AND created_at >= ?", (since,))
        return c.fetchone()[0]

    def _get_top_sources(self, days=7, limit=10):
        if not self.sql_store:
            return []
        try:
            stats = self.sql_store.get_stats()
            by_source = stats.get("by_source", {})
            sorted_sources = sorted(by_source.items(), key=lambda x: x[1], reverse=True)[:limit]
            return [{"source": s, "count": c} for s, c in sorted_sources]
        except Exception:
            return []

    def _get_top_topics(self, days=7, limit=10):
        if not self.sql_store:
            return []
        try:
            stats = self.sql_store.get_stats()
            by_topic = stats.get("by_topic", {})
            topic_counts = defaultdict(int)
            for topics_str, count in by_topic.items():
                if isinstance(topics_str, str):
                    for t in topics_str.split(","):
                        t = t.strip()
                        if t:
                            topic_counts[t] += count
                else:
                    topic_counts[str(topics_str)] += count
            sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
            return [{"topic": t, "count": c} for t, c in sorted_topics]
        except Exception:
            return []

    def _get_items_per_hour(self, days=7):
        if not self.sql_store:
            return []
        hours = defaultdict(int)
        try:
            sources = self.sql_store.get_stats().get("by_source", {})
            for source in sources:
                items = self.sql_store.get_by_source(source, limit=100)
                for item in items:
                    pub = item.get("published_at")
                    if pub:
                        if isinstance(pub, str):
                            pub_dt = datetime.fromisoformat(pub.replace("Z", "+00:00").split("+")[0])
                        else:
                            pub_dt = pub
                        if (datetime.utcnow() - pub_dt).days <= days:
                            hour_key = pub_dt.strftime("%Y-%m-%d %H:00")
                            hours[hour_key] += 1
        except Exception:
            pass
        sorted_hours = sorted(hours.items())
        return [{"time": h, "count": c} for h, c in sorted_hours]

    def _get_sources_status(self, days=7):
        if not self.sql_store:
            return []
        try:
            stats = self.sql_store.get_stats()
            by_source = stats.get("by_source", {})
            statuses = []
            for source, count in by_source.items():
                status = "healthy"
                if count == 0:
                    status = "inactive"
                elif count < 5:
                    status = "degraded"
                age = 0
                if self.sla_monitor:
                    try:
                        health = self.sla_monitor.get_source_health(source, days=max(days, 30))
                        age = health.get("avg_content_age_hours", 0)
                        if health.get("sla_compliance_pct", 100) < 80:
                            status = "degraded"
                        elif health.get("sla_compliance_pct", 100) < 50:
                            status = "critical"
                    except Exception:
                        pass
                statuses.append({
                    "source": source,
                    "items_count": count,
                    "status": status,
                    "avg_age_hours": age,
                })
            return statuses
        except Exception:
            return []

    def _get_recent_alerts(self, limit=20):
        if not self.alert_engine:
            return []
        try:
            stats = self.alert_engine.get_alert_stats(days=7)
            top = stats.get("top_alerts", [])
            return [{"name": a["name"], "count": a["count"], "severity": "info"} for a in top[:limit]]
        except Exception:
            return []

    def _get_recent_sla_breaches(self, days=7):
        if not self.sla_monitor:
            return []
        try:
            return self.sla_monitor.get_breach_report(days=days)[:20]
        except Exception:
            return []

    def get_status_widget(self):
        health = self.get_health_score(days=7)
        if health >= 90:
            status = "healthy"
            color = "green"
            message = "All systems operational"
        elif health >= 70:
            status = "degraded"
            color = "yellow"
            message = "Some systems experiencing issues"
        else:
            status = "critical"
            color = "red"
            message = "Critical system issues detected"
        metrics = []
        try:
            metrics.append({"label": "Health Score", "value": f"{health}%"})
            metrics.append({"label": "Active Sources", "value": str(self._count_active_sources())})
            metrics.append({"label": "Items Collected", "value": str(self._count_items())})
            metrics.append({"label": "SLA Compliance", "value": f"{self._get_sla_compliance_rate() * 100:.1f}%"})
        except Exception:
            pass
        return {
            "status": status,
            "color": color,
            "message": message,
            "metrics": metrics,
        }

    def get_source_status_table(self, source=None):
        return self._get_sources_status(days=7)

    def get_activity_timeline(self, hours=24):
        since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        c = self._conn.cursor()
        c.execute(
            "SELECT created_at, event, detail, severity FROM audit_log WHERE created_at >= ? ORDER BY created_at DESC LIMIT 100",
            (since,)
        )
        return [
            {"time": row[0], "event": row[1], "detail": row[2], "severity": row[3]}
            for row in c.fetchall()
        ]

    def get_performance_metrics(self, hours=24):
        since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        c = self._conn.cursor()
        c.execute(
            "SELECT AVG(collect_time_ms), AVG(classify_time_ms), AVG(store_time_ms), SUM(items_processed), SUM(error_count), COUNT(*) FROM perf_metrics WHERE created_at >= ?",
            (since,)
        )
        row = c.fetchone()
        avg_collect = row[0] or 0
        avg_classify = row[1] or 0
        avg_store = row[2] or 0
        total_items = row[3] or 0
        total_errors = row[4] or 0
        total_records = row[5] or 0
        time_span_hours = hours
        items_per_sec = round(total_items / (time_span_hours * 3600), 4) if time_span_hours > 0 else 0
        error_rate = round(total_errors / max(total_items, 1), 4)
        return {
            "avg_collect_time_ms": round(avg_collect, 2),
            "avg_classify_time_ms": round(avg_classify, 2),
            "avg_store_time_ms": round(avg_store, 2),
            "items_per_second": items_per_sec,
            "error_rate": error_rate,
            "total_items": total_items,
            "total_errors": total_errors,
        }

    def get_recent_errors(self, limit=20):
        since = (datetime.utcnow() - timedelta(days=7)).isoformat()
        c = self._conn.cursor()
        c.execute(
            "SELECT created_at, event, detail, source FROM audit_log WHERE severity IN ('error', 'critical') AND created_at >= ? ORDER BY created_at DESC LIMIT ?",
            (since, limit)
        )
        return [
            {"time": row[0], "event": row[1], "detail": row[2], "source": row[3]}
            for row in c.fetchall()
        ]

    def get_widget_configurations(self):
        return [
            {"id": "health_score", "name": "Health Score", "type": "gauge", "default_cols": 2, "default_rows": 1, "refresh_seconds": 60},
            {"id": "sources_status", "name": "Sources Status", "type": "table", "default_cols": 4, "default_rows": 2, "refresh_seconds": 120},
            {"id": "items_per_hour", "name": "Items per Hour", "type": "bar_chart", "default_cols": 4, "default_rows": 2, "refresh_seconds": 300},
            {"id": "recent_alerts", "name": "Recent Alerts", "type": "list", "default_cols": 3, "default_rows": 2, "refresh_seconds": 30},
            {"id": "sla_breaches", "name": "SLA Breaches", "type": "list", "default_cols": 3, "default_rows": 2, "refresh_seconds": 60},
            {"id": "activity_timeline", "name": "Activity Timeline", "type": "timeline", "default_cols": 6, "default_rows": 3, "refresh_seconds": 30},
            {"id": "performance_metrics", "name": "Performance Metrics", "type": "metric_grid", "default_cols": 3, "default_rows": 1, "refresh_seconds": 60},
            {"id": "top_sources", "name": "Top Sources", "type": "bar_chart", "default_cols": 3, "default_rows": 2, "refresh_seconds": 300},
            {"id": "top_topics", "name": "Top Topics", "type": "bar_chart", "default_cols": 3, "default_rows": 2, "refresh_seconds": 300},
            {"id": "status_widget", "name": "System Status", "type": "status_indicator", "default_cols": 2, "default_rows": 1, "refresh_seconds": 30},
        ]
