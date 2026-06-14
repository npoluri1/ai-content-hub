import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AccessReview:
    def __init__(self, db_path: str = "./data/access_reviews.db"):
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
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS access_reviews (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    reviewers TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    due_date TEXT NOT NULL,
                    frequency TEXT NOT NULL DEFAULT 'quarterly',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS review_items (
                    id TEXT PRIMARY KEY,
                    review_id TEXT NOT NULL,
                    user TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    permission TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (review_id) REFERENCES access_reviews(id)
                );
                CREATE TABLE IF NOT EXISTS review_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    review_item_id TEXT NOT NULL,
                    reviewer TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    reason TEXT,
                    decided_at TEXT NOT NULL,
                    FOREIGN KEY (review_item_id) REFERENCES review_items(id)
                );
                CREATE INDEX IF NOT EXISTS idx_review_items_review ON review_items(review_id);
                CREATE INDEX IF NOT EXISTS idx_review_items_status ON review_items(status);
                CREATE INDEX IF NOT EXISTS idx_review_decisions_item ON review_decisions(review_item_id);
            """)

    def create_review(self, name: str, resource_type: str, reviewers: list[str], due_date: str, frequency: str = "quarterly") -> str:
        review_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO access_reviews (id, name, resource_type, reviewers, status, due_date, frequency, created_at)
                   VALUES (?, ?, ?, ?, 'active', ?, ?, ?)""",
                (review_id, name, resource_type, json.dumps(reviewers), due_date, frequency, now),
            )
        logger.info(f"Access review created: {review_id} '{name}'")
        return review_id

    def add_review_item(self, review_id: str, user: str, resource: str, permission: str) -> str:
        item_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO review_items (id, review_id, user, resource, permission, status, created_at)
                   VALUES (?, ?, ?, ?, ?, 'pending', ?)""",
                (item_id, review_id, user, resource, permission, now),
            )
        return item_id

    def submit_decision(self, review_item_id: str, reviewer: str, decision: str, reason: str = None) -> bool:
        if decision not in ("approved", "revoked", "removed"):
            logger.error(f"Invalid decision: {decision}")
            return False

        now = datetime.utcnow().isoformat()
        with self._get_conn() as conn:
            item = conn.execute("SELECT * FROM review_items WHERE id = ?", (review_item_id,)).fetchone()
            if not item:
                logger.warning(f"Review item not found: {review_item_id}")
                return False

            conn.execute(
                "INSERT INTO review_decisions (review_item_id, reviewer, decision, reason, decided_at) VALUES (?, ?, ?, ?, ?)",
                (review_item_id, reviewer, decision, reason, now),
            )

            if decision == "approved":
                new_status = "approved"
            elif decision in ("revoked", "removed"):
                new_status = decision
            else:
                new_status = "pending"

            conn.execute(
                "UPDATE review_items SET status = ? WHERE id = ?", (new_status, review_item_id)
            )
            conn.commit()

        logger.info(f"Decision submitted for {review_item_id}: {decision} by {reviewer}")
        return True

    def get_review_status(self, review_id: str) -> dict:
        with self._get_conn() as conn:
            items = conn.execute(
                "SELECT status, COUNT(*) as cnt FROM review_items WHERE review_id = ? GROUP BY status",
                (review_id,)
            ).fetchall()

        total = 0
        approved = 0
        revoked = 0
        pending = 0

        for row in items:
            total += row["cnt"]
            if row["status"] == "approved":
                approved = row["cnt"]
            elif row["status"] == "revoked":
                revoked = row["cnt"]
            elif row["status"] == "pending":
                pending = row["cnt"]

        return {
            "total": total,
            "approved": approved,
            "revoked": revoked,
            "pending": pending,
            "progress_pct": round(((total - pending) / total * 100), 1) if total > 0 else 0.0,
        }

    def get_pending_reviews(self, reviewer: str) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT ar.id, ar.name, ar.resource_type, ar.due_date, ar.frequency, ri.id as item_id,
                          ri.user, ri.resource, ri.permission, ri.created_at
                   FROM access_reviews ar
                   JOIN review_items ri ON ri.review_id = ar.id
                   WHERE ri.status = 'pending'
                   AND ar.status = 'active'
                   AND json_extract(ar.reviewers, '$') LIKE ?
                   ORDER BY ar.due_date ASC""",
                (f"%{reviewer}%",)
            ).fetchall()
        return [dict(r) for r in rows]

    def list_reviews(self, status: str = None) -> list[dict]:
        with self._get_conn() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM access_reviews WHERE status = ? ORDER BY created_at DESC", (status,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM access_reviews ORDER BY created_at DESC").fetchall()

        results = []
        for r in rows:
            d = dict(r)
            d["reviewers"] = json.loads(d["reviewers"])
            results.append(d)
        return results

    def generate_report(self, review_id: str) -> str:
        review = None
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM access_reviews WHERE id = ?", (review_id,)).fetchone()
            if row:
                review = dict(row)
                review["reviewers"] = json.loads(review["reviewers"])

        if not review:
            return json.dumps({"error": "Review not found"})

        items = []
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM review_items WHERE review_id = ?", (review_id,)).fetchall()
            for r in rows:
                item = dict(r)
                decisions = conn.execute(
                    "SELECT * FROM review_decisions WHERE review_item_id = ?", (item["id"],)
                ).fetchall()
                item["decisions"] = [dict(d) for d in decisions]
                items.append(item)

        status = self.get_review_status(review_id)

        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "review": review,
            "items": items,
            "summary": status,
            "compliance_status": "compliant" if status["pending"] == 0 else "pending_actions",
        }

        return json.dumps(report, indent=2, default=str)

    def auto_remediate(self, review_id: str, days_overdue: int = 7) -> int:
        now = datetime.utcnow()
        cutoff = (now - timedelta(days=days_overdue)).isoformat()

        with self._get_conn() as conn:
            overdue_items = conn.execute(
                """SELECT ri.id, ar.due_date
                   FROM review_items ri
                   JOIN access_reviews ar ON ar.id = ri.review_id
                   WHERE ri.review_id = ? AND ri.status = 'pending' AND ar.due_date < ?""",
                (review_id, cutoff)
            ).fetchall()

            auto_revoked = 0
            for item in overdue_items:
                conn.execute(
                    "UPDATE review_items SET status = 'revoked' WHERE id = ?", (item["id"],)
                )
                conn.execute(
                    "INSERT INTO review_decisions (review_item_id, reviewer, decision, reason, decided_at) VALUES (?, 'auto_remediation', 'revoked', ?, ?)",
                    (item["id"], f"Auto-revoked after {days_overdue} days overdue (due: {item['due_date']})", now.isoformat()),
                )
                auto_revoked += 1

            conn.commit()

        if auto_revoked > 0:
            logger.info(f"Auto-remediated {auto_revoked} overdue items for review {review_id}")

        return auto_revoked

    def get_compliance_score(self) -> float:
        with self._get_conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM review_items").fetchone()[0]
            if total == 0:
                return 100.0

            reviewed = conn.execute(
                "SELECT COUNT(*) FROM review_items WHERE status != 'pending'"
            ).fetchone()[0]

        return round((reviewed / total) * 100, 1)
