import sqlite3
import uuid
import time
import threading
import traceback
from datetime import datetime, timedelta
from typing import Any, Callable


class ErrorHandler:
    def __init__(self, db_path: str = "./data/error_handler.db"):
        self._config = {
            "max_retries": 3,
            "retry_delay_seconds": 10,
            "backoff_multiplier": 2,
            "dead_letter_queue": True,
            "error_branch": True,
        }
        self._db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self._db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self):
        conn = sqlite3.connect(self._db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS dead_letter_queue (
                dlq_id TEXT PRIMARY KEY,
                workflow_id TEXT,
                node_id TEXT,
                item TEXT,
                error TEXT,
                traceback TEXT,
                failed_at TEXT,
                retry_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                resolved_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS error_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id TEXT,
                node_id TEXT,
                error_type TEXT,
                error_message TEXT,
                traceback TEXT,
                occurred_at TEXT,
                resolution TEXT,
                resolved_at TEXT,
                retry_attempts INTEGER DEFAULT 0,
                duration_seconds REAL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_dlq_workflow ON dead_letter_queue(workflow_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_error_log_workflow ON error_log(workflow_id)
        """)
        conn.commit()
        conn.close()

    def configure(self, config: dict):
        for key in ("max_retries", "retry_delay_seconds", "backoff_multiplier", "dead_letter_queue", "error_branch"):
            if key in config:
                self._config[key] = config[key]

    def wrap_handler(self, node_type: str, handler_fn: Callable) -> Callable:
        def wrapped(*args, **kwargs):
            node = kwargs.get("node", {})
            context = kwargs.get("context", {})
            error_config = node.get("error_handling", {})
            max_retries = error_config.get("max_retries", self._config["max_retries"])
            delay = error_config.get("retry_delay_seconds", self._config["retry_delay_seconds"])
            backoff = error_config.get("backoff_multiplier", self._config["backoff_multiplier"])

            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    result = handler_fn(*args, **kwargs)
                    return result
                except Exception as e:
                    last_error = e
                    if attempt < max_retries:
                        sleep_time = delay * (backoff ** attempt)
                        time.sleep(sleep_time)
                        continue
                    else:
                        error_result = self.handle_error(
                            e, node, context, error_config
                        )
                        if error_result.get("decision") == "error_branch":
                            return {"_error_branch": True, "error": str(e), "node": node.get("id")}
                        raise
        return wrapped

    def retry(self, fn: Callable, max_retries: int = 3, delay: int = 10, backoff: float = 2.0) -> tuple:
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                return True, fn()
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    sleep_time = delay * (backoff ** attempt)
                    time.sleep(sleep_time)
                else:
                    return False, last_error
        return False, last_error

    def handle_error(self, error: Exception, node: dict, context: dict, config: dict) -> dict:
        max_retries = config.get("max_retries", self._config["max_retries"])
        error_branch = config.get("error_branch", self._config["error_branch"])
        dlq_enabled = config.get("dead_letter_queue", self._config["dead_letter_queue"])

        node_id = node.get("id", "unknown")
        workflow_id = context.get("workflow_id", "unknown")

        node_history = context.get("_node_history", [])
        node_attempts = sum(1 for n in node_history if n.get("node_id") == node_id)

        error_type = type(error).__name__
        error_message = str(error)
        tb_str = traceback.format_exc()

        self._log_error(workflow_id, node_id, error_type, error_message, tb_str, node_attempts)

        if node_attempts < max_retries:
            next_retry_delay = self._config["retry_delay_seconds"] * (self._config["backoff_multiplier"] ** node_attempts)
            context_updates = {
                "_last_error": error_message,
                "_retry_count": node_attempts + 1,
                "_next_retry_at": (datetime.utcnow() + timedelta(seconds=next_retry_delay)).isoformat(),
            }
            return {
                "decision": "retry",
                "next_retry": next_retry_delay,
                "context_updates": context_updates,
            }

        if error_branch:
            context_updates = {"_last_error": error_message, "_error_node": node_id}
            return {
                "decision": "error_branch",
                "next_retry": None,
                "context_updates": context_updates,
            }

        if dlq_enabled:
            item = context.get("_current_item", {})
            self.send_to_dead_letter(item, error_message, workflow_id, node_id)

        context_updates = {"_last_error": error_message, "_failed": True, "_failed_node": node_id}
        return {
            "decision": "fail",
            "next_retry": None,
            "context_updates": context_updates,
        }

    def _log_error(self, workflow_id: str, node_id: str, error_type: str, error_message: str, tb_str: str, retry_attempts: int):
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO error_log (workflow_id, node_id, error_type, error_message, traceback, occurred_at, retry_attempts)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (workflow_id, node_id, error_type, error_message, tb_str, datetime.utcnow().isoformat(), retry_attempts),
        )
        conn.commit()

    def send_to_dead_letter(self, item: dict, error: str, workflow_id: str, node_id: str) -> str:
        dlq_id = f"dlq_{uuid.uuid4().hex[:12]}"
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO dead_letter_queue (dlq_id, workflow_id, node_id, item, error, traceback, failed_at, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')""",
            (dlq_id, workflow_id, node_id, str(item), error, traceback.format_exc(), datetime.utcnow().isoformat()),
        )
        conn.commit()
        return dlq_id

    def get_dead_letter_queue(self, workflow_id: str = None, limit: int = 50) -> list[dict]:
        conn = self._get_conn()
        if workflow_id:
            rows = conn.execute(
                "SELECT * FROM dead_letter_queue WHERE workflow_id = ? ORDER BY failed_at DESC LIMIT ?",
                (workflow_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM dead_letter_queue ORDER BY failed_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def retry_dlq_item(self, dlq_id: str) -> bool:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM dead_letter_queue WHERE dlq_id = ?", (dlq_id,)
        ).fetchone()
        if not row:
            return False
        conn.execute(
            """UPDATE dead_letter_queue
               SET retry_count = retry_count + 1, status = 'retrying'
               WHERE dlq_id = ?""",
            (dlq_id,),
        )
        conn.commit()
        return True

    def clear_dlq(self, workflow_id: str = None) -> int:
        conn = self._get_conn()
        if workflow_id:
            cursor = conn.execute("DELETE FROM dead_letter_queue WHERE workflow_id = ?", (workflow_id,))
        else:
            cursor = conn.execute("DELETE FROM dead_letter_queue")
        conn.commit()
        return cursor.rowcount

    def get_error_stats(self, workflow_id: str = None, days: int = 30) -> dict:
        conn = self._get_conn()
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()

        if workflow_id:
            total = conn.execute(
                "SELECT COUNT(*) as cnt FROM error_log WHERE workflow_id = ? AND occurred_at >= ?",
                (workflow_id, since),
            ).fetchone()["cnt"]
        else:
            total = conn.execute(
                "SELECT COUNT(*) as cnt FROM error_log WHERE occurred_at >= ?", (since,)
            ).fetchone()["cnt"]

        if workflow_id:
            retry_ok = conn.execute(
                "SELECT COUNT(*) as cnt FROM error_log WHERE workflow_id = ? AND occurred_at >= ? AND retry_attempts > 0 AND resolution = 'resolved'",
                (workflow_id, since),
            ).fetchone()["cnt"]
            retry_total = conn.execute(
                "SELECT COUNT(*) as cnt FROM error_log WHERE workflow_id = ? AND occurred_at >= ? AND retry_attempts > 0",
                (workflow_id, since),
            ).fetchone()["cnt"]
        else:
            retry_ok = conn.execute(
                "SELECT COUNT(*) as cnt FROM error_log WHERE occurred_at >= ? AND retry_attempts > 0 AND resolution = 'resolved'",
                (since,),
            ).fetchone()["cnt"]
            retry_total = conn.execute(
                "SELECT COUNT(*) as cnt FROM error_log WHERE occurred_at >= ? AND retry_attempts > 0",
                (since,),
            ).fetchone()["cnt"]

        retry_success_rate = (retry_ok / retry_total * 100) if retry_total > 0 else 0.0

        if workflow_id:
            top_errors_rows = conn.execute(
                """SELECT error_type, COUNT(*) as cnt
                   FROM error_log WHERE workflow_id = ? AND occurred_at >= ?
                   GROUP BY error_type ORDER BY cnt DESC LIMIT 10""",
                (workflow_id, since),
            ).fetchall()
        else:
            top_errors_rows = conn.execute(
                """SELECT error_type, COUNT(*) as cnt
                   FROM error_log WHERE occurred_at >= ?
                   GROUP BY error_type ORDER BY cnt DESC LIMIT 10""",
                (since,),
            ).fetchall()
        top_errors = [dict(r) for r in top_errors_rows]

        avg_time = conn.execute(
            "SELECT AVG(duration_seconds) as avg_time FROM error_log WHERE occurred_at >= ? AND duration_seconds IS NOT NULL",
            (since,),
        ).fetchone()
        avg_resolution_time = avg_time["avg_time"] if avg_time and avg_time["avg_time"] else 0.0

        return {
            "total_errors": total,
            "retry_success_rate": round(retry_success_rate, 2),
            "top_errors": top_errors,
            "avg_resolution_time": round(avg_resolution_time, 2),
            "period_days": days,
        }

    def resolve_error(self, error_log_id: int, resolution: str = "resolved") -> bool:
        conn = self._get_conn()
        cursor = conn.execute(
            "UPDATE error_log SET resolution = ?, resolved_at = ? WHERE id = ?",
            (resolution, datetime.utcnow().isoformat(), error_log_id),
        )
        conn.commit()
        return cursor.rowcount > 0

    def get_error_log(self, workflow_id: str = None, limit: int = 100) -> list[dict]:
        conn = self._get_conn()
        if workflow_id:
            rows = conn.execute(
                "SELECT * FROM error_log WHERE workflow_id = ? ORDER BY occurred_at DESC LIMIT ?",
                (workflow_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM error_log ORDER BY occurred_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]
