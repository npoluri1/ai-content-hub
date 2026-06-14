import sqlite3
import json
import os
import math
from datetime import datetime, timedelta
from collections import defaultdict


class AlertFatigueManager:
    def __init__(self, db_path="./data/alert_fatigue.db"):
        self.db_path = db_path
        if db_path != ":memory:":
            os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        c = self._conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS user_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT NOT NULL,
                alert_name TEXT,
                rule_id TEXT,
                user TEXT NOT NULL,
                action TEXT NOT NULL,
                response_time_seconds INTEGER DEFAULT 0,
                severity TEXT DEFAULT 'info',
                source TEXT,
                topic TEXT,
                created_at TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS user_fatigue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user TEXT NOT NULL,
                date TEXT NOT NULL,
                fatigue_score REAL DEFAULT 0.0,
                alerts_received INTEGER DEFAULT 0,
                alerts_ignored INTEGER DEFAULT 0,
                avg_response_time REAL DEFAULT 0.0,
                suppression_rules TEXT,
                digest_mode INTEGER DEFAULT 0,
                updated_at TEXT,
                UNIQUE(user, date)
            )
        """)
        self._conn.commit()
        c.close()

    def _now(self):
        return datetime.utcnow().isoformat()

    def _today(self):
        return datetime.utcnow().strftime("%Y-%m-%d")

    def record_action(self, alert_id, user, action, response_time_seconds=0):
        now = self._now()
        c = self._conn.cursor()
        c.execute(
            "INSERT INTO user_actions (alert_id, user, action, response_time_seconds, created_at) VALUES (?, ?, ?, ?, ?)",
            (alert_id, user, action, response_time_seconds, now)
        )
        self._conn.commit()
        c.close()
        self._update_fatigue(user)

    def _update_fatigue(self, user):
        today = self._today()
        c = self._conn.cursor()
        c.execute("SELECT COUNT(*) FROM user_actions WHERE user = ? AND DATE(created_at) = ?", (user, today))
        total = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM user_actions WHERE user = ? AND DATE(created_at) = ? AND action IN ('ignored', 'false_positive')", (user, today))
        ignored = c.fetchone()[0]
        c.execute("SELECT AVG(response_time_seconds) FROM user_actions WHERE user = ? AND DATE(created_at) = ? AND response_time_seconds > 0", (user, today))
        avg_rt = c.fetchone()[0] or 0
        fatigue = self._compute_fatigue_score(total, ignored, avg_rt)
        now = self._now()
        c.execute(
            "INSERT OR REPLACE INTO user_fatigue (user, date, fatigue_score, alerts_received, alerts_ignored, avg_response_time, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user, today, fatigue, total, ignored, avg_rt, now)
        )
        self._conn.commit()
        c.close()

    def _compute_fatigue_score(self, total, ignored, avg_response_time):
        if total == 0:
            return 0.0
        ignore_ratio = ignored / total
        rt_factor = 0.0
        if avg_response_time > 300:
            rt_factor = min(1.0, (avg_response_time - 300) / 2700)
        score = (ignore_ratio * 0.5 + rt_factor * 0.3 + min(1.0, total / 50) * 0.2) * 100
        return round(min(100, max(0, score)), 2)

    def get_fatigue_score(self, user, days=7):
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        c = self._conn.cursor()
        c.execute("SELECT fatigue_score FROM user_fatigue WHERE user = ? AND updated_at >= ? ORDER BY date DESC LIMIT 1", (user, since))
        row = c.fetchone()
        current_score = row[0] if row else 0.0
        c.execute("SELECT COUNT(*) FROM user_actions WHERE user = ? AND created_at >= ?", (user, since))
        alerts_received = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM user_actions WHERE user = ? AND created_at >= ? AND action IN ('ignored', 'false_positive')", (user, since))
        alerts_ignored = c.fetchone()[0]
        c.execute("SELECT AVG(response_time_seconds) FROM user_actions WHERE user = ? AND created_at >= ? AND response_time_seconds > 0", (user, since))
        avg_rt = c.fetchone()[0] or 0
        c.execute("SELECT created_at FROM user_actions WHERE user = ? AND created_at >= ? ORDER BY created_at ASC", (user, since))
        times = [row[0] for row in c.fetchall()]
        c.close()
        time_pattern = self._analyze_time_pattern(times)
        factors = [
            {"name": "alerts_received", "value": alerts_received, "impact": "negative" if alerts_received > 30 else "neutral"},
            {"name": "ignore_rate", "value": round(alerts_ignored / max(alerts_received, 1), 2), "impact": "negative"},
            {"name": "avg_response_time_seconds", "value": round(avg_rt, 1), "impact": "negative" if avg_rt > 300 else "neutral"},
            {"name": "time_clustering", "value": time_pattern, "impact": "negative" if time_pattern > 0.5 else "neutral"},
        ]
        if current_score >= 70:
            risk_level = "high"
        elif current_score >= 40:
            risk_level = "medium"
        else:
            risk_level = "low"
        return {
            "user": user,
            "score": current_score,
            "factors": factors,
            "risk_level": risk_level,
            "alerts_received": alerts_received,
            "alerts_ignored": alerts_ignored,
            "avg_response_time_seconds": round(avg_rt, 1),
        }

    def _analyze_time_pattern(self, times):
        if len(times) < 5:
            return 0.0
        night_hours = sum(1 for t in times if 0 <= int(t[11:13]) < 6)
        ratio = night_hours / len(times)
        return round(ratio, 2)

    def get_team_fatigue(self, team, days=7):
        results = []
        for user in team:
            try:
                score = self.get_fatigue_score(user, days=days)
                results.append(score)
            except Exception:
                results.append({"user": user, "score": 0, "risk_level": "unknown"})
        return results

    def suggest_suppression(self, user, days=7):
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        c = self._conn.cursor()
        c.execute(
            "SELECT rule_id, alert_name, action, COUNT(*) as cnt FROM user_actions WHERE user = ? AND created_at >= ? GROUP BY rule_id, alert_name, action",
            (user, since)
        )
        rules_data = defaultdict(lambda: {"total": 0, "false_positive": 0, "ignored": 0})
        for row in c.fetchall():
            rule_id = row[0] or "unknown"
            name = row[1] or "Unknown"
            action = row[2]
            cnt = row[3]
            rules_data[(rule_id, name)]["total"] += cnt
            if action in ("false_positive", "ignored"):
                rules_data[(rule_id, name)][action] += cnt
        c.close()
        suggestions = []
        for (rule_id, name), data in rules_data.items():
            if data["total"] == 0:
                continue
            fp_rate = (data["false_positive"] + data["ignored"]) / data["total"]
            suggestion = "keep"
            if fp_rate > 0.8:
                suggestion = "suppress_permanently"
            elif fp_rate > 0.5:
                suggestion = "suppress_temporarily"
            elif fp_rate > 0.3:
                suggestion = "review_rule"
            suggestions.append({
                "rule_id": rule_id,
                "name": name,
                "false_positive_rate": round(fp_rate, 2),
                "total_alerts": data["total"],
                "suggestion": suggestion,
            })
        suggestions.sort(key=lambda x: x["false_positive_rate"], reverse=True)
        return suggestions

    def suppress_for_user(self, user, rule_id, hours=24):
        c = self._conn.cursor()
        today = self._today()
        c.execute("SELECT suppression_rules FROM user_fatigue WHERE user = ? AND date = ?", (user, today))
        row = c.fetchone()
        existing = json.loads(row[0]) if row and row[0] else []
        expires_at = (datetime.utcnow() + timedelta(hours=hours)).isoformat()
        existing.append({"rule_id": rule_id, "suppressed_until": expires_at})
        c.execute(
            "INSERT OR REPLACE INTO user_fatigue (user, date, suppression_rules, updated_at) VALUES (?, ?, ?, ?)",
            (user, today, json.dumps(existing), self._now())
        )
        self._conn.commit()
        c.close()
        return True

    def get_digest_suggestion(self, user):
        since = (datetime.utcnow() - timedelta(hours=24)).isoformat()
        c = self._conn.cursor()
        c.execute("SELECT COUNT(*) FROM user_actions WHERE user = ? AND created_at >= ?", (user, since))
        alerts_last_hour = c.fetchone()[0]
        c.execute("SELECT fatigue_score FROM user_fatigue WHERE user = ? ORDER BY date DESC LIMIT 1", (user,))
        row = c.fetchone()
        fatigue = row[0] if row else 0
        c.close()
        alerts_per_hour = alerts_last_hour / 24.0
        recommend = fatigue > 50 or alerts_per_hour > 3
        reason = ""
        if fatigue > 50:
            reason = f"Fatigue score ({fatigue}) exceeds threshold"
        elif alerts_per_hour > 3:
            reason = f"Alert rate ({alerts_per_hour:.1f}/hr) exceeds threshold"
        else:
            reason = "Alert volume is manageable"
        if recommend:
            suggested_freq = "hourly" if alerts_per_hour > 10 else "daily" if alerts_per_hour > 3 else "every_6h"
        else:
            suggested_freq = "realtime"
        return {
            "user": user,
            "recommend": recommend,
            "reason": reason,
            "current_alerts_per_hour": round(alerts_per_hour, 2),
            "suggested_frequency": suggested_freq,
            "fatigue_score": fatigue,
        }

    def calculate_noise_ratio(self, alert_id=None, days=30):
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        c = self._conn.cursor()
        if alert_id:
            c.execute("SELECT action, COUNT(*) FROM user_actions WHERE alert_id = ? AND created_at >= ? GROUP BY action", (alert_id, since))
        else:
            c.execute("SELECT action, COUNT(*) FROM user_actions WHERE created_at >= ? GROUP BY action", (since,))
        counts = {row[0]: row[1] for row in c.fetchall()}
        c.close()
        total = sum(counts.values())
        if total == 0:
            return 0.0
        noise_actions = counts.get("ignored", 0) + counts.get("false_positive", 0)
        signal_actions = counts.get("acknowledged", 0) + counts.get("resolved", 0)
        total_signal = signal_actions + noise_actions
        if total_signal == 0:
            return 0.0
        return round(noise_actions / total_signal, 3)

    def get_top_noise_sources(self, days=30, limit=10):
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        c = self._conn.cursor()
        c.execute(
            "SELECT rule_id, alert_name, COUNT(*) as cnt FROM user_actions WHERE action IN ('ignored', 'false_positive') AND created_at >= ? AND rule_id IS NOT NULL GROUP BY rule_id ORDER BY cnt DESC LIMIT ?",
            (since, limit)
        )
        rows = c.fetchall()
        c.close()
        sources = []
        for row in rows:
            c2 = self._conn.cursor()
            c2.execute("SELECT COUNT(*) FROM user_actions WHERE rule_id = ? AND created_at >= ?", (row[0], since))
            total = c2.fetchone()[0]
            c2.close()
            sources.append({
                "rule_id": row[0],
                "name": row[1] or "Unknown",
                "noise_count": row[2],
                "total_alerts": total,
                "noise_ratio": round(row[2] / max(total, 1), 3),
            })
        return sources
