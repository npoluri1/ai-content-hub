import sqlite3
import json
import uuid
import os
from datetime import datetime


class WorkflowStorage:
    def __init__(self, db_path="./data/workflows.db"):
        self.db_path = db_path
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS workflows (
                id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                workflow_json TEXT,
                enabled INTEGER DEFAULT 1,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS workflow_executions (
                id TEXT PRIMARY KEY,
                workflow_id TEXT,
                status TEXT,
                result_json TEXT,
                started_at TEXT,
                finished_at TEXT
            )
        """)
        conn.commit()
        conn.close()

    def _now(self):
        return datetime.utcnow().isoformat()

    def save_workflow(self, workflow):
        workflow_id = workflow.get("id", str(uuid.uuid4()))
        now = self._now()
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO workflows (id, name, description, workflow_json, enabled, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (workflow_id, workflow.get("name", ""), workflow.get("description", ""), json.dumps(workflow), 1, now, now)
        )
        conn.commit()
        conn.close()
        return workflow_id

    def get_workflow(self, workflow_id):
        conn = self._get_conn()
        c = conn.execute("SELECT * FROM workflows WHERE id = ?", (workflow_id,))
        row = c.fetchone()
        conn.close()
        if row:
            return {
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "workflow": json.loads(row[3]) if row[3] else {},
                "enabled": bool(row[4]),
                "created_at": row[5],
                "updated_at": row[6],
            }
        return None

    def list_workflows(self, include_disabled=False):
        conn = self._get_conn()
        if include_disabled:
            c = conn.execute("SELECT * FROM workflows ORDER BY created_at DESC")
        else:
            c = conn.execute("SELECT * FROM workflows WHERE enabled = 1 ORDER BY created_at DESC")
        rows = c.fetchall()
        conn.close()
        result = []
        for row in rows:
            result.append({
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "enabled": bool(row[4]),
                "created_at": row[5],
                "updated_at": row[6],
            })
        return result

    def delete_workflow(self, workflow_id):
        conn = self._get_conn()
        conn.execute("DELETE FROM workflows WHERE id = ?", (workflow_id,))
        conn.execute("DELETE FROM workflow_executions WHERE workflow_id = ?", (workflow_id,))
        conn.commit()
        affected = conn.total_changes
        conn.close()
        return affected > 0

    def enable_workflow(self, workflow_id):
        conn = self._get_conn()
        conn.execute("UPDATE workflows SET enabled = 1, updated_at = ? WHERE id = ?", (self._now(), workflow_id))
        conn.commit()
        affected = conn.total_changes
        conn.close()
        return affected > 0

    def disable_workflow(self, workflow_id):
        conn = self._get_conn()
        conn.execute("UPDATE workflows SET enabled = 0, updated_at = ? WHERE id = ?", (self._now(), workflow_id))
        conn.commit()
        affected = conn.total_changes
        conn.close()
        return affected > 0

    def save_execution(self, execution_id, workflow_id, status, result):
        now = self._now()
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO workflow_executions (id, workflow_id, status, result_json, started_at, finished_at) VALUES (?, ?, ?, ?, ?, ?)",
            (execution_id, workflow_id, status, json.dumps(result) if result else "{}", now, now)
        )
        conn.commit()
        conn.close()
        return True

    def get_executions(self, workflow_id, limit=20):
        conn = self._get_conn()
        c = conn.execute(
            "SELECT * FROM workflow_executions WHERE workflow_id = ? ORDER BY started_at DESC LIMIT ?",
            (workflow_id, limit)
        )
        rows = c.fetchall()
        conn.close()
        result = []
        for row in rows:
            result.append({
                "id": row[0],
                "workflow_id": row[1],
                "status": row[2],
                "result": json.loads(row[3]) if row[3] else {},
                "started_at": row[4],
                "finished_at": row[5],
            })
        return result

    def get_stats(self):
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM workflows").fetchone()[0]
        active = conn.execute("SELECT COUNT(*) FROM workflows WHERE enabled = 1").fetchone()[0]
        execs = conn.execute("SELECT COUNT(*) FROM workflow_executions").fetchone()[0]
        success = conn.execute("SELECT COUNT(*) FROM workflow_executions WHERE status = 'completed'").fetchone()[0]
        conn.close()
        return {
            "total_workflows": total,
            "active_workflows": active,
            "total_executions": execs,
            "success_rate": round((success / execs * 100) if execs > 0 else 0.0, 1),
        }
