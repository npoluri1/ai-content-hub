import sqlite3
import json
import uuid
import os
from datetime import datetime, timedelta


ESCALATION_LEVELS = {
    0: {"name": "initial", "max_wait_minutes": 5},
    1: {"name": "team", "max_wait_minutes": 10},
    2: {"name": "manager", "max_wait_minutes": 30},
    3: {"name": "director", "max_wait_minutes": 60},
    4: {"name": "emergency", "max_wait_minutes": 120},
}


class EscalationEngine:
    def __init__(self, db_path="./data/escalations.db"):
        self.db_path = db_path
        if db_path != ":memory:":
            os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        c = self._conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS escalation_policies (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                rules TEXT NOT NULL,
                channels TEXT NOT NULL,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS active_escalations (
                id TEXT PRIMARY KEY,
                alert_id TEXT NOT NULL,
                policy_id TEXT NOT NULL,
                alert_data TEXT,
                current_level INTEGER DEFAULT 0,
                started_at TEXT,
                last_escalated_at TEXT,
                acknowledged_by TEXT,
                acknowledged_at TEXT,
                resolved_by TEXT,
                resolved_at TEXT,
                resolution TEXT,
                status TEXT DEFAULT 'active'
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS escalation_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                escalation_id TEXT NOT NULL,
                alert_id TEXT,
                level INTEGER NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                performed_by TEXT,
                created_at TEXT,
                FOREIGN KEY (escalation_id) REFERENCES active_escalations(id)
            )
        """)
        self._conn.commit()
        c.close()

    def _now(self):
        return datetime.utcnow().isoformat()

    def _row_to_policy(self, row):
        return {
            "id": row[0],
            "name": row[1],
            "rules": json.loads(row[2]) if row[2] else [],
            "channels": json.loads(row[3]) if row[3] else [],
            "created_at": row[4],
            "updated_at": row[5],
        }

    def _row_to_escalation(self, row):
        return {
            "id": row[0],
            "alert_id": row[1],
            "policy_id": row[2],
            "alert_data": json.loads(row[3]) if row[3] else {},
            "current_level": row[4],
            "started_at": row[5],
            "last_escalated_at": row[6],
            "acknowledged_by": row[7],
            "acknowledged_at": row[8],
            "resolved_by": row[9],
            "resolved_at": row[10],
            "resolution": row[11],
            "status": row[12],
        }

    def create_escalation_policy(self, name, rules, channels):
        policy_id = str(uuid.uuid4())
        now = self._now()
        c = self._conn.cursor()
        c.execute(
            "INSERT INTO escalation_policies (id, name, rules, channels, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (policy_id, name, json.dumps(rules), json.dumps(channels), now, now)
        )
        self._conn.commit()
        c.close()
        return policy_id

    def get_policy(self, policy_id):
        c = self._conn.cursor()
        c.execute("SELECT * FROM escalation_policies WHERE id = ?", (policy_id,))
        row = c.fetchone()
        c.close()
        if row:
            return self._row_to_policy(row)
        return None

    def list_policies(self):
        c = self._conn.cursor()
        c.execute("SELECT * FROM escalation_policies ORDER BY created_at DESC")
        rows = c.fetchall()
        c.close()
        return [self._row_to_policy(row) for row in rows]

    def update_policy(self, policy_id, **kwargs):
        allowed = {"name", "rules", "channels"}
        updates = []
        values = []
        for k, v in kwargs.items():
            if k in allowed:
                if k in ("rules", "channels"):
                    v = json.dumps(v)
                updates.append(f"{k} = ?")
                values.append(v)
        if not updates:
            return False
        updates.append("updated_at = ?")
        values.append(self._now())
        values.append(policy_id)
        c = self._conn.cursor()
        c.execute(f"UPDATE escalation_policies SET {', '.join(updates)} WHERE id = ?", values)
        self._conn.commit()
        affected = c.rowcount > 0
        c.close()
        return affected

    def delete_policy(self, policy_id):
        c = self._conn.cursor()
        c.execute("DELETE FROM escalation_policies WHERE id = ?", (policy_id,))
        self._conn.commit()
        affected = c.rowcount > 0
        c.close()
        return affected

    def _evaluate_rules(self, alert, rules):
        matched_rules = []
        for rule in rules:
            condition = rule.get("condition", "")
            if "severity == critical" in condition and alert.get("severity") == "critical":
                matched_rules.append(rule)
            if "unacknowledged" in condition and "5min" in condition:
                matched_rules.append(rule)
        return matched_rules

    def _escalate(self, escalation_id, alert_id, current_level, policy):
        now = self._now()
        next_level = min(current_level + 1, 4)
        level_info = ESCALATION_LEVELS.get(next_level, {})
        users = []
        channels = []
        for rule in policy.get("rules", []):
            if rule.get("escalate_to"):
                users.extend(rule["escalate_to"])
            if rule.get("notify_via"):
                channels.extend(rule["notify_via"])
        users = list(set(users))
        channels = list(set(channels or policy.get("channels", [])))
        c = self._conn.cursor()
        c.execute(
            "UPDATE active_escalations SET current_level = ?, last_escalated_at = ? WHERE id = ?",
            (next_level, now, escalation_id)
        )
        c.execute(
            "INSERT INTO escalation_log (escalation_id, alert_id, level, action, details, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (escalation_id, alert_id, next_level, "escalated", json.dumps({
                "level_name": level_info.get("name", f"level_{next_level}"),
                "notified_users": users,
                "notify_channels": channels,
                "max_wait_minutes": level_info.get("max_wait_minutes", 60),
            }), now)
        )
        self._conn.commit()
        c.close()
        return {
            "escalation_id": escalation_id,
            "alert_id": alert_id,
            "level": next_level,
            "level_name": level_info.get("name", f"level_{next_level}"),
            "action": "escalated",
            "notified_users": users,
            "notify_channels": channels,
            "timestamp": now,
        }

    def process_alert(self, alert, policy_id=None):
        steps = []
        alert_id = alert.get("id", str(uuid.uuid4()))
        now = self._now()
        if policy_id:
            policy = self.get_policy(policy_id)
        else:
            policies = self.list_policies()
            if not policies:
                return []
            policy = policies[0]
            policy_id = policy["id"]
        if not policy:
            return []
        escalation_id = str(uuid.uuid4())
        c = self._conn.cursor()
        c.execute(
            "INSERT INTO active_escalations (id, alert_id, policy_id, alert_data, current_level, started_at, last_escalated_at, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (escalation_id, alert_id, policy_id, json.dumps(alert), 0, now, now, "active")
        )
        c.execute(
            "INSERT INTO escalation_log (escalation_id, alert_id, level, action, details, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (escalation_id, alert_id, 0, "created", json.dumps({"alert": alert, "policy": policy["name"]}), now)
        )
        self._conn.commit()
        c.close()
        matched = self._evaluate_rules(alert, policy.get("rules", []))
        if matched:
            step = self._escalate(escalation_id, alert_id, 0, policy)
            steps.append(step)
        return steps

    def acknowledge(self, alert_id, user):
        c = self._conn.cursor()
        now = self._now()
        c.execute(
            "UPDATE active_escalations SET acknowledged_by = ?, acknowledged_at = ?, status = 'acknowledged' WHERE alert_id = ? AND status = 'active'",
            (user, now, alert_id)
        )
        affected = c.rowcount
        if affected:
            c.execute(
                "INSERT INTO escalation_log (escalation_id, alert_id, level, action, details, performed_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("ack", alert_id, 0, "acknowledged", json.dumps({"user": user}), user, now)
            )
            self._conn.commit()
        c.close()
        return affected > 0

    def resolve(self, alert_id, user, resolution):
        c = self._conn.cursor()
        now = self._now()
        c.execute(
            "UPDATE active_escalations SET resolved_by = ?, resolved_at = ?, resolution = ?, status = 'resolved' WHERE alert_id = ? AND status IN ('active', 'acknowledged')",
            (user, now, resolution, alert_id)
        )
        affected = c.rowcount
        if affected:
            c.execute(
                "INSERT INTO escalation_log (escalation_id, alert_id, level, action, details, performed_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("res", alert_id, 0, "resolved", json.dumps({"user": user, "resolution": resolution}), user, now)
            )
            self._conn.commit()
        c.close()
        return affected > 0

    def get_escalation_status(self, alert_id):
        c = self._conn.cursor()
        c.execute("SELECT * FROM active_escalations WHERE alert_id = ? ORDER BY started_at DESC LIMIT 1", (alert_id,))
        row = c.fetchone()
        c.close()
        if not row:
            return None
        escalation = self._row_to_escalation(row)
        now = datetime.utcnow()
        started = datetime.fromisoformat(escalation["started_at"])
        time_in_level = (now - started).total_seconds() / 60 if escalation["status"] == "active" else 0
        level_info = ESCALATION_LEVELS.get(escalation["current_level"], {})
        return {
            "escalation_id": escalation["id"],
            "alert_id": escalation["alert_id"],
            "current_level": escalation["current_level"],
            "level_name": level_info.get("name", "unknown"),
            "time_in_level_minutes": round(time_in_level, 1),
            "max_wait_minutes": level_info.get("max_wait_minutes", 0),
            "assigned_to": escalation.get("acknowledged_by"),
            "status": escalation["status"],
            "started_at": escalation["started_at"],
            "last_escalated_at": escalation["last_escalated_at"],
        }

    def get_active_escalations(self):
        c = self._conn.cursor()
        c.execute("SELECT * FROM active_escalations WHERE status = 'active' ORDER BY started_at ASC")
        rows = c.fetchall()
        c.close()
        escalations = []
        for row in rows:
            esc = self._row_to_escalation(row)
            level_info = ESCALATION_LEVELS.get(esc["current_level"], {})
            now = datetime.utcnow()
            started = datetime.fromisoformat(esc["started_at"])
            time_in_level = (now - started).total_seconds() / 60
            escalations.append({
                "escalation_id": esc["id"],
                "alert_id": esc["alert_id"],
                "current_level": esc["current_level"],
                "level_name": level_info.get("name", "unknown"),
                "time_in_level_minutes": round(time_in_level, 1),
                "max_wait_minutes": level_info.get("max_wait_minutes", 0),
                "status": esc["status"],
                "started_at": esc["started_at"],
            })
        return escalations

    def get_escalation_stats(self, days=30):
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        c = self._conn.cursor()
        c.execute("SELECT COUNT(*) FROM active_escalations WHERE started_at >= ?", (since,))
        total = c.fetchone()[0]
        c.execute("SELECT AVG((julianday(acknowledged_at) - julianday(started_at)) * 86400) FROM active_escalations WHERE acknowledged_at IS NOT NULL AND started_at >= ?", (since,))
        row = c.fetchone()
        mtta = row[0] if row and row[0] else 0
        c.execute("SELECT AVG((julianday(resolved_at) - julianday(started_at)) * 86400) FROM active_escalations WHERE resolved_at IS NOT NULL AND started_at >= ?", (since,))
        row = c.fetchone()
        mttr = row[0] if row and row[0] else 0
        c.execute("""
            SELECT ae.policy_id, ep.name, COUNT(*) as cnt
            FROM active_escalations ae
            JOIN escalation_policies ep ON ae.policy_id = ep.id
            WHERE ae.started_at >= ?
            GROUP BY ae.policy_id ORDER BY cnt DESC
        """, (since,))
        per_policy = [{"policy_id": row[0], "policy_name": row[1], "count": row[2]} for row in c.fetchall()]
        c.close()
        return {
            "total_escalations": total,
            "mean_time_to_acknowledge_seconds": round(mtta, 1),
            "mean_time_to_resolve_seconds": round(mttr, 1),
            "escalations_per_policy": per_policy,
            "period_days": days,
        }
