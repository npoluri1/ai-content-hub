import sqlite3
import json
import math
from datetime import datetime, timedelta
from collections import defaultdict


class AnomalyDetector:
    def __init__(self, sql_store=None):
        self.sql_store = sql_store
        self._conn = sqlite3.connect(":memory:")
        self._init_db()

    def _init_db(self):
        c = self._conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS daily_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                source TEXT,
                topic TEXT,
                count INTEGER DEFAULT 0,
                sentiment_sum REAL DEFAULT 0.0,
                sentiment_count INTEGER DEFAULT 0,
                engagement_sum INTEGER DEFAULT 0,
                engagement_count INTEGER DEFAULT 0
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS source_daily (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                source TEXT NOT NULL,
                content_count INTEGER DEFAULT 0,
                engagement_sum INTEGER DEFAULT 0,
                UNIQUE(date, source)
            )
        """)
        self._conn.commit()

    def _now(self):
        return datetime.utcnow().isoformat()

    def _today(self):
        return datetime.utcnow().strftime("%Y-%m-%d")

    def record_daily(self, date_str, source=None, topic=None, count=1, sentiment=0.0, engagement=0):
        c = self._conn.cursor()
        c.execute(
            "INSERT OR IGNORE INTO daily_stats (date, source, topic, count, sentiment_sum, sentiment_count, engagement_sum, engagement_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (date_str, source, topic, 0, 0.0, 0, 0, 0)
        )
        c.execute(
            "UPDATE daily_stats SET count = count + ?, sentiment_sum = sentiment_sum + ?, sentiment_count = sentiment_count + ?, engagement_sum = engagement_sum + ?, engagement_count = engagement_count + ? WHERE date = ? AND source IS ? AND topic IS ?",
            (count, sentiment, 1 if sentiment != 0 else 0, engagement, 1 if engagement != 0 else 0, date_str, source, topic)
        )
        if source:
            c.execute(
                "INSERT OR IGNORE INTO source_daily (date, source, content_count, engagement_sum) VALUES (?, ?, ?, ?)",
                (date_str, source, 0, 0)
            )
            c.execute(
                "UPDATE source_daily SET content_count = content_count + ?, engagement_sum = engagement_sum + ? WHERE date = ? AND source = ?",
                (count, engagement, date_str, source)
            )
        self._conn.commit()

    def _compute_stats(self, values):
        if not values:
            return {"mean": 0.0, "std": 0.0, "min": 0, "max": 0, "median": 0}
        n = len(values)
        mean = sum(values) / n
        variance = sum((x - mean) ** 2 for x in values) / n if n > 1 else 0
        std = math.sqrt(variance)
        sorted_vals = sorted(values)
        median = sorted_vals[n // 2] if n % 2 == 1 else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
        return {
            "mean": round(mean, 3),
            "std": round(std, 3),
            "min": min(values),
            "max": max(values),
            "median": median,
        }

    def _get_daily_counts(self, source=None, topic=None, days=30):
        since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
        c = self._conn.cursor()
        query = "SELECT date, count FROM daily_stats WHERE date >= ?"
        params = [since]
        if source:
            query += " AND source = ?"
            params.append(source)
        if topic:
            query += " AND topic = ?"
            params.append(topic)
        query += " ORDER BY date ASC"
        c.execute(query, params)
        return {row[0]: row[1] for row in c.fetchall()}

    def get_daily_baseline(self, source=None, topic=None, days=30):
        counts = self._get_daily_counts(source=source, topic=topic, days=days)
        values = list(counts.values())
        return self._compute_stats(values)

    def check_volume_anomaly(self, source=None, topic=None, window_days=7, z_score_threshold=2.0):
        counts = self._get_daily_counts(source=source, topic=topic, days=window_days * 3)
        if not counts:
            today = self._today()
            self.record_daily(today, source=source, topic=topic, count=0)
            counts = self._get_daily_counts(source=source, topic=topic, days=window_days * 3)
        count_values = list(counts.values())
        if len(count_values) < 3:
            return {"is_anomaly": False, "current_count": count_values[-1] if count_values else 0, "expected_count": 0, "z_score": 0, "direction": "normal", "message": "Insufficient data"}
        current = count_values[-1]
        baseline_values = count_values[:-1]
        if not baseline_values:
            return {"is_anomaly": False, "current_count": current, "expected_count": 0, "z_score": 0, "direction": "normal", "message": "Insufficient baseline data"}
        stats = self._compute_stats(baseline_values)
        expected = stats["mean"]
        std = stats["std"]
        if std == 0:
            if current == expected:
                z_score = 0
            else:
                z_score = (current - expected) / (expected if expected > 0 else 1)
        else:
            z_score = (current - expected) / std if std > 0 else 0
        is_anomaly = abs(z_score) > z_score_threshold
        direction = "spike" if z_score > 0 and is_anomaly else ("drop" if z_score < 0 and is_anomaly else "normal")
        return {
            "is_anomaly": is_anomaly,
            "current_count": current,
            "expected_count": round(expected, 2),
            "z_score": round(z_score, 3),
            "direction": direction,
            "source": source,
            "topic": topic,
        }

    def check_topic_shift(self, topic, window_days=14, change_threshold=0.5):
        total_days = window_days * 2
        counts = self._get_daily_counts(topic=topic, days=total_days)
        count_values = list(counts.values())
        if len(count_values) < 4:
            return {"topic": topic, "prev_avg": 0, "current_avg": 0, "change_pct": 0, "is_shift": False, "message": "Insufficient data"}
        mid = len(count_values) // 2
        prev_half = count_values[:mid]
        cur_half = count_values[mid:]
        prev_avg = sum(prev_half) / len(prev_half) if prev_half else 0
        cur_avg = sum(cur_half) / len(cur_half) if cur_half else 0
        change_pct = 0.0
        if prev_avg > 0:
            change_pct = (cur_avg - prev_avg) / prev_avg
        elif cur_avg > 0:
            change_pct = 1.0
        is_shift = abs(change_pct) > change_threshold
        return {
            "topic": topic,
            "prev_avg": round(prev_avg, 3),
            "current_avg": round(cur_avg, 3),
            "change_pct": round(change_pct, 3),
            "is_shift": is_shift,
        }

    def _get_daily_sentiment_avg(self, topic=None, days=7):
        since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
        c = self._conn.cursor()
        query = "SELECT date, sentiment_sum, sentiment_count FROM daily_stats WHERE date >= ? AND sentiment_count > 0"
        params = [since]
        if topic:
            query += " AND topic = ?"
            params.append(topic)
        query += " ORDER BY date ASC"
        c.execute(query, params)
        result = {}
        for row in c.fetchall():
            result[row[0]] = row[1] / row[2] if row[2] > 0 else 0.0
        return result

    def check_sentiment_shift(self, topic, window_days=7, threshold=0.3):
        total_days = window_days * 2
        sentiments = self._get_daily_sentiment_avg(topic=topic, days=total_days)
        if not sentiments:
            return {"topic": topic, "prev_avg": 0, "current_avg": 0, "change": 0, "is_shift": False, "message": "No sentiment data"}
        values = list(sentiments.values())
        if len(values) < 2:
            return {"topic": topic, "prev_avg": values[0], "current_avg": values[0], "change": 0, "is_shift": False, "message": "Insufficient data"}
        mid = len(values) // 2
        prev_vals = values[:mid]
        cur_vals = values[mid:]
        prev_avg = sum(prev_vals) / len(prev_vals) if prev_vals else 0
        cur_avg = sum(cur_vals) / len(cur_vals) if cur_vals else 0
        change = cur_avg - prev_avg
        is_shift = abs(change) > threshold
        return {
            "topic": topic,
            "prev_avg": round(prev_avg, 3),
            "current_avg": round(cur_avg, 3),
            "change": round(change, 3),
            "is_shift": is_shift,
        }

    def check_engagement_anomaly(self, source=None, window_days=7, z_score_threshold=2.0):
        since = (datetime.utcnow() - timedelta(days=window_days * 3)).strftime("%Y-%m-%d")
        c = self._conn.cursor()
        query = "SELECT date, content_count, engagement_sum FROM source_daily WHERE date >= ?"
        params = [since]
        if source:
            query += " AND source = ?"
            params.append(source)
        query += " ORDER BY date ASC"
        c.execute(query, params)
        rows = c.fetchall()
        if not rows:
            return {"is_anomaly": False, "current_engagement": 0, "expected_engagement": 0, "z_score": 0, "direction": "normal", "message": "No data"}
        engagement_ratios = []
        for _, count, eng_sum in rows:
            if count > 0:
                engagement_ratios.append(eng_sum / count)
        if not engagement_ratios:
            return {"is_anomaly": False, "current_engagement": 0, "expected_engagement": 0, "z_score": 0, "direction": "normal", "message": "No engagement data"}
        current = engagement_ratios[-1]
        baseline = engagement_ratios[:-1]
        if not baseline:
            return {"is_anomaly": False, "current_engagement": round(current, 3), "expected_engagement": round(current, 3), "z_score": 0, "direction": "normal"}
        stats = self._compute_stats(baseline)
        expected = stats["mean"]
        std = stats["std"]
        z_score = (current - expected) / std if std > 0 else 0
        is_anomaly = abs(z_score) > z_score_threshold
        direction = "spike" if z_score > 0 and is_anomaly else ("drop" if z_score < 0 and is_anomaly else "normal")
        return {
            "is_anomaly": is_anomaly,
            "current_engagement": round(current, 3),
            "expected_engagement": round(expected, 3),
            "z_score": round(z_score, 3),
            "direction": direction,
            "source": source,
        }

    def check_new_source(self, source, baseline_days=7):
        since = (datetime.utcnow() - timedelta(days=baseline_days)).strftime("%Y-%m-%d")
        c = self._conn.cursor()
        c.execute("SELECT content_count FROM source_daily WHERE source = ? AND date >= ? ORDER BY date ASC", (source, since))
        counts = [row[0] for row in c.fetchall()]
        today = self._today()
        c.execute("SELECT content_count FROM source_daily WHERE source = ? AND date = ?", (source, today))
        today_row = c.fetchone()
        today_count = today_row[0] if today_row else 0
        if not counts:
            return {"source": source, "is_anomaly": False, "message": "No baseline for this source"}
        avg = sum(counts) / len(counts)
        if len(counts) >= 2:
            variance = sum((x - avg) ** 2 for x in counts) / len(counts)
            std = math.sqrt(variance)
        else:
            std = avg * 0.5 if avg > 0 else 1.0
        z_score = (today_count - avg) / std if std > 0 else 0
        is_anomaly = abs(z_score) > 2.0
        return {
            "source": source,
            "is_anomaly": is_anomaly,
            "today_count": today_count,
            "baseline_avg": round(avg, 2),
            "z_score": round(z_score, 3),
            "direction": "spike" if z_score > 0 and is_anomaly else ("drop" if z_score < 0 and is_anomaly else "normal"),
        }

    def run_all_checks(self, days=7):
        findings = []
        volume = self.check_volume_anomaly(window_days=days)
        if volume["is_anomaly"]:
            findings.append({"check": "volume_anomaly", "details": volume})
        c = self._conn.cursor()
        c.execute("SELECT DISTINCT topic FROM daily_stats WHERE topic IS NOT NULL AND topic != ''")
        topics = [row[0] for row in c.fetchall()]
        for topic in topics:
            shift = self.check_topic_shift(topic, window_days=days)
            if shift["is_shift"]:
                findings.append({"check": "topic_shift", "details": shift})
            sent = self.check_sentiment_shift(topic, window_days=days)
            if sent["is_shift"]:
                findings.append({"check": "sentiment_shift", "details": sent})
        c.execute("SELECT DISTINCT source FROM source_daily")
        sources = [row[0] for row in c.fetchall()]
        for src in sources:
            eng = self.check_engagement_anomaly(source=src, window_days=days)
            if eng["is_anomaly"]:
                findings.append({"check": "engagement_anomaly", "details": eng})
            ns = self.check_new_source(src, baseline_days=days)
            if ns["is_anomaly"]:
                findings.append({"check": "source_behavior_change", "details": ns})
        return findings
