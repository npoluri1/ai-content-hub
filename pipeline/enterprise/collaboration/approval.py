import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class ApprovalWorkflow:
    def __init__(self, db_path: str = "./data/approvals.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflows (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    steps TEXT NOT NULL DEFAULT '[]',
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS submissions (
                    id TEXT PRIMARY KEY,
                    content_id TEXT NOT NULL,
                    workflow_id TEXT NOT NULL,
                    submitted_by TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    current_step INTEGER DEFAULT 0,
                    history TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE
                )
            """)

    def create_workflow(
        self,
        name: str,
        steps: list[dict],
        created_by: str,
    ) -> dict:
        wf_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        steps_json = json.dumps(steps)
        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO workflows (id, name, steps, created_by, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (wf_id, name, steps_json, created_by, now, now),
            )
            conn.commit()
        logger.info(f"Workflow created: {wf_id} ({name})")
        return {
            "id": wf_id,
            "name": name,
            "steps": steps,
            "created_by": created_by,
            "created_at": now,
            "updated_at": now,
        }

    def get_workflow(self, workflow_id: str) -> dict | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM workflows WHERE id = ?", (workflow_id,)
            ).fetchone()
        if not row:
            return None
        result = dict(row)
        result["steps"] = json.loads(result["steps"])
        return result

    def list_workflows(self) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM workflows ORDER BY created_at DESC"
            ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["steps"] = json.loads(d["steps"])
            results.append(d)
        return results

    def submit_content(
        self,
        content_id: str,
        workflow_id: str,
        submitted_by: str,
    ) -> str:
        submission_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        initial_history = json.dumps([
            {
                "step": "submission",
                "action": "submitted",
                "user": submitted_by,
                "timestamp": now,
                "comment": None,
            }
        ])
        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO submissions
                   (id, content_id, workflow_id, submitted_by, status, current_step, history, created_at, updated_at)
                   VALUES (?, ?, ?, ?, 'in_progress', 0, ?, ?, ?)""",
                (submission_id, content_id, workflow_id, submitted_by, initial_history, now, now),
            )
            conn.commit()
        logger.info(f"Content {content_id} submitted for approval: {submission_id}")
        return submission_id

    def approve(
        self,
        submission_id: str,
        step_name: str,
        user: str,
        comment: str | None = None,
    ) -> bool:
        return self._step_action(submission_id, step_name, user, "approved", comment)

    def reject(
        self,
        submission_id: str,
        step_name: str,
        user: str,
        reason: str,
    ) -> bool:
        return self._step_action(submission_id, step_name, user, "rejected", reason)

    def _step_action(
        self,
        submission_id: str,
        step_name: str,
        user: str,
        action: str,
        comment: str | None = None,
    ) -> bool:
        with self._get_conn() as conn:
            sub_row = conn.execute(
                "SELECT * FROM submissions WHERE id = ?", (submission_id,)
            ).fetchone()
            if not sub_row:
                logger.error(f"Submission not found: {submission_id}")
                return False

            wf_row = conn.execute(
                "SELECT * FROM workflows WHERE id = ?", (sub_row["workflow_id"],)
            ).fetchone()
            if not wf_row:
                logger.error(f"Workflow not found for submission: {submission_id}")
                return False

            steps = json.loads(wf_row["steps"])
            current_step_idx = sub_row["current_step"]
            history = json.loads(sub_row["history"])

            if current_step_idx >= len(steps):
                logger.error(f"No more steps to process for {submission_id}")
                return False

            current_step = steps[current_step_idx]
            if current_step["name"] != step_name:
                logger.error(
                    f"Expected step '{current_step['name']}', got '{step_name}'"
                )
                return False

            if user not in current_step.get("assignees", []):
                logger.error(f"User {user} not assigned to step '{step_name}'")
                return False

            now = datetime.utcnow().isoformat()
            entry = {
                "step": step_name,
                "action": action,
                "user": user,
                "timestamp": now,
                "comment": comment,
            }
            history.append(entry)

            if action == "rejected":
                conn.execute(
                    "UPDATE submissions SET status = 'rejected', history = ?, updated_at = ? WHERE id = ?",
                    (json.dumps(history), now, submission_id),
                )
                conn.commit()
                logger.info(f"Submission {submission_id} rejected at step '{step_name}' by {user}")
                return True

            approvals_for_step = [
                h for h in history
                if h["step"] == step_name and h["action"] == "approved"
            ]
            required = current_step.get("required_approvals", 1)

            if len(approvals_for_step) >= required:
                next_step = current_step_idx + 1
                if next_step >= len(steps):
                    conn.execute(
                        "UPDATE submissions SET status = 'approved', current_step = ?, history = ?, updated_at = ? WHERE id = ?",
                        (next_step, json.dumps(history), now, submission_id),
                    )
                    conn.commit()
                    logger.info(f"Submission {submission_id} fully approved")
                else:
                    conn.execute(
                        "UPDATE submissions SET status = 'in_progress', current_step = ?, history = ?, updated_at = ? WHERE id = ?",
                        (next_step, json.dumps(history), now, submission_id),
                    )
                    conn.commit()
                    logger.info(f"Submission {submission_id} advanced to next step")
            else:
                conn.execute(
                    "UPDATE submissions SET history = ?, updated_at = ? WHERE id = ?",
                    (json.dumps(history), now, submission_id),
                )
                conn.commit()
                logger.info(
                    f"Step '{step_name}' approved by {user} ({len(approvals_for_step)}/{required})"
                )
            return True

    def get_status(self, submission_id: str) -> dict | None:
        with self._get_conn() as conn:
            sub_row = conn.execute(
                "SELECT * FROM submissions WHERE id = ?", (submission_id,)
            ).fetchone()
            if not sub_row:
                return None
            wf_row = conn.execute(
                "SELECT * FROM workflows WHERE id = ?", (sub_row["workflow_id"],)
            ).fetchone()
            sub = dict(sub_row)
            wf = dict(wf_row) if wf_row else {}
            sub["history"] = json.loads(sub["history"])
            steps = json.loads(wf.get("steps", "[]")) if wf else []
            current_step_name = steps[sub["current_step"]]["name"] if sub["current_step"] < len(steps) else None
            return {
                "submission_id": submission_id,
                "content_id": sub["content_id"],
                "workflow_name": wf.get("name", "unknown"),
                "workflow_id": sub["workflow_id"],
                "current_step": current_step_name,
                "current_step_index": sub["current_step"],
                "status": sub["status"],
                "history": sub["history"],
                "created_at": sub["created_at"],
                "updated_at": sub["updated_at"],
            }

    def get_pending_approvals(self, user: str) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM submissions WHERE status = 'in_progress' ORDER BY created_at DESC"
            ).fetchall()
        pending = []
        for row in rows:
            sub = dict(row)
            wf_row = conn.execute(
                "SELECT * FROM workflows WHERE id = ?", (sub["workflow_id"],)
            ).fetchone()
            if not wf_row:
                continue
            steps = json.loads(wf_row["steps"])
            current_idx = sub["current_step"]
            if current_idx < len(steps):
                step = steps[current_idx]
                if user in step.get("assignees", []):
                    sub["history"] = json.loads(sub["history"])
                    pending.append({
                        "submission_id": sub["id"],
                        "content_id": sub["content_id"],
                        "workflow_name": wf_row["name"],
                        "step_name": step["name"],
                        "status": sub["status"],
                        "created_at": sub["created_at"],
                    })
        return pending

    def get_my_submissions(self, user: str) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM submissions WHERE submitted_by = ? ORDER BY created_at DESC",
                (user,),
            ).fetchall()
        results = []
        for row in rows:
            sub = dict(row)
            wf_row = conn.execute(
                "SELECT name FROM workflows WHERE id = ?", (sub["workflow_id"],)
            ).fetchone()
            sub["history"] = json.loads(sub["history"])
            results.append({
                "submission_id": sub["id"],
                "content_id": sub["content_id"],
                "workflow_name": wf_row["name"] if wf_row else "unknown",
                "status": sub["status"],
                "current_step": sub["current_step"],
                "created_at": sub["created_at"],
                "updated_at": sub["updated_at"],
            })
        return results
